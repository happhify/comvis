import csv

from app.history_reader import history_rows_for_csv, read_history

HEADER = [
    "timestamp", "camera_name", "source_type", "frame_id", "detection_id",
    "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "bbox_width", "bbox_height",
    "detector_label", "detector_confidence", "identity_label", "identity_status",
    "recognition_confidence", "recognition_margin", "from_cache",
    "crop_width", "crop_height", "note",
]


def make_row(timestamp, entry_id, status="verified", label="hadi",
             confidence=0.98, camera="kamera_1"):
    return [
        timestamp, camera, "rtsp", 1, 0,
        10, 20, 60, 120, 50, 100,
        "person", 0.9, label, status,
        confidence, 0.5, False,
        50, 100, f"cache_entry_id={entry_id}",
    ]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)


# ============================================================
# read_history - kasus dasar
# ============================================================

def test_read_history_missing_file_returns_warning(tmp_path):
    result = read_history(log_path=tmp_path / "nope.csv")
    assert result["status"] == "warning"
    assert result["data"] == []


def test_read_history_groups_same_entry_id_into_one_session(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1),
        make_row("2026-08-06 08:00:10", entry_id=1),
        make_row("2026-08-06 08:00:20", entry_id=1),
    ])

    result = read_history(log_path=log_path)

    assert result["total"] == 1
    session = result["data"][0]
    assert session["first_seen"] == "2026-08-06 08:00:00"
    assert session["last_seen"] == "2026-08-06 08:00:20"
    assert session["duration_seconds"] == 20
    assert session["frames"] == 3
    assert session["identity_status"] == "verified"
    assert session["status"] == "Employee: Hadi"


def test_read_history_splits_session_on_large_time_gap(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1),
        # >120 detik kemudian -> dianggap kemunculan baru, bukan sesi yang sama
        make_row("2026-08-06 08:10:00", entry_id=1),
    ])

    result = read_history(log_path=log_path)

    assert result["total"] == 2


def test_read_history_different_entry_ids_are_separate_sessions(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1),
        make_row("2026-08-06 08:00:05", entry_id=2),
    ])

    result = read_history(log_path=log_path)
    assert result["total"] == 2


def test_read_history_filters_by_date_prefix(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-05 08:00:00", entry_id=1),
        make_row("2026-08-06 08:00:00", entry_id=2),
    ])

    result = read_history(date_text="2026-08-06", log_path=log_path)
    assert result["total"] == 1
    assert result["data"][0]["first_seen"].startswith("2026-08-06")


def test_read_history_filters_by_status(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1, status="verified"),
        make_row("2026-08-06 08:05:00", entry_id=2, status="unknown"),
    ])

    result = read_history(status="unknown", log_path=log_path)
    assert result["total"] == 1
    assert result["data"][0]["identity_status"] == "unknown"


def test_read_history_pagination(tmp_path):
    log_path = tmp_path / "log.csv"
    rows = [
        make_row(f"2026-08-06 08:{i:02d}:00", entry_id=i)
        for i in range(5)
    ]
    write_csv(log_path, rows)

    page = read_history(limit=2, offset=1, log_path=log_path)
    assert page["total"] == 5
    assert len(page["data"]) == 2


def test_read_history_sorted_most_recent_first(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1),
        make_row("2026-08-06 09:00:00", entry_id=2),
    ])

    result = read_history(log_path=log_path)
    first_seen_times = [s["first_seen"] for s in result["data"]]
    assert first_seen_times == sorted(first_seen_times, reverse=True)


def test_display_label_for_unknown_status(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1, status="unknown", label="unknown"),
    ])

    result = read_history(log_path=log_path)
    assert result["data"][0]["status"] == "Unknown"


# ============================================================
# history_rows_for_csv (dipakai fitur export)
# ============================================================

def test_history_rows_for_csv_respects_status_filter(tmp_path):
    log_path = tmp_path / "log.csv"
    write_csv(log_path, [
        make_row("2026-08-06 08:00:00", entry_id=1, status="verified"),
        make_row("2026-08-06 08:05:00", entry_id=2, status="unknown"),
    ])

    rows = history_rows_for_csv(status="verified", log_path=log_path)
    assert len(rows) == 1
    assert rows[0]["identity_status"] == "verified"
