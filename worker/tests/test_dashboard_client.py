"""
enabled=False supaya thread pengirim HTTP tidak ikut nyala saat test
(kita cuma mau test transformasi data-nya, bukan network call-nya).
"""
from src.dashboard_client import DashboardFrameClient


def make_client():
    return DashboardFrameClient(enabled=False)


def test_stats_payload_counts_verified_as_employee_active():
    client = make_client()
    detections = [
        {"status": "verified"},
        {"status": "verified"},
        {"status": "unknown"},
    ]

    payload = client._build_stats_payload(
        camera_name="kamera_1", source_type="rtsp", frame_id=100, fps=25.0,
        detections=detections, total_detections=50,
    )

    assert payload["employee_active"] == 2
    assert payload["unknown_active"] == 1
    assert payload["people_in_frame"] == 3
    assert payload["camera_status"] == "LIVE"


def test_stats_payload_treats_missing_status_as_unknown():
    client = make_client()
    detections = [{}]  # tidak ada key "status" sama sekali

    payload = client._build_stats_payload(
        camera_name="kamera_1", source_type="rtsp", frame_id=1, fps=0.0,
        detections=detections, total_detections=0,
    )

    assert payload["employee_active"] == 0
    assert payload["unknown_active"] == 1


def test_submit_frame_noop_when_disabled():
    client = make_client()
    client.submit_frame(frame=object(), frame_id=5)
    assert client.frame_queue.empty()


def test_submit_stats_noop_when_disabled():
    client = make_client()
    client.submit_stats(
        camera_name="kamera_1", source_type="rtsp", frame_id=5, fps=10.0,
        detections=[], total_detections=0,
    )
    assert client.stats_queue.empty()


def test_get_control_default_before_any_response():
    client = make_client()
    assert client.get_control() == {"detection_enabled": True}
