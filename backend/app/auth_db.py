"""
app/auth_db.py  (FILE BARU - Tahap Auth 1)

Menyimpan user dan session login di SQLite: data/comvis_auth.db
(folder "data", BUKAN "outputs", supaya tidak ikut terhapus
saat bersih-bersih output).

Keamanan level prototype:
- Password TIDAK disimpan mentah, tapi di-hash PBKDF2-SHA256
  dengan salt berbeda per user (bawaan Python, tanpa install).
- Login menghasilkan session token acak yang kedaluwarsa 12 jam.

Role yang dikenal:
- "user"        : lihat dashboard
- "admin"       : + server monitoring
- "super_admin" : + kelola user
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "comvis_auth.db"

VALID_ROLES = ("user", "admin", "super_admin")
SESSION_HOURS = 12
PBKDF2_ITERATIONS = 200_000

# Panjang password minimal. Sengaja dilonggarkan ke 4 selama masa
# development supaya password sederhana seperti "user" bisa dipakai.
# Sebelum dashboard dipakai orang banyak, kembalikan ke 6 atau lebih.
MIN_PASSWORD_LENGTH = 4

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================
# Koneksi & inisialisasi
# ============================================================

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=2.0)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Membuat tabel + user default kalau database masih kosong."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )

    _seed_default_users()


def _seed_default_users():
    """
    Kalau belum ada user sama sekali, buat 3 akun contoh.
    PENTING: segera ganti password default lewat
    scripts/manage_users.py reset-password
    """
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    if total > 0:
        return

    # Password default = sama dengan username (mudah diingat saat
    # development). GANTI sebelum dipakai orang lain!
    defaults = [
        ("superadmin", "superadmin", "super_admin"),
        ("admin", "admin", "admin"),
        ("user", "user", "user"),
    ]

    for username, password, role in defaults:
        create_user(username, password, role)

    print("=" * 56)
    print("[AUTH] User default dibuat (GANTI PASSWORD-nya segera!):")
    for username, password, role in defaults:
        print(f"       {username:<12} password: {password:<10} role: {role}")
    print("       Ganti via: python scripts/manage_users.py reset-password --username <nama>")
    print("=" * 56)


# ============================================================
# Password hashing
# ============================================================

def _hash_password(password: str, salt_hex: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    )
    return digest.hex()


# ============================================================
# Manajemen user
# ============================================================

def create_user(username: str, password: str, role: str):
    username = username.strip().lower()
    role = role.strip().lower()

    if role not in VALID_ROLES:
        raise ValueError(f"Role tidak dikenal: {role}. Pilihan: {VALID_ROLES}")
    if not username or not password:
        raise ValueError("Username dan password tidak boleh kosong.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password minimal {MIN_PASSWORD_LENGTH} karakter.")

    salt_hex = secrets.token_bytes(16).hex()
    password_hash = _hash_password(password, salt_hex)

    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (username, password_salt, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, salt_hex, password_hash, role,
             datetime.now().strftime(TIME_FORMAT)),
        )


def list_users():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY id"
        ).fetchall()
    return [
        {"id": r[0], "username": r[1], "role": r[2], "created_at": r[3]}
        for r in rows
    ]


def set_password(username: str, new_password: str):
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password minimal {MIN_PASSWORD_LENGTH} karakter.")
    salt_hex = secrets.token_bytes(16).hex()
    password_hash = _hash_password(new_password, salt_hex)
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE users SET password_salt = ?, password_hash = ? WHERE username = ?",
            (salt_hex, password_hash, username.strip().lower()),
        )
        if cur.rowcount == 0:
            raise ValueError(f"User tidak ditemukan: {username}")


def set_role(username: str, role: str):
    role = role.strip().lower()
    if role not in VALID_ROLES:
        raise ValueError(f"Role tidak dikenal: {role}. Pilihan: {VALID_ROLES}")
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            (role, username.strip().lower()),
        )
        if cur.rowcount == 0:
            raise ValueError(f"User tidak ditemukan: {username}")


def delete_user(username: str):
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
        if row is None:
            raise ValueError(f"User tidak ditemukan: {username}")
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row[0],))
        conn.execute("DELETE FROM users WHERE id = ?", (row[0],))


# ============================================================
# Login & session
# ============================================================

def verify_login(username: str, password: str):
    """Return dict user kalau username+password benar, selain itu None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_salt, password_hash, role "
            "FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()

    if row is None:
        return None

    user_id, uname, salt_hex, stored_hash, role = row
    calculated = _hash_password(password, salt_hex)

    # compare_digest: perbandingan aman terhadap timing attack
    if not secrets.compare_digest(calculated, stored_hash):
        return None

    return {"id": user_id, "username": uname, "role": role}


def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = datetime.now() + timedelta(hours=SESSION_HOURS)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.strftime(TIME_FORMAT)),
        )
    return token


def get_user_by_token(token: str):
    """Return user kalau token valid & belum kedaluwarsa, selain itu None."""
    if not token:
        return None

    with _connect() as conn:
        row = conn.execute(
            """
            SELECT s.expires_at, u.id, u.username, u.role
            FROM sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()

        if row is None:
            return None

        expires_at, user_id, username, role = row

        if datetime.strptime(expires_at, TIME_FORMAT) < datetime.now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

    return {"id": user_id, "username": username, "role": role}


def delete_session(token: str):
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))