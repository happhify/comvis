import queue
import threading
import time

import cv2
import requests


class DashboardFrameClient:
    """
    Mengirim data dari main.py ke FastAPI dashboard.

    Yang dikirim:
    1. annotated_frame ke /api/frame
    2. statistik deteksi ke /api/stats-update

    Dibuat pakai background thread supaya main.py tetap ringan.
    """

    def __init__(
        self,
        frame_api_url="http://localhost:8000/api/frame",
        stats_api_url="http://localhost:8000/api/stats-update",
        enabled=True,
        send_frame_every_n_frames=5,
        send_stats_every_n_frames=5,
        resize_width=960,
        jpeg_quality=70,
        timeout=0.2,
    ):
        self.frame_api_url = frame_api_url
        self.stats_api_url = stats_api_url
        self.enabled = enabled

        self.send_frame_every_n_frames = send_frame_every_n_frames
        self.send_stats_every_n_frames = send_stats_every_n_frames

        self.resize_width = resize_width
        self.jpeg_quality = jpeg_quality
        self.timeout = timeout

        self.frame_queue = queue.Queue(maxsize=1)
        self.stats_queue = queue.Queue(maxsize=1)

        self.stop_event = threading.Event()

        # Saklar terakhir yang diterima dari backend (Tahap Fitur).
        # Diisi oleh stats worker, dibaca oleh main loop.
        self._control_lock = threading.Lock()
        self._remote_control = {"detection_enabled": True}

        self.frame_worker = threading.Thread(
            target=self._frame_worker_loop,
            daemon=True,
        )

        self.stats_worker = threading.Thread(
            target=self._stats_worker_loop,
            daemon=True,
        )

        if self.enabled:
            self.frame_worker.start()
            self.stats_worker.start()

    # ========================================================
    # Frame sender
    # ========================================================

    def submit_frame(self, frame, frame_id):
        """
        Mengirim frame ke queue.
        Frame tidak langsung dikirim di main loop agar FPS tidak drop.
        """
        if not self.enabled:
            return

        if frame is None:
            return

        if frame_id % self.send_frame_every_n_frames != 0:
            return

        try:
            if self.frame_queue.full():
                self.frame_queue.get_nowait()

            self.frame_queue.put_nowait(frame.copy())
        except queue.Full:
            pass

    def _resize_frame(self, frame):
        height, width = frame.shape[:2]

        if self.resize_width is None or self.resize_width <= 0:
            return frame

        if width <= self.resize_width:
            return frame

        scale = self.resize_width / width
        new_height = int(height * scale)

        return cv2.resize(frame, (self.resize_width, new_height))

    def _frame_worker_loop(self):
        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                frame = self._resize_frame(frame)

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
                )

                if not success:
                    continue

                requests.post(
                    self.frame_api_url,
                    data=encoded.tobytes(),
                    headers={"Content-Type": "image/jpeg"},
                    timeout=self.timeout,
                )

            except Exception:
                # Backend belum hidup tidak boleh membuat main.py crash.
                time.sleep(0.2)

    # ========================================================
    # Stats sender
    # ========================================================

    def submit_stats(
        self,
        camera_name,
        source_type,
        frame_id,
        fps,
        detections,
        total_detections,
        unique_persons=0,
        active_persons=None, 
    ):
        """
        Mengirim statistik realtime ke queue.
        """
        if not self.enabled:
            return

        if frame_id % self.send_stats_every_n_frames != 0:
            return

        stats = self._build_stats_payload(
            camera_name=camera_name,
            source_type=source_type,
            frame_id=frame_id,
            fps=fps,
            detections=detections,
            total_detections=total_detections,
            unique_persons=unique_persons,
            active_persons=active_persons,
        )

        try:
            if self.stats_queue.full():
                self.stats_queue.get_nowait()

            self.stats_queue.put_nowait(stats)
        except queue.Full:
            pass

    def _build_stats_payload(
        self,
        camera_name,
        source_type,
        frame_id,
        fps,
        detections,
        total_detections,
        unique_persons=0,
        active_persons=None, 
    ):
        employee_active = 0
        unknown_active = 0

        for detection in detections:
            status = str(detection.get("status", "unknown")).lower()

            if status == "verified":
                employee_active += 1
            else:
                unknown_active += 1

        return {
            "camera_name": camera_name,
            "camera_status": "LIVE",
            "source_type": source_type,
            "people_in_frame": len(detections),
            "employee_active": employee_active,
            "unknown_active": unknown_active,
            "total_detections": total_detections,
            "unique_persons": int(unique_persons),
            "active_persons": active_persons or [],
            "fps": round(float(fps), 2),
            "frame_id": frame_id,
        }

    def get_control(self):
        """
        Dibaca main.py tiap frame: perintah terbaru dari dashboard.
        Default detection_enabled=True kalau backend belum menjawab.
        """
        with self._control_lock:
            return dict(self._remote_control)

    def _stats_worker_loop(self):
        while not self.stop_event.is_set():
            try:
                stats = self.stats_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                response = requests.post(
                    self.stats_api_url,
                    json=stats,
                    timeout=self.timeout,
                )

                # Backend menumpangkan saklar kontrol di jawabannya
                try:
                    control = response.json().get("control")
                    if isinstance(control, dict):
                        with self._control_lock:
                            self._remote_control = control
                except Exception:
                    pass

            except Exception:
                # Backend belum hidup tidak boleh membuat main.py crash.
                time.sleep(0.2)

    # ========================================================
    # Stop
    # ========================================================

    def stop(self):
        self.stop_event.set()