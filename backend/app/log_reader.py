import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = PROJECT_ROOT / "outputs" / "logs" / "detection_log.csv"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def format_status(identity_status, identity_label, confidence):
    """
    Mengubah status mentah CSV menjadi label yang enak dibaca di dashboard.
    """
    status = str(identity_status or "unverified").strip().lower()
    label = str(identity_label or "").strip()

    if status == "verified":
        if label and label.lower() not in ["unknown", "small_crop", "empty_crop"]:
            return f"Employee: {label.capitalize()}"
        return "Employee: Verified"

    if status == "unknown":
        return "Unknown"

    return "Unverified"


def read_recent_detections(limit=10, log_path=DEFAULT_LOG_PATH):
    """
    Membaca detection_log.csv dan mengambil beberapa baris terakhir.

    Dibuat aman:
    - Kalau file belum ada, return list kosong.
    - Kalau CSV kosong, return list kosong.
    - Kalau kolom tertentu belum ada, tetap tidak crash.
    """

    path = Path(log_path)

    if not path.exists():
        return {
            "status": "warning",
            "message": "detection_log.csv belum tersedia.",
            "data": [],
        }

    try:
        with open(path, mode="r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)

    except Exception as error:
        return {
            "status": "error",
            "message": f"Gagal membaca detection_log.csv: {error}",
            "data": [],
        }

    if not rows:
        return {
            "status": "warning",
            "message": "detection_log.csv masih kosong.",
            "data": [],
        }

    recent_rows = rows[-limit:]
    recent_rows.reverse()

    data = []

    for row in recent_rows:
        timestamp = row.get("timestamp", "-")
        camera_name = row.get("camera_name", "kamera_1")
        frame_id = row.get("frame_id", "-")
        detection_id = row.get("detection_id", "-")

        identity_status = row.get("identity_status", "unverified")
        identity_label = row.get("identity_label", "unknown")
        recognition_confidence = safe_float(
            row.get("recognition_confidence", 0.0),
            default=0.0,
        )

        detector_confidence = safe_float(
            row.get("detector_confidence", 0.0),
            default=0.0,
        )

        display_status = format_status(
            identity_status=identity_status,
            identity_label=identity_label,
            confidence=recognition_confidence,
        )

        item = {
            "time": timestamp,
            "camera": camera_name,
            "track_id": f"F{frame_id}-D{detection_id}",
            "frame_id": safe_int(frame_id, default=0),
            "detection_id": safe_int(detection_id, default=0),
            "identity_status": identity_status,
            "identity_label": identity_label,
            "status": display_status,
            "recognition_confidence": round(recognition_confidence, 4),
            "detector_confidence": round(detector_confidence, 4),
        }

        data.append(item)

    return {
        "status": "ok",
        "message": f"Berhasil membaca {len(data)} deteksi terbaru.",
        "data": data,
    }