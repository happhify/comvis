"""
scripts/manage_users.py  (FILE BARU - Tahap Auth 1)

Alat kelola user dashboard dari terminal (sebelum ada UI kelola user).

Contoh pakai (dari D:\Projects\comvis):
    python scripts/manage_users.py list
    python scripts/manage_users.py add --username budi --role user
    python scripts/manage_users.py reset-password --username admin
    python scripts/manage_users.py set-role --username budi --role admin
    python scripts/manage_users.py delete --username budi

Password diminta lewat prompt tersembunyi (tidak terlihat saat diketik).
"""

import argparse
import getpass
import sys
from pathlib import Path

# Supaya "from backend.auth_db import ..." bisa jalan walau script
# ini ada di dalam folder scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import auth_db  # noqa: E402


def ask_password_twice():
    p1 = getpass.getpass("Password baru : ")
    p2 = getpass.getpass("Ulangi        : ")
    if p1 != p2:
        print("[ERROR] Password tidak sama.")
        sys.exit(1)
    return p1


def main():
    parser = argparse.ArgumentParser(description="Kelola user dashboard ComVis")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Tampilkan semua user")

    p_add = sub.add_parser("add", help="Tambah user baru")
    p_add.add_argument("--username", required=True)
    p_add.add_argument("--role", default="user", choices=auth_db.VALID_ROLES)

    p_reset = sub.add_parser("reset-password", help="Ganti password user")
    p_reset.add_argument("--username", required=True)

    p_role = sub.add_parser("set-role", help="Ganti role user")
    p_role.add_argument("--username", required=True)
    p_role.add_argument("--role", required=True, choices=auth_db.VALID_ROLES)

    p_del = sub.add_parser("delete", help="Hapus user")
    p_del.add_argument("--username", required=True)

    args = parser.parse_args()

    auth_db.init_db()

    try:
        if args.command == "list":
            print(f"{'ID':<4} {'USERNAME':<16} {'ROLE':<13} DIBUAT")
            for u in auth_db.list_users():
                print(f"{u['id']:<4} {u['username']:<16} {u['role']:<13} {u['created_at']}")

        elif args.command == "add":
            password = ask_password_twice()
            auth_db.create_user(args.username, password, args.role)
            print(f"[OK] User '{args.username}' dibuat dengan role '{args.role}'.")

        elif args.command == "reset-password":
            password = ask_password_twice()
            auth_db.set_password(args.username, password)
            print(f"[OK] Password '{args.username}' diganti.")

        elif args.command == "set-role":
            auth_db.set_role(args.username, args.role)
            print(f"[OK] Role '{args.username}' sekarang '{args.role}'.")

        elif args.command == "delete":
            auth_db.delete_user(args.username)
            print(f"[OK] User '{args.username}' dihapus.")

    except ValueError as error:
        print(f"[ERROR] {error}")
        sys.exit(1)
    except Exception as error:  # username duplikat, dsb.
        print(f"[ERROR] {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()