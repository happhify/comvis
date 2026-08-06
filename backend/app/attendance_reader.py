"""
app/attendance_reader.py

Status kehadiran hari ini untuk SEMUA pegawai di config/employees.yaml.

Classifier saat ini cuma bisa membedakan "hadi" vs "unknown", jadi baru
pegawai dengan source="real" (Hadi) yang statusnya dihitung dari data
deteksi sungguhan (detection_log.csv). Pegawai lain (source="dummy")
pakai nilai tetap dari employees.yaml sebagai placeholder, sampai
classifier-nya di-retrain jadi multi-kelas dan bisa mengenali mereka.

Field "source" ikut dikirim ke frontend supaya dashboard bisa menandai
mana data asli dan mana yang masih dummy - jangan disamarkan.
"""

from datetime import datetime
from pathlib import Path

import yaml

from app.history_reader import DEFAULT_LOG_PATH, get_attendance_today

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMPLOYEES_CONFIG_PATH = PROJECT_ROOT / "config" / "employees.yaml"


def _read_employees_config(path=EMPLOYEES_CONFIG_PATH):
    path = Path(path)
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return []

    return cfg.get("employees") or []


def _dummy_attendance(employee, today):
    def with_today(hhmm):
        return f"{today} {hhmm}:00" if hhmm else None

    return {
        "id": employee.get("id"),
        "name": employee.get("name", employee.get("id")),
        "source": "dummy",
        "status": employee.get("dummy_status", "absent"),
        "arrived_at": with_today(employee.get("dummy_arrived_at")),
        "last_seen": with_today(employee.get("dummy_last_seen")),
    }


def get_attendance_today_all(
    employees_config_path=EMPLOYEES_CONFIG_PATH,
    log_path=DEFAULT_LOG_PATH,
):
    """Dipanggil endpoint /api/attendance-today."""
    today = datetime.now().strftime("%Y-%m-%d")
    employees = _read_employees_config(employees_config_path)

    real_attendance = None  # dihitung sekali saja, dipakai bareng semua source="real"

    rows = []
    for employee in employees:
        if employee.get("source") == "real":
            if real_attendance is None:
                real_attendance = get_attendance_today(log_path=log_path)
            rows.append({
                "id": employee.get("id"),
                "name": employee.get("name", employee.get("id")),
                "source": "real",
                "status": real_attendance["status"],
                "arrived_at": real_attendance["arrived_at"],
                "last_seen": real_attendance["last_seen"],
            })
        else:
            rows.append(_dummy_attendance(employee, today))

    return {"date": today, "employees": rows}
