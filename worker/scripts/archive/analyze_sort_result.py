"""
scripts/analyze_sort_result.py

Menelusuri KE MANA setiap crop berakhir setelah disortir.

Caranya: file di dataset adalah salinan persis crop aslinya, jadi
dicocokkan lewat hash isi file (bukan nama). Dari situ kita tahu,
untuk tiap kategori crop, berapa yang kamu masukkan ke 'hadi',
berapa ke 'unknown', dan berapa yang dilewati.

Dua angka terpenting:
- verified_hadi   -> unknown : FALSE POSITIVE terkonfirmasi manual
                               (sistem yakin Hadi, ternyata bukan)
- unverified_hadi -> hadi    : sistem TERLALU konservatif
                               (benar Hadi tapi tidak berani bilang)

READ-ONLY: tidak mengubah apa pun.
"""

import argparse
import hashlib
import os
import re
import shutil
from collections import defaultdict

CROPS_DIR = "outputs/crops"
HADI_DIR = "datasets/known/hadi"
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
    return sorted(
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in VALID_EXT
    )


def file_hash(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return None
    return h.hexdigest()


def hash_folder(folder):
    """hash -> nama file di folder itu."""
    result = {}
    for name in list_images(folder):
        h = file_hash(os.path.join(folder, name))
        if h and h not in result:
            result[h] = name
    return result


def main():
    parser = argparse.ArgumentParser(description="Telusuri ke mana tiap crop berakhir.")
    parser.add_argument("--export", metavar="FOLDER", default=None,
                        help="Salin file 'verified_hadi -> unknown' ke folder ini untuk diperiksa")
    args = parser.parse_args()

    print()
    print("=" * 74)
    print("ANALISIS HASIL SORTIR - ke mana setiap crop berakhir")
    print("=" * 74)

    crops = list_images(CROPS_DIR)
    if not crops:
        print(f"[ERROR] Tidak ada gambar di {CROPS_DIR}")
        return

    print(f"Membaca {len(crops)} crop ...")
    hadi_map = hash_folder(HADI_DIR)
    unknown_map = hash_folder(UNKNOWN_DIR)
    print(f"Dataset: {len(hadi_map)} hadi, {len(unknown_map)} unknown")

    # kategori -> counter
    stat = defaultdict(lambda: {"hadi": 0, "unknown": 0, "lewat": 0, "total": 0})
    fp_files = []      # verified_hadi yang masuk unknown
    recall_files = []  # unverified_hadi yang masuk hadi

    for name in crops:
        stem = os.path.splitext(name)[0]
        m = CROP_PATTERN.match(stem)
        kategori = f"{m.group('status')}_{m.group('label')}" if m else "(tanpa pola)"

        h = file_hash(os.path.join(CROPS_DIR, name))
        s = stat[kategori]
        s["total"] += 1

        if h in hadi_map:
            s["hadi"] += 1
            if kategori == "unverified_hadi":
                recall_files.append((name, hadi_map[h]))
        elif h in unknown_map:
            s["unknown"] += 1
            if kategori == "verified_hadi":
                fp_files.append((name, unknown_map[h]))
        else:
            s["lewat"] += 1

    print()
    print("-" * 74)
    print(f"{'KATEGORI CROP':<26}{'TOTAL':>7}{'-> hadi':>10}{'-> unknown':>12}{'dilewati':>11}")
    print("-" * 74)
    for kategori in sorted(stat, key=lambda k: -stat[k]["total"]):
        s = stat[kategori]
        print(f"{kategori:<26}{s['total']:>7}{s['hadi']:>10}{s['unknown']:>12}{s['lewat']:>11}")
    print("-" * 74)

    # ---------- Angka kunci ----------
    v = stat.get("verified_hadi")
    u = stat.get("unverified_hadi")

    print()
    print("=" * 74)
    print("ANGKA KUNCI")
    print("=" * 74)

    if v and v["total"] > 0:
        dinilai = v["hadi"] + v["unknown"]
        print(f"\n1. FALSE POSITIVE terkonfirmasi manual")
        print(f"   Dari {v['total']} crop yang sistem sebut 'Verified Hadi':")
        print(f"     - benar Hadi        : {v['hadi']}")
        print(f"     - BUKAN Hadi        : {v['unknown']}   <-- false positive")
        print(f"     - dilewati/skip     : {v['lewat']}")
        if dinilai > 0:
            print(f"   Tingkat kesalahan   : {v['unknown']}/{dinilai} = "
                  f"{v['unknown'] / dinilai * 100:.1f}% dari yang kamu nilai")

    if u and u["total"] > 0:
        dinilai = u["hadi"] + u["unknown"]
        print(f"\n2. SEBERAPA KONSERVATIF sistemnya")
        print(f"   Dari {u['total']} crop 'Unverified' yang dicurigai Hadi:")
        print(f"     - ternyata memang Hadi : {u['hadi']}   <-- terlewat, padahal benar")
        print(f"     - memang bukan Hadi    : {u['unknown']}")
        print(f"     - dilewati/skip        : {u['lewat']}")
        if dinilai > 0:
            print(f"   Sistem terlalu hati-hati pada "
                  f"{u['hadi']}/{dinilai} = {u['hadi'] / dinilai * 100:.1f}% kasus")

    if fp_files:
        print()
        print("-" * 74)
        print(f"File dataset yang berasal dari crop 'verified_hadi' tapi kamu taruh")
        print(f"di UNKNOWN ({len(fp_files)} file). Periksa ulang kalau ragu:")
        for asal, tujuan in fp_files[:15]:
            print(f"  datasets/unknown/{tujuan}")
        if len(fp_files) > 15:
            print(f"  ... dan {len(fp_files) - 15} lainnya")

        if args.export:
            os.makedirs(args.export, exist_ok=True)
            disalin = 0
            for asal, tujuan in fp_files:
                src = os.path.join(UNKNOWN_DIR, tujuan)
                dst = os.path.join(args.export, f"cek_{disalin + 1:03d}__{tujuan}")
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    disalin += 1
            print()
            print(f"[EXPORT] {disalin} file disalin ke: {args.export}")
            print("         Buka folder itu, lihat satu per satu.")
            print("         Hitung berapa yang TERNYATA Hadi (berarti salah taruh).")

    print()
    print("=" * 74)


if __name__ == "__main__":
    main()