"""
scripts/harvest_false_positives.py

Memanen hard negative GRATIS dari jendela waktu ketika target
DIPASTIKAN TIDAK ADA di frame (mis. long run test).

Logikanya: kalau target tidak ada, setiap crop bernama
'*_verified_<target>_*' pada jendela itu PASTI salah. Jadi bisa langsung
dimasukkan ke kelas unknown tanpa dinilai manual satu per satu.

Crop yang isinya sudah ada di datasets/unknown dilewati (tidak dobel).
Gunakan --every untuk menghindari frame berurutan yang nyaris kembar.

    python scripts/harvest_false_positives.py --start "..." --end "..."
    python scripts/harvest_false_positives.py --start "..." --end "..." --every 3 --apply
"""

import argparse
import hashlib
import os
import re
import shutil
from datetime import datetime

CROPS_DIR = "outputs/crops"
UNKNOWN_DIR = "datasets/unknown"
VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")

CROP_PATTERN = re.compile(
    r"^(?P<camera>.+?)_(?P<date>\d{8})_(?P<time>\d{6})"
    r"_frame_(?P<frame>\d+)_person_(?P<person>\d+)"
    r"_(?P<status>[a-z]+)_(?P<label>.+?)_conf_(?P<conf>[\d.]+)$"
)


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if os.path.splitext(f)[1].lower() in VALID_EXT)


def file_hash(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return None
    return h.hexdigest()


def parse_dt(text):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(str(text).strip(), fmt)
        except ValueError:
            continue
    return None


def scan_highest_index(folder, prefix):
    highest = 0
    for name in list_images(folder):
        stem, _ = os.path.splitext(name)
        if not stem.startswith(prefix + "_"):
            continue
        try:
            n = int(stem[len(prefix) + 1:])
        except ValueError:
            continue
        highest = max(highest, n)
    return highest


def main():
    parser = argparse.ArgumentParser(description="Panen hard negative dari jendela tanpa target.")
    parser.add_argument("--start", required=True, help='"YYYY-MM-DD HH:MM:SS"')
    parser.add_argument("--end", required=True, help='"YYYY-MM-DD HH:MM:SS"')
    parser.add_argument("--target-label", default="hadi")
    parser.add_argument("--every", type=int, default=1,
                        help="Ambil tiap N crop (hindari frame nyaris kembar). Default 1")
    parser.add_argument("--apply", action="store_true", help="Benar-benar salin")
    args = parser.parse_args()

    start_dt, end_dt = parse_dt(args.start), parse_dt(args.end)
    target = args.target_label.lower().strip()

    print()
    print("=" * 72)
    print("PANEN HARD NEGATIVE" + ("  [MENJALANKAN]" if args.apply else "  [SIMULASI]"))
    print("=" * 72)
    print(f"Jendela : {args.start}  ->  {args.end}")
    print(f"Target  : {target}  (semua '{target} verified' di jendela ini = SALAH)")

    if start_dt is None or end_dt is None or end_dt <= start_dt:
        print("[ERROR] Format waktu salah atau --end tidak lebih lambat dari --start.")
        return

    # crop verified_<target> di dalam jendela
    kandidat = []
    for name in list_images(CROPS_DIR):
        stem = os.path.splitext(name)[0]
        m = CROP_PATTERN.match(stem)
        if not m:
            continue
        if m.group("status") != "verified" or m.group("label") != target:
            continue

        d, t = m.group("date"), m.group("time")
        ts = parse_dt(f"{d[0:4]}-{d[4:6]}-{d[6:8]} {t[0:2]}:{t[2:4]}:{t[4:6]}")
        if ts is None or ts < start_dt or ts > end_dt:
            continue
        kandidat.append(name)

    print(f"\nCrop 'verified {target}' di jendela : {len(kandidat)}")

    if not kandidat:
        print("[INFO] Tidak ada. Pastikan save_crops aktif saat run itu.")
        return

    if args.every > 1:
        kandidat = kandidat[::args.every]
        print(f"Setelah sampling tiap {args.every}      : {len(kandidat)}")

    # buang yang isinya sudah ada di dataset
    sudah = {file_hash(os.path.join(UNKNOWN_DIR, n)) for n in list_images(UNKNOWN_DIR)}
    baru = []
    for name in kandidat:
        h = file_hash(os.path.join(CROPS_DIR, name))
        if h and h not in sudah:
            baru.append(name)
            sudah.add(h)

    print(f"Sudah ada di dataset (dilewati)    : {len(kandidat) - len(baru)}")
    print(f"BENAR-BENAR BARU                   : {len(baru)}")

    sebelum = len(list_images(UNKNOWN_DIR))
    print(f"\nunknown sekarang {sebelum} -> akan jadi {sebelum + len(baru)}")

    if not args.apply:
        print("\n[SIMULASI] Belum ada yang disalin. Tambahkan --apply untuk menjalankan.")
        return

    counter = scan_highest_index(UNKNOWN_DIR, "unknown")
    disalin = 0
    for name in baru:
        while True:
            counter += 1
            dst = os.path.join(UNKNOWN_DIR, f"unknown_{counter:04d}.jpg")
            if not os.path.exists(dst):
                break
        shutil.copy2(os.path.join(CROPS_DIR, name), dst)
        disalin += 1

    print(f"\n[SELESAI] {disalin} hard negative ditambahkan ke {UNKNOWN_DIR}")
    print(f"[SELESAI] unknown sekarang: {len(list_images(UNKNOWN_DIR))}")
    print()
    print("Langkah berikutnya: python scripts/balance_dataset.py")


if __name__ == "__main__":
    main()