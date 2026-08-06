import numpy as np

from src.utils import crop_bbox, ensure_dir, resize_frame_by_width


def make_frame(height=200, width=300):
    return np.zeros((height, width, 3), dtype=np.uint8)


# ============================================================
# resize_frame_by_width
# ============================================================

def test_resize_keeps_aspect_ratio():
    frame = make_frame(height=200, width=400)
    resized = resize_frame_by_width(frame, target_width=200)
    assert resized.shape[1] == 200
    assert resized.shape[0] == 100  # 200/400 * 200 = 100


def test_resize_noop_when_frame_already_narrower():
    frame = make_frame(height=100, width=150)
    resized = resize_frame_by_width(frame, target_width=960)
    assert resized.shape == frame.shape


def test_resize_returns_none_for_none_frame():
    assert resize_frame_by_width(None, target_width=960) is None


def test_resize_noop_when_target_width_invalid():
    frame = make_frame()
    assert resize_frame_by_width(frame, target_width=0) is frame
    assert resize_frame_by_width(frame, target_width=None) is frame


# ============================================================
# crop_bbox
# ============================================================

def test_crop_bbox_extracts_region():
    frame = make_frame(height=100, width=100)
    crop = crop_bbox(frame, (10, 20, 60, 80))
    assert crop.shape[:2] == (60, 50)  # (y2-y1, x2-x1)


def test_crop_bbox_clamps_to_frame_bounds():
    frame = make_frame(height=100, width=100)
    crop = crop_bbox(frame, (-50, -50, 500, 500))
    assert crop.shape[:2] == (100, 100)


# ============================================================
# ensure_dir
# ============================================================

def test_ensure_dir_creates_missing_directory(tmp_path):
    target = tmp_path / "nested" / "dir"
    assert not target.exists()
    ensure_dir(str(target))
    assert target.exists()


def test_ensure_dir_noop_when_already_exists(tmp_path):
    ensure_dir(str(tmp_path))  # sudah ada, tidak boleh error
    assert tmp_path.exists()
