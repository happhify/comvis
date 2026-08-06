import csv
from datetime import datetime

import yaml

from app.attendance_reader import get_attendance_today_all

TODAY = datetime.now().strftime("%Y-%m-%d")

LOG_HEADER = [
    "timestamp", "camera_name", "source_type", "frame_id", "detection_id",
    "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "bbox_width", "bbox_height",
    "detector_label", "detector_confidence", "identity_label", "identity_status",
    "recognition_confidence", "recognition_margin", "from_cache",
    "crop_width", "crop_height", "note",
]


def write_log(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(LOG_HEADER)
        writer.writerows(rows)


def log_row(timestamp, entry_id, status="verified"):
    return [
        timestamp, "kamera_1", "rtsp", 1, 0,
        10, 20, 60, 120, 50, 100,
        "person", 0.9, "hadi", status,
        0.98, 0.5, False,
        50, 100, f"cache_entry_id={entry_id}",
    ]


def write_employees_config(path, employees):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"employees": employees}, f)


def test_missing_employees_config_returns_empty_list(tmp_path):
    result = get_attendance_today_all(
        employees_config_path=tmp_path / "nope.yaml",
        log_path=tmp_path / "log.csv",
    )
    assert result == {"date": TODAY, "employees": []}


def test_dummy_employee_uses_static_config_values(tmp_path):
    config_path = tmp_path / "employees.yaml"
    write_employees_config(config_path, [
        {
            "id": "karyawan_2", "name": "Karyawan 2", "source": "dummy",
            "dummy_status": "present",
            "dummy_arrived_at": "08:05",
            "dummy_last_seen": "12:40",
        },
    ])

    result = get_attendance_today_all(
        employees_config_path=config_path,
        log_path=tmp_path / "log.csv",
    )

    assert result["employees"] == [{
        "id": "karyawan_2",
        "name": "Karyawan 2",
        "source": "dummy",
        "status": "present",
        "arrived_at": f"{TODAY} 08:05:00",
        "last_seen": f"{TODAY} 12:40:00",
    }]


def test_dummy_employee_absent_has_null_times(tmp_path):
    config_path = tmp_path / "employees.yaml"
    write_employees_config(config_path, [
        {
            "id": "karyawan_3", "name": "Karyawan 3", "source": "dummy",
            "dummy_status": "absent",
            "dummy_arrived_at": None,
            "dummy_last_seen": None,
        },
    ])

    result = get_attendance_today_all(
        employees_config_path=config_path,
        log_path=tmp_path / "log.csv",
    )

    row = result["employees"][0]
    assert row["status"] == "absent"
    assert row["arrived_at"] is None
    assert row["last_seen"] is None


def test_real_employee_computed_from_detection_log(tmp_path):
    config_path = tmp_path / "employees.yaml"
    write_employees_config(config_path, [
        {"id": "hadi", "name": "Hadi", "source": "real"},
    ])

    log_path = tmp_path / "log.csv"
    write_log(log_path, [log_row(f"{TODAY} 08:15:00", entry_id=1)])

    result = get_attendance_today_all(
        employees_config_path=config_path, log_path=log_path,
    )

    row = result["employees"][0]
    assert row["source"] == "real"
    assert row["status"] == "present"
    assert row["arrived_at"] == f"{TODAY} 08:15:00"


def test_real_employee_absent_when_no_detection_log(tmp_path):
    config_path = tmp_path / "employees.yaml"
    write_employees_config(config_path, [
        {"id": "hadi", "name": "Hadi", "source": "real"},
    ])

    result = get_attendance_today_all(
        employees_config_path=config_path, log_path=tmp_path / "nope.csv",
    )

    row = result["employees"][0]
    assert row["status"] == "absent"


def test_mixed_real_and_dummy_employees_preserve_order(tmp_path):
    config_path = tmp_path / "employees.yaml"
    write_employees_config(config_path, [
        {"id": "hadi", "name": "Hadi", "source": "real"},
        {
            "id": "karyawan_2", "name": "Karyawan 2", "source": "dummy",
            "dummy_status": "present", "dummy_arrived_at": "08:00",
            "dummy_last_seen": "17:00",
        },
    ])
    log_path = tmp_path / "log.csv"
    write_log(log_path, [log_row(f"{TODAY} 09:00:00", entry_id=1)])

    result = get_attendance_today_all(
        employees_config_path=config_path, log_path=log_path,
    )

    ids = [e["id"] for e in result["employees"]]
    assert ids == ["hadi", "karyawan_2"]
    assert result["employees"][0]["source"] == "real"
    assert result["employees"][1]["source"] == "dummy"
