"""
app/daily_stats_reader.py  (Tahap Database)

Membaca outputs/comvis_stats.db dan merangkum:
- jumlah orang per HARI  -> read_daily_stats  (endpoint /api/daily-stats)
- jumlah orang per JAM   -> read_hourly_stats (endpoint /api/hourly-stats)

Dibuat aman: kalau database belum ada -> return list kosong, jangan error.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "outputs" / "comvis_stats.db"


def read_daily_stats(days=14, db_path=DB_PATH):
    path = Path(db_path)

    if not path.exists():
        return {
            "status": "warning",
            "message": "Database belum ada. Data mulai terkumpul saat main.py berjalan.",
            "data": [],
        }

    try:
        conn = sqlite3.connect(path, timeout=2.0)
        try:
            cursor = conn.execute(
                """
                SELECT date, COUNT(*) AS total
                FROM person_events
                GROUP BY date
                ORDER BY date DESC
                LIMIT ?
                """,
                (int(days),),
            )
            data = [
                {"date": row[0], "count": int(row[1])}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    except sqlite3.Error as error:
        return {
            "status": "error",
            "message": f"Gagal membaca database: {error}",
            "data": [],
        }

    return {"status": "ok", "data": data}


def read_hourly_stats(date_text=None, db_path=DB_PATH):
    """
    Jumlah orang per jam (0-23) untuk SATU tanggal.
    - date_text kosong -> pakai hari ini.
    - Belum ada data    -> data kosong + pesan (dashboard tampilkan "Belum ada data").
    - Ada data          -> 24 baris {hour, count}; jam tanpa data tetap 0
                           supaya grafik selalu punya 24 batang yang rapi.
    """
    path = Path(db_path)

    # Default tanggal = hari ini (format sama dengan kolom "date")
    if not date_text:
        date_text = datetime.now().strftime("%Y-%m-%d")

    if not path.exists():
        return {
            "status": "warning",
            "message": "Database belum ada. Data mulai terkumpul saat main.py berjalan.",
            "date": date_text,
            "data": [],
        }

    try:
        conn = sqlite3.connect(path, timeout=2.0)
        try:
            cursor = conn.execute(
                """
                SELECT CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
                       COUNT(*) AS total
                FROM person_events
                WHERE date = ?
                GROUP BY hour
                ORDER BY hour
                """,
                (date_text,),
            )
            counts = {int(row[0]): int(row[1]) for row in cursor.fetchall()}
        finally:
            conn.close()

    except sqlite3.Error as error:
        return {
            "status": "error",
            "message": f"Gagal membaca database: {error}",
            "date": date_text,
            "data": [],
        }

    # Tidak ada satu pun kejadian di tanggal ini
    if sum(counts.values()) == 0:
        return {
            "status": "ok",
            "message": "Belum ada data untuk tanggal ini.",
            "date": date_text,
            "data": [],
        }

    # 24 baris jam, jam kosong diisi 0
    data = [{"hour": h, "count": counts.get(h, 0)} for h in range(24)]
    return {"status": "ok", "date": date_text, "data": data}