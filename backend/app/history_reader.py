"""
app/history_reader.py  (Fitur Riwayat Deteksi)

Mengubah detection_log.csv (satu baris PER FRAME) menjadi daftar KEJADIAN:
satu baris per orang per sesi (jam masuk, keluar, durasi, status, keyakinan).

Dioptimalkan untuk log besar: filter tanggal memakai perbandingan TEKS
(prefix) lebih dulu, sehingga parsing datetime hanya dilakukan pada baris
hari yang diminta - bukan seluruh log.
"""

import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = PROJECT_ROOT / "outputs" / "logs" / "detection_log.csv"

SESSION_GAP_SECONDS = 120
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _safe_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def _parse_ts(s):
    try:
        return datetime.strptime(str(s).strip(), TIME_FMT)
    except Exception:
        return None


def _entry_id(note):
    m = re.search(r"cache_entry_id\s*=\s*(\d+)", str(note or ""))
    return int(m.group(1)) if m else None


def _display(status, label):
    status = str(status or "unverified").lower()
    label = str(label or "").strip()
    if status == "verified":
        if label and label not in ("unknown", "small_crop", "empty_crop"):
            return f"Employee: {label.capitalize()}"
        return "Employee"
    if status == "unknown":
        return "Unknown"
    return "Unverified"


def _make_session(eid, items):
    ts_list = [ts for ts, _ in items]
    statuses = [str(r.get("identity_status", "unverified")).lower() for _, r in items]
    labels = [str(r.get("identity_label", "")).lower() for _, r in items]

    status = Counter(statuses).most_common(1)[0][0]
    same = [l for s, l in zip(statuses, labels) if s == status and l]
    label = Counter(same).most_common(1)[0][0] if same else ""
    confs = [_safe_float(r.get("recognition_confidence")) for _, r in items]
    first, last = min(ts_list), max(ts_list)

    return {
        "entry_id": eid if (eid is not None and eid >= 0) else None,
        "first_seen": first.strftime(TIME_FMT),
        "last_seen": last.strftime(TIME_FMT),
        "duration_seconds": int((last - first).total_seconds()),
        "camera": items[0][1].get("camera_name", "kamera_1"),
        "identity_status": status,
        "identity_label": label,
        "status": _display(status, label),
        "confidence": round(max(confs) if confs else 0.0, 4),
        "frames": len(items),
    }


def _build_sessions(log_path, date_text):
    path = Path(log_path)
    if not path.exists():
        return None

    matched = []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return []
            col = {name: i for i, name in enumerate(header)}
            ts_i = col.get("timestamp")
            if ts_i is None:
                return []
            st_i = col.get("identity_status")
            lb_i = col.get("identity_label")
            cf_i = col.get("recognition_confidence")
            cam_i = col.get("camera_name")
            nt_i = col.get("note")

            def get(row, i):
                return row[i] if (i is not None and i < len(row)) else ""

            for row in reader:
                if ts_i >= len(row):
                    continue
                tsval = row[ts_i]
                # filter tanggal via TEKS dulu (murah) sebelum parsing
                if date_text and not tsval.startswith(date_text):
                    continue
                ts = _parse_ts(tsval)
                if ts is None:
                    continue
                matched.append((ts, {
                    "identity_status": get(row, st_i),
                    "identity_label": get(row, lb_i),
                    "recognition_confidence": get(row, cf_i),
                    "camera_name": get(row, cam_i) or "kamera_1",
                    "note": get(row, nt_i),
                }))
    except Exception:
        return None

    groups = {}
    for ts, r in matched:
        eid = _entry_id(r.get("note"))
        groups.setdefault(eid if eid is not None else -1, []).append((ts, r))

    sessions = []
    for eid, items in groups.items():
        items.sort(key=lambda x: x[0])
        cur, last = [], None
        for ts, r in items:
            if last is not None and (ts - last).total_seconds() > SESSION_GAP_SECONDS:
                sessions.append(_make_session(eid, cur))
                cur = []
            cur.append((ts, r))
            last = ts
        if cur:
            sessions.append(_make_session(eid, cur))

    sessions.sort(key=lambda s: s["first_seen"], reverse=True)
    return sessions


def read_history(date_text=None, status="all", limit=50, offset=0,
                 log_path=DEFAULT_LOG_PATH):
    sessions = _build_sessions(log_path, date_text)
    if sessions is None:
        return {"status": "warning", "message": "detection_log.csv belum tersedia.",
                "total": 0, "data": []}

    status = (status or "all").lower()
    if status != "all":
        sessions = [s for s in sessions if s["identity_status"] == status]

    total = len(sessions)
    offset = max(0, int(offset))
    limit = max(1, min(int(limit), 200))
    return {"status": "ok", "total": total, "limit": limit, "offset": offset,
            "data": sessions[offset:offset + limit]}


def history_rows_for_csv(date_text=None, status="all", log_path=DEFAULT_LOG_PATH):
    sessions = _build_sessions(log_path, date_text) or []
    status = (status or "all").lower()
    if status != "all":
        sessions = [s for s in sessions if s["identity_status"] == status]
    return sessions