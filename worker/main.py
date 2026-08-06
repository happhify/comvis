import os
import csv
import time
from datetime import datetime

import cv2
import yaml
from dotenv import load_dotenv

from src.rtsp_reader import RTSPReader
from src.detector import PersonDetector
from src.classifier import EmployeeClassifier
from src.visualizer import draw_person_boxes, draw_hud
from src.recognition_cache import RecognitionCache
from src.utils import resize_frame_by_width
from src.runtime_monitor import RuntimeMonitor
from src.dashboard_client import DashboardFrameClient
from src.daily_stats_db import DailyStatsDB
#from src.dashboard_writer import save_dashboard_frame


def load_config(config_path="config/camera.yaml"):
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def ensure_dir(path):
    if path and not os.path.exists(path):
        os.makedirs(path)


def get_timestamp_string():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def find_camera(cameras_list, camera_id):
    for camera in cameras_list:
        if camera.get("id") == camera_id:
            return camera
    return None


def resolve_rtsp_url(camera_entry):
    rtsp_env_key = camera_entry.get("rtsp_env_key", "RTSP_URL")
    rtsp_url = os.getenv(rtsp_env_key)

    if rtsp_url is None or rtsp_url.strip() == "":
        print(f"[ERROR] RTSP URL tidak ditemukan di .env untuk kamera "
              f"'{camera_entry.get('id')}'.")
        print(f"[INFO] Pastikan ada variabel: {rtsp_env_key}")
        return None

    return rtsp_url


def connect_camera(
    camera_entry,
    fallback_video,
    reconnect,
    reconnect_delay_seconds,
    max_failed_reads,
):
    """
    Membuka koneksi ke SATU kamera (dipakai saat start maupun saat pindah
    kamera dari dashboard). Coba RTSP dulu, kalau gagal jatuh ke
    fallback_video. Return (reader, camera_name, source_type) kalau
    berhasil, atau (None, None, None) kalau dua-duanya gagal.
    """
    camera_id = camera_entry.get("id", "kamera")
    camera_name = camera_entry.get("name", camera_id)

    rtsp_url = resolve_rtsp_url(camera_entry)

    if rtsp_url is not None:
        reader = RTSPReader(
            source=rtsp_url,
            source_name=camera_name,
            reconnect=reconnect,
            reconnect_delay_seconds=reconnect_delay_seconds,
            max_failed_reads=max_failed_reads,
        )

        if reader.connect():
            return reader, camera_name, "rtsp"

        print(f"[WARNING] Gagal membuka RTSP kamera '{camera_name}'.")

    if fallback_video:
        print(f"[INFO] Mencoba fallback video lokal untuk '{camera_name}'...")

        reader = RTSPReader(
            source=fallback_video,
            source_name=camera_name,
            reconnect=False,
            reconnect_delay_seconds=reconnect_delay_seconds,
            max_failed_reads=max_failed_reads,
        )

        if reader.connect():
            return reader, camera_name, "video"

    print(f"[ERROR] Kamera '{camera_name}': RTSP dan fallback video "
          f"sama-sama gagal dibuka.")
    return None, None, None


def resize_frame(frame, target_width):
    if target_width is None or target_width <= 0:
        return frame

    height, width = frame.shape[:2]
    scale = target_width / width
    new_height = int(height * scale)

    resized_frame = cv2.resize(frame, (target_width, new_height))
    return resized_frame


def draw_fps(frame, fps):
    text = f"FPS: {fps:.2f}"

    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )

    return frame


def crop_bbox(frame, bbox):
    x1, y1, x2, y2 = bbox

    height, width = frame.shape[:2]

    x1 = max(0, int(x1))
    y1 = max(0, int(y1))
    x2 = min(width, int(x2))
    y2 = min(height, int(y2))

    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    return crop


def create_video_writer(output_path, frame, fps=20):
    output_dir = os.path.dirname(output_path)
    ensure_dir(output_dir)

    height, width = frame.shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        output_path,
        fourcc,
        fps,
        (width, height),
    )

    if not writer.isOpened():
        print("[ERROR] Gagal membuat VideoWriter.")
        return None

    print(f"[INFO] Output video akan disimpan ke: {output_path}")
    return writer

def init_log_file(log_path):
    log_dir = os.path.dirname(log_path)
    ensure_dir(log_dir)

    header = [
        "timestamp",
        "camera_name",
        "source_type",
        "frame_id",
        "detection_id",
        "bbox_x1",
        "bbox_y1",
        "bbox_x2",
        "bbox_y2",
        "bbox_width",
        "bbox_height",
        "detector_label",
        "detector_confidence",
        "identity_label",
        "identity_status",
        "recognition_confidence",
        "recognition_margin",
        "from_cache",
        "crop_width",
        "crop_height",
        "note",
    ]

    if os.path.exists(log_path):
        with open(log_path, mode="r", encoding="utf-8") as file:
            first_line = file.readline().strip()

        existing_header = first_line.split(",")

        if existing_header == header:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = log_path.replace(".csv", f"_backup_{timestamp}.csv")

        os.rename(log_path, backup_path)
        print(f"[WARNING] Format log lama berbeda. Log lama dibackup ke: {backup_path}")

    with open(log_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)

def write_detection_log(log_path, camera_name, source_type, frame_id, detections):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        for detection_id, detection in enumerate(detections):
            x1, y1, x2, y2 = detection["bbox"]

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            bbox_width = max(0, x2 - x1)
            bbox_height = max(0, y2 - y1)

            row = [
                timestamp,
                camera_name,
                source_type,
                frame_id,
                detection_id,
                x1,
                y1,
                x2,
                y2,
                bbox_width,
                bbox_height,
                "person",
                round(detection.get("confidence", 0.0), 4),
                detection.get("identity_raw_label", "unknown"),
                detection.get("status", "unknown"),
                round(detection.get("identity_confidence", 0.0), 4),
                round(detection.get("identity_margin", 0.0), 4),
                detection.get("from_cache", False),
                bbox_width,
                bbox_height,
                f"cache_entry_id={detection.get('cache_entry_id', '')}",
            ]

            writer.writerow(row)

def save_person_crops(frame, detections, camera_name, frame_id, crop_output_dir):
    ensure_dir(crop_output_dir)

    saved_count = 0
    timestamp = get_timestamp_string()

    for person_id, detection in enumerate(detections):
        bbox = detection["bbox"]
        crop = crop_bbox(frame, bbox)

        if crop is None or crop.size == 0:
            continue

        status = detection.get("status", "person")
        raw_label = detection.get("identity_raw_label", "person")
        conf = detection.get("identity_confidence", detection.get("confidence", 0.0))

        filename = (
            f"{camera_name}_{timestamp}_"
            f"frame_{frame_id}_person_{person_id}_"
            f"{status}_{raw_label}_conf_{conf:.2f}.jpg"
        )

        save_path = os.path.join(crop_output_dir, filename)

        cv2.imwrite(save_path, crop)
        saved_count += 1

    if saved_count > 0:
        print(f"[INFO] Saved crops: {saved_count}")

def recognize_detections(
    frame,
    detections,
    classifier,
    recognition_cache,
    frame_id,
    min_crop_width=40,
    min_crop_height=80,
):
    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]

        x1 = int(x1)
        y1 = int(y1)
        x2 = int(x2)
        y2 = int(y2)

        bbox = (x1, y1, x2, y2)

        crop_width = x2 - x1
        crop_height = y2 - y1

        entry_id, cache_entry, is_new_entry = recognition_cache.get_or_create_entry(
            bbox=bbox,
            frame_id=frame_id,
        )

        detection["cache_entry_id"] = entry_id

        if crop_width < min_crop_width or crop_height < min_crop_height:
            detection["status"] = "unknown"
            detection["display_label"] = "Unknown 0.00"
            detection["identity_confidence"] = 0.0
            detection["identity_raw_label"] = "small_crop"
            detection["identity_margin"] = 0.0
            detection["identity_top2_label"] = "none"
            detection["identity_top2_confidence"] = 0.0
            detection["from_cache"] = False

            recognition_cache.update_recognition(
                entry_id=entry_id,
                bbox=bbox,
                frame_id=frame_id,
                identity_status="unknown",
                identity_label="small_crop",
                recognition_confidence=0.0,
                recognition_margin=0.0,
            )

            continue

        run_recognition = recognition_cache.should_run_recognition(
            entry=cache_entry,
            frame_id=frame_id,
        )

        if run_recognition:
            crop = crop_bbox(frame, bbox)

            if crop is None or crop.size == 0:
                detection["status"] = "unknown"
                detection["display_label"] = "Unknown 0.00"
                detection["identity_confidence"] = 0.0
                detection["identity_raw_label"] = "empty_crop"
                detection["identity_margin"] = 0.0
                detection["identity_top2_label"] = "none"
                detection["identity_top2_confidence"] = 0.0
                detection["from_cache"] = False

                recognition_cache.update_recognition(
                    entry_id=entry_id,
                    bbox=bbox,
                    frame_id=frame_id,
                    identity_status="unknown",
                    identity_label="empty_crop",
                    recognition_confidence=0.0,
                    recognition_margin=0.0,
                )

                continue

            result = classifier.predict(crop)

            status = result.get("status", "unknown")
            display_label = result.get("display_label", "Unknown 0.00")
            raw_label = result.get("raw_label", "unknown")
            confidence = result.get("confidence", 0.0)
            margin = result.get("margin", 0.0)
            top2_label = result.get("top2_label", "none")
            top2_confidence = result.get("top2_confidence", 0.0)

            detection["status"] = status
            detection["display_label"] = display_label
            detection["identity_confidence"] = confidence
            detection["identity_raw_label"] = raw_label
            detection["identity_margin"] = margin
            detection["identity_top2_label"] = top2_label
            detection["identity_top2_confidence"] = top2_confidence
            detection["from_cache"] = False

            recognition_cache.update_recognition(
                entry_id=entry_id,
                bbox=bbox,
                frame_id=frame_id,
                identity_status=status,
                identity_label=raw_label,
                recognition_confidence=confidence,
                recognition_margin=margin,
            )

        else:
            cached_result = recognition_cache.get_display_result(cache_entry)

            cached_status = cached_result.get("identity_status", "unknown")
            cached_label = cached_result.get("identity_label", "unknown")
            cached_confidence = cached_result.get("recognition_confidence", 0.0)
            cached_margin = cached_result.get("recognition_margin", 0.0)

            detection["status"] = cached_status
            detection["identity_raw_label"] = cached_label
            detection["identity_confidence"] = cached_confidence
            detection["identity_margin"] = cached_margin
            detection["identity_top2_label"] = "cached"
            detection["identity_top2_confidence"] = 0.0
            detection["from_cache"] = True

            if cached_status == "verified":
                detection["display_label"] = f"Hadi {cached_confidence:.2f}"
            else:
                detection["display_label"] = f"Unknown {cached_confidence:.2f}"

    recognition_cache.cleanup(frame_id)

    return detections

def main():
    load_dotenv()

    # Container tidak punya display -> cv2.imshow()/waitKey() akan crash.
    # docker-compose men-set HEADLESS=true untuk service worker.
    headless = os.getenv("HEADLESS", "false").strip().lower() == "true"

    config = load_config()

    cameras_config = config.get("cameras", {})
    preview_config = config["preview"]
    connection_config = config["connection"]
    detection_config = config.get("detection", {})
    recognition_config = config.get("recognition", {})
    output_config = config.get("output", {})
    realtime_config = config.get("realtime", {})
    runtime_config = config.get("runtime_monitor", {})

    cameras_list = cameras_config.get("list", [])
    fallback_video = cameras_config.get("fallback_video", "videos/sample_video.mp4")

    if not cameras_list:
        print("[ERROR] config/camera.yaml tidak punya cameras.list (belum ada kamera terdaftar).")
        return

    window_name = preview_config.get("window_name", "Preview CCTV")
    resize_width = realtime_config.get(
        "resize_width",
        preview_config.get("resize_width", 960)
    )
    show_fps = preview_config.get("show_fps", True)

    reconnect = connection_config.get("reconnect", True)
    reconnect_delay_seconds = connection_config.get("reconnect_delay_seconds", 3)
    max_failed_reads = connection_config.get("max_failed_reads", 30)

    detection_enabled = detection_config.get("enabled", True)
    detector_model_path = detection_config.get("model_path", "models/yolov8n.pt")
    detector_confidence = detection_config.get("confidence_threshold", 0.35)
    detector_device = detection_config.get("device", "cpu")

    recognition_enabled = recognition_config.get("enabled", True)
    classifier_model_path = recognition_config.get("model_path", "models/body_best.pt")
    classifier_device = recognition_config.get("device", "cpu")
    verified_threshold = recognition_config.get("verified_threshold", 0.97)
    unknown_threshold = recognition_config.get("unknown_threshold", 0.70)
    min_margin = recognition_config.get("min_margin", 0.40)
    min_crop_width = recognition_config.get("min_crop_width", 40)
    min_crop_height = recognition_config.get("min_crop_height", 80)

    recognition_interval = realtime_config.get("recognition_interval", 10)
    cache_ttl_frames = realtime_config.get("cache_ttl_frames", 30)
    cache_iou_threshold = realtime_config.get("cache_iou_threshold", 0.35)

    save_video = output_config.get("save_video", True)
    # Nama file video dibuat per-kamera (result_<camera_id>.mp4) supaya
    # ganti kamera tidak menimpa rekaman kamera lain -> cukup folder-nya
    # yang diambil dari config, nama filenya dibuat dinamis di bawah.
    video_output_dir = os.path.dirname(output_config.get(
        "video_output_path",
        "outputs/videos/result_kamera_1.mp4",
    )) or "outputs/videos"

    def video_path_for_camera(camera_id):
        return os.path.join(video_output_dir, f"result_{camera_id}.mp4")

    save_crops = output_config.get("save_crops", True)
    crop_output_dir = output_config.get("crop_output_dir", "outputs/crops")
    crop_every_n_frames = output_config.get("crop_every_n_frames", 30)

    save_log = output_config.get("save_log", True)
    log_output_path = output_config.get(
        "log_output_path",
        "outputs/logs/detection_log.csv",
    )

    runtime_monitor_enabled = runtime_config.get("enabled", True)
    runtime_summary_json_path = runtime_config.get(
        "summary_json_path",
        "outputs/logs/runtime_summary.json",
    )
    runtime_summary_csv_path = runtime_config.get(
        "summary_csv_path",
        "outputs/logs/runtime_summary.csv",
    )

    initial_camera_id = cameras_config.get("default") or cameras_list[0].get("id")
    initial_camera = find_camera(cameras_list, initial_camera_id) or cameras_list[0]

    reader, camera_name, source_type = connect_camera(
        camera_entry=initial_camera,
        fallback_video=fallback_video,
        reconnect=reconnect,
        reconnect_delay_seconds=reconnect_delay_seconds,
        max_failed_reads=max_failed_reads,
    )

    if reader is None:
        print("[INFO] Pastikan RTSP benar atau file videos/sample_video.mp4 tersedia.")
        return

    current_camera_id = initial_camera.get("id")

    detector = None

    if detection_enabled:
        detector = PersonDetector(
            model_path=detector_model_path,
            confidence_threshold=detector_confidence,
            device=detector_device,
        )

    classifier = None

    if recognition_enabled:
        classifier = EmployeeClassifier(
            model_path=classifier_model_path,
            device=classifier_device,
            verified_threshold=verified_threshold,
            unknown_threshold=unknown_threshold,
            min_margin=min_margin,
        )
    
    recognition_cache = RecognitionCache(
        recognition_interval=recognition_interval,
        cache_ttl_frames=cache_ttl_frames,
        iou_threshold=cache_iou_threshold,
    )

    print("[INFO] Recognition cache aktif.")
    print(f"[INFO] recognition_interval : {recognition_interval}")
    print(f"[INFO] cache_ttl_frames     : {cache_ttl_frames}")
    print(f"[INFO] cache_iou_threshold  : {cache_iou_threshold}")

    if save_log:
        init_log_file(log_output_path)
        print(f"[INFO] Log CSV akan disimpan ke: {log_output_path}")

    runtime_monitor = None

    if runtime_monitor_enabled:
        runtime_monitor = RuntimeMonitor(
            camera_name=camera_name,
            source_type=source_type,
            summary_json_path=runtime_summary_json_path,
            summary_csv_path=runtime_summary_csv_path,
        )

        print("[INFO] Runtime monitor aktif.")

    prev_time = time.time()
    frame_id = 0
    video_writer = None
    current_video_path = None
    total_detections = 0

    # Database SQLite untuk rekap orang per hari (Tahap Database)
    daily_stats_db = DailyStatsDB(db_path="outputs/comvis_stats.db")
    last_unique_persons = 0

    # Di Docker Compose, backend diakses lewat nama service ("backend"),
    # bukan localhost. Di luar Docker (dev di Windows), backend jalan di
    # host yang sama -> default tetap localhost.
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

    dashboard_client = DashboardFrameClient(
        frame_api_url=f"{backend_url}/api/frame",
        stats_api_url=f"{backend_url}/api/stats-update",
        enabled=True,
        send_frame_every_n_frames=5,
        send_stats_every_n_frames=5,
        resize_width=960,
        jpeg_quality=70,
        timeout=0.2,
    )

    print("[INFO] Preview RTSP + YOLO + Employee Recognition dimulai.")
    print("[INFO] Tekan tombol 'q' untuk keluar.")

    while True:
        ret, raw_frame = reader.read()

        if not ret:
            if runtime_monitor is not None:
                runtime_monitor.add_failed_read()
            continue

        frame_id += 1

        work_frame = resize_frame_by_width(raw_frame, resize_width)

        # Saklar dari dashboard: admin bisa mematikan deteksi.
        # Saat OFF, video tetap streaming tapi YOLO/classifier dilewati.
        control = dashboard_client.get_control()

        # Perintah pindah kamera dari dashboard (dropdown kamera di sidebar).
        requested_camera_id = control.get("camera_id")

        if requested_camera_id and requested_camera_id != current_camera_id:
            next_camera = find_camera(cameras_list, requested_camera_id)

            if next_camera is None:
                print(f"[WARNING] Kamera '{requested_camera_id}' tidak dikenal, "
                      f"tetap di '{current_camera_id}'.")
            else:
                print(f"[INFO] Pindah kamera: '{current_camera_id}' -> "
                      f"'{requested_camera_id}'...")

                new_reader, new_camera_name, new_source_type = connect_camera(
                    camera_entry=next_camera,
                    fallback_video=fallback_video,
                    reconnect=reconnect,
                    reconnect_delay_seconds=reconnect_delay_seconds,
                    max_failed_reads=max_failed_reads,
                )

                if new_reader is None:
                    print(f"[WARNING] Gagal pindah ke kamera '{requested_camera_id}', "
                          f"tetap di '{current_camera_id}'.")
                else:
                    reader.release()
                    reader = new_reader
                    camera_name = new_camera_name
                    source_type = new_source_type
                    current_camera_id = requested_camera_id

                    # Tracking & video output lama tidak relevan lagi -
                    # kamera baru = tempat yang beda.
                    recognition_cache = RecognitionCache(
                        recognition_interval=recognition_interval,
                        cache_ttl_frames=cache_ttl_frames,
                        iou_threshold=cache_iou_threshold,
                    )

                    if video_writer is not None:
                        video_writer.release()
                        video_writer = None

                    if runtime_monitor is not None:
                        runtime_monitor.camera_name = camera_name

                    print(f"[INFO] Kamera aktif sekarang: '{camera_name}' "
                          f"({current_camera_id}).")

            # Frame yang barusan dibaca itu dari kamera LAMA -> lewati,
            # mulai bersih di iterasi berikutnya dengan reader yang baru.
            continue

        detection_active = bool(control.get("detection_enabled", True))

        detections = []

        if detection_active and detection_enabled and detector is not None:
            detections = detector.detect_person(work_frame)

        if recognition_enabled and classifier is not None:
            detections = recognize_detections(
                frame=work_frame,
                detections=detections,
                classifier=classifier,
                recognition_cache=recognition_cache,
                frame_id=frame_id,
                min_crop_width=min_crop_width,
                min_crop_height=min_crop_height,
            )
        else:
            for detection in detections:
                detection["status"] = "person"
                detection["display_label"] = f"person {detection['confidence']:.2f}"
                detection["identity_confidence"] = 0.0
                detection["identity_raw_label"] = "person"
                detection["identity_margin"] = 0.0
                detection["from_cache"] = False

        total_detections += len(detections)

        if save_log:
            write_detection_log(
                log_path=log_output_path,
                camera_name=camera_name,
                source_type=source_type,
                frame_id=frame_id,
                detections=detections,
            )

        if save_crops and frame_id % crop_every_n_frames == 0:
            save_person_crops(
                frame=work_frame,
                detections=detections,
                camera_name=camera_name,
                frame_id=frame_id,
                crop_output_dir=crop_output_dir,
            )

        annotated_frame = work_frame.copy()

        annotated_frame = draw_person_boxes(
            annotated_frame,
            detections,
        )

        current_time = time.time()
        fps = 1 / (current_time - prev_time)
        prev_time = current_time

        # Perkiraan jumlah ORANG unik selama sesi, diambil dari
        # recognition cache: setiap orang baru yang masuk tracking
        # membuat 1 entry baru. Catatan: orang yang keluar frame lalu
        # masuk lagi setelah cache kedaluwarsa akan terhitung lagi,
        # jadi ini perkiraan, bukan angka pasti.
        if recognition_cache is not None:
            unique_persons = recognition_cache.next_entry_id - 1
        else:
            unique_persons = 0

        # Kalau angka orang unik bertambah, catat selisihnya ke SQLite.
        # Contoh: 3 -> 5 berarti ada 2 orang baru masuk tracking.
        if unique_persons > last_unique_persons:
            daily_stats_db.record_new_persons(
                camera_name=camera_name,
                count=unique_persons - last_unique_persons,
            )
        last_unique_persons = unique_persons
        active_persons = recognition_cache.get_active_persons() if recognition_cache is not None else []

        dashboard_client.submit_stats(
            camera_name=camera_name,
            source_type=source_type,
            frame_id=frame_id,
            fps=fps,
            detections=detections,
            total_detections=total_detections,
            unique_persons=unique_persons,
            active_persons=active_persons,
        )

        if runtime_monitor is not None:
            runtime_monitor.update_frame(
                frame_id=frame_id,
                fps=fps,
                detections=detections,
            )

        hud_lines = []

        if show_fps:
            hud_lines.append(f"FPS: {fps:.2f}")

        hud_lines.append(f"Persons: {len(detections)}")
        hud_lines.append(f"Camera: {camera_name}")

        if not detection_active:
            hud_lines.append(
                ("DETEKSI NONAKTIF (dimatikan dari dashboard)", (0, 200, 255))
            )

        annotated_frame = draw_hud(annotated_frame, hud_lines)

        dashboard_client.submit_frame(
            frame=annotated_frame,
            frame_id=frame_id,
        )

        if not headless:
            cv2.imshow(window_name, annotated_frame)

        if save_video:
            if video_writer is None:
                current_video_path = video_path_for_camera(current_camera_id)
                video_writer = create_video_writer(
                    output_path=current_video_path,
                    frame=annotated_frame,
                    fps=20,
                )

            if video_writer is not None:
                video_writer.write(annotated_frame)

        if not headless:
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                print("[INFO] Tombol q ditekan. Program dihentikan.")
                break

    if runtime_monitor is not None:
        runtime_monitor.save_summary()

    dashboard_client.stop()

    reader.release()

    if video_writer is not None:
        video_writer.release()
        print(f"[INFO] Video output tersimpan: {current_video_path}")

    if not headless:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()