import csv

import main as worker_main


# ============================================================
# format_display_label
# ============================================================

def test_format_display_label_verified_shows_hadi():
    label = worker_main.format_display_label("verified", entry_id=12, confidence=0.981)
    assert label == "Hadi #12 0.98"


def test_format_display_label_unknown_shows_unknown():
    label = worker_main.format_display_label("unknown", entry_id=7, confidence=0.634)
    assert label == "Unknown #7 0.63"


# ============================================================
# find_camera
# ============================================================

def test_find_camera_returns_matching_entry():
    cameras = [{"id": "kamera_1", "name": "A"}, {"id": "kamera_2", "name": "B"}]
    result = worker_main.find_camera(cameras, "kamera_2")
    assert result == {"id": "kamera_2", "name": "B"}


def test_find_camera_returns_none_when_not_found():
    cameras = [{"id": "kamera_1", "name": "A"}]
    assert worker_main.find_camera(cameras, "kamera_99") is None


# ============================================================
# resolve_rtsp_url
# ============================================================

def test_resolve_rtsp_url_reads_from_env(monkeypatch):
    monkeypatch.setenv("RTSP_URL_TEST", "rtsp://example.com/stream")
    camera = {"id": "kamera_1", "rtsp_env_key": "RTSP_URL_TEST"}
    assert worker_main.resolve_rtsp_url(camera) == "rtsp://example.com/stream"


def test_resolve_rtsp_url_returns_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("RTSP_URL_UNSET", raising=False)
    camera = {"id": "kamera_1", "rtsp_env_key": "RTSP_URL_UNSET"}
    assert worker_main.resolve_rtsp_url(camera) is None


def test_resolve_rtsp_url_returns_none_when_env_blank(monkeypatch):
    monkeypatch.setenv("RTSP_URL_BLANK", "   ")
    camera = {"id": "kamera_1", "rtsp_env_key": "RTSP_URL_BLANK"}
    assert worker_main.resolve_rtsp_url(camera) is None


# ============================================================
# write_detection_log / init_log_file - format CSV harus konsisten
# karena backend/app/history_reader.py membaca kolom-kolom ini by name.
# ============================================================

def test_detection_log_round_trip(tmp_path):
    log_path = str(tmp_path / "detection_log.csv")
    worker_main.init_log_file(log_path)

    detections = [
        {
            "bbox": (10, 20, 60, 120),
            "confidence": 0.9,
            "identity_raw_label": "hadi",
            "status": "verified",
            "identity_confidence": 0.98,
            "identity_margin": 0.5,
            "from_cache": False,
            "cache_entry_id": 3,
        }
    ]

    worker_main.write_detection_log(
        log_path=log_path, camera_name="kamera_1", source_type="rtsp",
        frame_id=42, detections=detections,
    )

    with open(log_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    row = rows[0]
    assert row["camera_name"] == "kamera_1"
    assert row["frame_id"] == "42"
    assert row["identity_label"] == "hadi"
    assert row["identity_status"] == "verified"
    assert row["note"] == "cache_entry_id=3"
