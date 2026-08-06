from datetime import datetime, timedelta

from app.shared_state import STALE_AFTER_SECONDS, SharedState


# ============================================================
# Frame handling
# ============================================================

def test_update_and_get_latest_frame():
    state = SharedState()
    state.update_frame(b"jpegbytes")
    assert state.get_latest_frame() == b"jpegbytes"


def test_update_frame_ignores_empty_payload():
    state = SharedState()
    state.update_frame(b"first")
    state.update_frame(b"")  # kosong -> harus diabaikan, bukan menimpa
    assert state.get_latest_frame() == b"first"


def test_frame_status_counts_updates():
    state = SharedState()
    assert state.get_frame_status()["has_frame"] is False

    state.update_frame(b"a")
    state.update_frame(b"b")
    status = state.get_frame_status()
    assert status["has_frame"] is True
    assert status["frame_counter"] == 2


# ============================================================
# Stats handling
# ============================================================

def test_update_stats_fills_defaults_for_missing_keys():
    state = SharedState()
    state.update_stats({"camera_name": "kamera_2"})
    stats = state.get_stats()
    assert stats["camera_name"] == "kamera_2"
    assert stats["camera_status"] == "LIVE"
    assert stats["people_in_frame"] == 0


def test_update_stats_ignores_empty_payload():
    state = SharedState()
    state.update_stats({"camera_name": "kamera_2"})
    state.update_stats({})
    assert state.get_stats()["camera_name"] == "kamera_2"


def test_stats_marked_waiting_when_stale():
    state = SharedState()
    state.update_stats({"camera_status": "LIVE"})

    # Paksa last_update jadi lebih tua dari batas stale
    with state._lock:
        old_time = datetime.now() - timedelta(seconds=STALE_AFTER_SECONDS + 5)
        state._stats["last_update"] = old_time.strftime("%Y-%m-%d %H:%M:%S")

    stats = state.get_stats()
    assert stats["camera_status"] == "WAITING"
    assert stats["stale_seconds"] >= STALE_AFTER_SECONDS


def test_stats_stay_live_when_fresh():
    state = SharedState()
    state.update_stats({"camera_status": "LIVE"})
    stats = state.get_stats()
    assert stats["camera_status"] == "LIVE"


# ============================================================
# Control handling
# ============================================================

def test_control_defaults():
    state = SharedState()
    assert state.get_control() == {"detection_enabled": True, "camera_id": None}


def test_set_control_updates_detection_enabled():
    state = SharedState()
    state.set_control({"detection_enabled": False})
    assert state.get_control()["detection_enabled"] is False


def test_set_control_updates_camera_id():
    state = SharedState()
    state.set_control({"camera_id": "kamera_2"})
    assert state.get_control()["camera_id"] == "kamera_2"


def test_set_control_ignores_unknown_keys():
    state = SharedState()
    state.set_control({"admin_override": True, "camera_id": "kamera_2"})
    control = state.get_control()
    assert "admin_override" not in control
    assert control["camera_id"] == "kamera_2"


def test_set_control_ignores_none_and_empty_camera_id():
    state = SharedState()
    state.set_control({"camera_id": "kamera_2"})
    state.set_control({"camera_id": None})
    state.set_control({"camera_id": ""})
    # camera_id None/"" tidak boleh menimpa nilai yang sudah ada
    assert state.get_control()["camera_id"] == "kamera_2"


def test_set_control_with_empty_dict_is_noop():
    state = SharedState()
    state.set_control({"camera_id": "kamera_2"})
    state.set_control({})
    assert state.get_control()["camera_id"] == "kamera_2"
