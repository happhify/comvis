"""
src/daily_stats_db.py  (FILE BARU - Tahap Database)

Menyimpan kejadian "orang baru terdeteksi" ke database SQLite.

Kenapa SQLite?
- Database sungguhan (bisa di-query SQL), tapi tanpa install server.
- Cuma satu file: outputs/comvis_stats.db
- Sudah bawaan Python (import sqlite3), tidak perlu pip install.

Yang disimpan BUKAN setiap frame (itu tugas detection_log.csv),
melainkan 1 baris setiap ada ORANG BARU masuk tracking.
Sinyalnya sama dengan kartu "Orang unik" di dashboard.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


class DailyStatsDB:
    def __init__(self, db_path="outputs/comvis_stats.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self):
        # timeout: kalau file sedang dipakai proses lain, tunggu max 2 detik
        conn = sqlite3.connect(self.db_path, timeout=2.0)
        # WAL = mode journal yang aman untuk 1 penulis + banyak pembaca
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_table(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS person_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    date TEXT NOT NULL,
                    camera_name TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_person_events_date "
                "ON person_events(date)"
            )

    def record_new_persons(self, camera_name, count=1):
        """
        Mencatat 'count' orang baru. Dipanggil dari main.py setiap kali
        angka orang unik bertambah. Sengaja menelan error database:
        pencatatan statistik tidak boleh membuat deteksi ikut crash.
        """
        if count <= 0:
            return

        now = datetime.now()
        rows = [
            (
                now.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d"),
                str(camera_name),
            )
        ] * int(count)

        try:
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO person_events (timestamp, date, camera_name) "
                    "VALUES (?, ?, ?)",
                    rows,
                )
        except sqlite3.Error as error:
            print(f"[WARNING] Gagal menulis daily stats DB: {error}")