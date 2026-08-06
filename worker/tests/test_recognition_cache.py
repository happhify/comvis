import pytest

from src.recognition_cache import RecognitionCache, calculate_iou


# ============================================================
# calculate_iou
# ============================================================

def test_iou_identical_boxes_is_one():
    box = (10, 10, 50, 50)
    assert calculate_iou(box, box) == pytest.approx(1.0)


def test_iou_non_overlapping_boxes_is_zero():
    box_a = (0, 0, 10, 10)
    box_b = (100, 100, 110, 110)
    assert calculate_iou(box_a, box_b) == 0.0


def test_iou_partial_overlap():
    box_a = (0, 0, 10, 10)
    box_b = (5, 0, 15, 10)
    # Intersection 5x10=50, union 100+100-50=150 -> 1/3
    assert abs(calculate_iou(box_a, box_b) - (1 / 3)) < 1e-6


# ============================================================
# get_or_create_entry
# ============================================================

def test_new_bbox_creates_new_entry():
    cache = RecognitionCache()
    entry_id, entry, is_new = cache.get_or_create_entry(bbox=(0, 0, 50, 100), frame_id=1)
    assert is_new is True
    assert entry_id == 1
    assert entry.bbox == (0, 0, 50, 100)


def test_overlapping_bbox_reuses_existing_entry():
    cache = RecognitionCache(iou_threshold=0.35)
    entry_id_1, _, _ = cache.get_or_create_entry(bbox=(0, 0, 100, 100), frame_id=1)
    # Geser sedikit (masih overlap tinggi) -> harus dianggap orang yang sama
    entry_id_2, entry, is_new = cache.get_or_create_entry(bbox=(5, 5, 105, 105), frame_id=2)

    assert is_new is False
    assert entry_id_2 == entry_id_1
    assert entry.frame_id == 2  # bbox/frame_id ter-update


def test_far_away_bbox_creates_separate_entry():
    cache = RecognitionCache(iou_threshold=0.35)
    id_1, _, _ = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    id_2, _, is_new = cache.get_or_create_entry(bbox=(500, 500, 550, 550), frame_id=1)

    assert is_new is True
    assert id_2 != id_1


def test_expired_entry_is_not_matched():
    cache = RecognitionCache(cache_ttl_frames=5, iou_threshold=0.35)
    id_1, _, _ = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    # Frame jauh di depan, sudah lewat TTL -> tidak boleh nyambung ke entry lama
    id_2, _, is_new = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=10)

    assert is_new is True
    assert id_2 != id_1


# ============================================================
# should_run_recognition
# ============================================================

def test_should_run_recognition_true_on_first_time():
    cache = RecognitionCache(recognition_interval=10)
    _, entry, _ = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    assert cache.should_run_recognition(entry, frame_id=1) is True


def test_should_run_recognition_false_within_interval():
    cache = RecognitionCache(recognition_interval=10)
    entry_id, entry, _ = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    cache.update_recognition(
        entry_id=entry_id, bbox=(0, 0, 50, 50), frame_id=1,
        identity_status="verified", identity_label="hadi",
        recognition_confidence=0.98, recognition_margin=0.5,
    )
    assert cache.should_run_recognition(entry, frame_id=5) is False


def test_should_run_recognition_true_after_interval_elapsed():
    cache = RecognitionCache(recognition_interval=10)
    entry_id, entry, _ = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    cache.update_recognition(
        entry_id=entry_id, bbox=(0, 0, 50, 50), frame_id=1,
        identity_status="verified", identity_label="hadi",
        recognition_confidence=0.98, recognition_margin=0.5,
    )
    assert cache.should_run_recognition(entry, frame_id=11) is True


# ============================================================
# cleanup
# ============================================================

def test_cleanup_removes_expired_entries_only():
    cache = RecognitionCache(cache_ttl_frames=5)
    cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    cache.get_or_create_entry(bbox=(500, 500, 550, 550), frame_id=10)

    cache.cleanup(current_frame_id=10)

    remaining_frame_ids = [e.frame_id for e in cache.entries.values()]
    assert remaining_frame_ids == [10]


# ============================================================
# get_active_persons
# ============================================================

def test_get_active_persons_sorted_by_duration_desc():
    cache = RecognitionCache()
    id_1, entry_1, _ = cache.get_or_create_entry(bbox=(0, 0, 50, 50), frame_id=1)
    entry_1.first_seen_ts -= 100  # orang ini sudah lama di frame

    id_2, entry_2, _ = cache.get_or_create_entry(bbox=(500, 500, 550, 550), frame_id=1)
    entry_2.first_seen_ts -= 5  # orang ini baru masuk

    people = cache.get_active_persons()

    assert [p["entry_id"] for p in people] == [id_1, id_2]
    assert people[0]["duration_seconds"] >= people[1]["duration_seconds"]


def test_get_active_persons_respects_limit():
    cache = RecognitionCache()
    for i in range(5):
        cache.get_or_create_entry(bbox=(i * 100, 0, i * 100 + 50, 50), frame_id=1)

    people = cache.get_active_persons(limit=2)
    assert len(people) == 2
