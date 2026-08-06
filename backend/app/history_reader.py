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


def _select_candidate_lines(data_lines, date_text):
    """
    Log ditulis berurutan dari waktu ke waktu (append-only), jadi baris
    untuk SATU tanggal selalu menumpuk berurutan di ekor file. Kalau
    date_text diisi, scan dari BELAKANG dan berhenti begitu keluar dari
    tanggal itu - biayanya sebanding dengan jumlah baris HARI ITU, bukan
    seluruh riwayat. Tanpa ini, query "hari ini" ikut membaca ulang
    seluruh log lama setiap kali dipanggil, dan detection_log.csv bisa
    tumbuh ratusan ribu baris setelah berjalan berhari-hari (worker
    menulis satu baris per deteksi per frame).
    """
    if not date_text:
        return data_lines

    candidates = []
    seen_match = False
    for line in reversed(data_lines):
        if line.startswith(date_text):
            candidates.append(line)
            seen_match = True
        elif seen_match:
            break
    candidates.reverse()
    return candidates


def _build_sessions(log_path, date_text):
    path = Path(log_path)
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.readlines()
    except Exception:
        return None

    if not lines:
        return []

    header = next(csv.reader([lines[0]]), None)
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

    candidate_lines = _select_candidate_lines(lines[1:], date_text)

    matched = []
    for row in csv.reader(candidate_lines):
        if not row or ts_i >= len(row):
            continue
        tsval = row[ts_i]
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


def get_attendance_today(log_path=DEFAULT_LOG_PATH):
    """
    Status kehadiran hari ini: jam "verified" pertama & terakhir di
    detection_log.csv - bukan dari kamera/tracking langsung.

    Catatan penting: cuma mencerminkan kamera yang BENAR-BENAR aktif hari
    ini (sistem cuma mengawasi satu kamera sekaligus). "absent" berarti
    belum terdeteksi di kamera yang diawasi, BUKAN bukti orangnya tidak
    ada di gedung.

    Sengaja TIDAK numpang ke _build_sessions(): baris HARI INI SENDIRI
    bisa ratusan ribu (satu baris per orang per frame), jadi endpoint ini
    dipoll dashboard tiap 60 detik tidak boleh ikut menanggung biaya
    regex entry_id + pengelompokan sesi + sorting yang dipakai fitur
    Riwayat Deteksi. Di sini cukup 1x scan cari timestamp verified
    ter-awal/ter-akhir, pakai split string mentah (bukan csv.reader)
    karena kolom log ini tidak pernah butuh quoting.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    absent = {"date": today, "status": "absent", "arrived_at": None, "last_seen": None}

    path = Path(log_path)
    if not path.exists():
        return absent

    try:
        with open(path, encoding="utf-8", newline="") as f:
            lines = f.readlines()
    except Exception:
        return absent

    if not lines:
        return absent

    header = next(csv.reader([lines[0]]), None)
    if not header:
        return absent
    col = {name: i for i, name in enumerate(header)}
    ts_i = col.get("timestamp")
    st_i = col.get("identity_status")
    if ts_i is None or st_i is None:
        return absent

    arrived_at = None
    last_seen = None

    # Log ditulis berurutan dari waktu ke waktu -> baris hari ini
    # menumpuk di ekor file. Scan dari BELAKANG: match pertama yang
    # ketemu = jam TERAKHIR terlihat, match yang terus ditimpa sampai
    # keluar dari tanggal ini = jam PERTAMA terlihat (paling awal).
    seen_today = False
    for line in reversed(lines[1:]):
        if not line.startswith(today):
            if seen_today:
                break
            continue

        seen_today = True
        fields = line.rstrip("\n").split(",")
        if st_i >= len(fields) or ts_i >= len(fields) or fields[st_i] != "verified":
            continue

        tsval = fields[ts_i]
        if last_seen is None:
            last_seen = tsval
        arrived_at = tsval

    if arrived_at is None:
        return absent

    return {"date": today, "status": "present", "arrived_at": arrived_at, "last_seen": last_seen}