import threading
from datetime import datetime
STALE_AFTER_SECONDS = 15


class SharedState:
    """
    Menyimpan data terakhir dari main.py.

    Isi yang disimpan:
    1. Frame JPEG terakhir untuk /api/stream
    2. Statistik realtime untuk /api/stats
    """

    def __init__(self):
        self._lock = threading.Lock()

        self._latest_frame_jpeg = None
        self._frame_last_update = None
        self._frame_counter = 0

        # Saklar kontrol dari dashboard (Tahap Fitur):
        # main.py membaca ini lewat respons /api/stats-update.
        # camera_id: None berarti "belum ada perintah pindah kamera" ->
        # main.py tetap pakai cameras.default dari config/camera.yaml.
        self._control = {
            "detection_enabled": True,
            "camera_id": None,
        }

        self._stats = {
            "camera_name": "kamera_1",
            "camera_status": "WAITING",
            "source_type": "rtsp",
            "people_in_frame": 0,
            "employee_active": 0,
            "unknown_active": 0,
            "total_detections": 0,
            "unique_persons": 0,
            "active_persons": [],  
            "fps": 0.0,
            "frame_id": 0,
            "last_update": None,
            "note": "Menunggu data dari main.py",
        }

    # ========================================================
    # Frame handling
    # ========================================================

    def update_frame(self, frame_jpeg: bytes):
        """
        Menyimpan frame JPEG terbaru untuk video stream.
        """
        if not frame_jpeg:
            return

        with self._lock:
            self._latest_frame_jpeg = frame_jpeg
            self._frame_last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._frame_counter += 1

    def get_latest_frame(self):
        """
        Mengambil frame JPEG terbaru.
        """
        with self._lock:
            return self._latest_frame_jpeg

    def get_frame_status(self):
        """
        Mengecek status frame stream.
        """
        with self._lock:
            return {
                "has_frame": self._latest_frame_jpeg is not None,
                "last_update": self._frame_last_update,
                "frame_counter": self._frame_counter,
            }

    # ========================================================
    # Stats handling
    # ========================================================

    def update_stats(self, stats: dict):
        """
        Menyimpan statistik realtime terbaru dari main.py.
        """
        if not stats:
            return

        with self._lock:
            self._stats = {
                "camera_name": stats.get("camera_name", "kamera_1"),
                "camera_status": stats.get("camera_status", "LIVE"),
                "source_type": stats.get("source_type", "rtsp"),
                "people_in_frame": int(stats.get("people_in_frame", 0)),
                "employee_active": int(stats.get("employee_active", 0)),
                "unknown_active": int(stats.get("unknown_active", 0)),
                "total_detections": int(stats.get("total_detections", 0)),
                "unique_persons": int(stats.get("unique_persons", 0)),
                "active_persons": list(stats.get("active_persons") or []), 
                "fps": float(stats.get("fps", 0.0)),
                "frame_id": int(stats.get("frame_id", 0)),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "Data realtime dari main.py",
            }
            
    def get_stats(self):
        """
        Mengambil statistik realtime terakhir.

        Kalau main.py berhenti mengirim (ditutup / crash), status "LIVE"
        yang tersimpan sudah tidak benar. Di sini umurnya dicek dulu,
        lalu diturunkan jadi "WAITING" supaya pembaca lain (monitor,
        script, dashboard) tidak tertipu data lama.
        """
        with self._lock:
            stats = dict(self._stats)

        stats["stale_seconds"] = None

        last_update = stats.get("last_update")
        if last_update:
            try:
                age = (
                    datetime.now()
                    - datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
                ).total_seconds()
            except ValueError:
                return stats

            stats["stale_seconds"] = int(max(0, age))

            if age > STALE_AFTER_SECONDS and stats.get("camera_status") == "LIVE":
                stats["camera_status"] = "WAITING"
                stats["note"] = (
                    f"Data terakhir {int(age)} detik lalu - main.py mungkin berhenti."
                )

        return stats

    # ========================================================
    # Control handling (saklar dari dashboard)
    # ========================================================

    def get_control(self):
        with self._lock:
            return dict(self._control)

    def set_control(self, updates: dict):
        """
        Mengubah saklar. Hanya key yang dikenal yang diterima,
        supaya orang tidak bisa menyisipkan data aneh.
        """
        if not updates:
            return

        with self._lock:
            if "detection_enabled" in updates and updates["detection_enabled"] is not None:
                self._control["detection_enabled"] = bool(updates["detection_enabled"])

            if "camera_id" in updates and updates["camera_id"]:
                self._control["camera_id"] = str(updates["camera_id"])


shared_state = SharedState()