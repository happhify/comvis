"""
scripts/balance_dataset.py

Menyeimbangkan kelas sebelum retrain, TANPA membuang gambar berharga.

Masalahnya: unknown jauh lebih banyak daripada hadi. Kalau dilatih apa
adanya, model belajar "kalau ragu bilang unknown saja" - precision naik
bukan karena hard negative bekerja, tapi karena kelasnya timpang.

Tapi menyampel acak juga salah: justru gambar TERPENTING (orang yang
pernah salah dikenali sebagai Hadi) bisa ikut terbuang.

Maka pembagiannya:
- HARD negative = gambar unknown yang asalnya crop '*_verified_hadi_*'
                  atau '*_unverified_hadi_*'  -> model pernah condong
                  ke Hadi di sini. SEMUA dipertahankan.
- EASY negative = sisanya (orang yang jelas bukan Hadi). Dikurangi
                  sampai rasio target tercapai.

Yang dibuang hanya DIPINDAH ke datasets/_unused_unknown/ (tidak dihapus).

    python scripts/balance_dataset.py                 # simulasi
    python scripts/balance_dataset.py --apply         # jalankan
    python scripts/balance_dataset.py --ratio 2.5     # ubah rasio target
"""

import argparse
import hashlib
import os
import random
import re
import shutil

CROPS_DIR = "outputs/crops"
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"
UNUSED_DIR = "datasets/_unused_unknown"

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")

# crop yang menandakan model CONDONG ke Hadi
HARD_PATTERNS = ("_verified_hadi_", "_unverified_hadi_")


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


def hard_negative_hashes():
    """Hash crop yang pernah dianggap/dicurigai Hadi oleh model."""
    hashes = set()
    for name in list_images(CROPS_DIR):
        if any(p in name for p in HARD_PATTERNS):
            h = file_hash(os.path.join(CROPS_DIR, name))
            if h:
                hashes.add(h)
    return hashes


def main():
    parser = argparse.ArgumentParser(description="Seimbangkan kelas sebelum retrain.")
    parser.add_argument("--apply", action="store_true", help="Benar-benar jalankan")
    parser.add_argument("--ratio", type=float, default=2.0,
                        help="Target unknown : hadi. Default 2.0")
    parser.add_argument("--seed", type=int, default=42, help="Seed acak (agar bisa diulang)")
    args = parser.parse_args()

    random.seed(args.seed)

    print()
    print("=" * 72)
    print("SEIMBANGKAN DATASET" + ("  [MENJALANKAN]" if args.apply else "  [SIMULASI]"))
    print("=" * 72)

    hadi_files = list_images(HADI_DIR)
    unknown_files = list_images(UNKNOWN_DIR)
    n_hadi = len(hadi_files)

    if n_hadi == 0:
        print("[ERROR] Folder hadi kosong.")
        return

    print(f"Sekarang : hadi {n_hadi}, unknown {len(unknown_files)} "
          f"(rasio 1:{len(unknown_files) / n_hadi:.1f})")

    target_unknown = int(round(n_hadi * args.ratio))
    print(f"Target   : unknown {target_unknown} (rasio 1:{args.ratio})")

    print("\nMemindai crop untuk menandai hard negative ...")
    hard_hashes = hard_negative_hashes()
    print(f"  Crop yang pernah dicondongkan ke Hadi: {len(hard_hashes)} (isi unik)")

    hard, easy = [], []
    for name in unknown_files:
        h = file_hash(os.path.join(UNKNOWN_DIR, name))
        (hard if h in hard_hashes else easy).append(name)

    print(f"\nIsi kelas unknown:")
    print(f"  HARD negative (wajib disimpan) : {len(hard)}")
    print(f"  EASY negative (bisa dikurangi) : {len(easy)}")

    if len(hard) >= target_unknown:
        print(f"\n[CATATAN] Hard negative saja ({len(hard)}) sudah >= target "
              f"({target_unknown}).")
        print("          Semua hard dipertahankan, semua easy dipindahkan.")
        keep_easy = []
    else:
        kuota = target_unknown - len(hard)
        keep_easy = random.sample(easy, min(kuota, len(easy)))
        print(f"\n  Dari {len(easy)} easy negative, diambil {len(keep_easy)} "
              f"untuk memenuhi kuota.")

    keep = set(hard) | set(keep_easy)
    buang = [n for n in unknown_files if n not in keep]

    print()
    print("-" * 72)
    print(f"HASIL AKHIR : hadi {n_hadi}, unknown {len(keep)} "
          f"(rasio 1:{len(keep) / n_hadi:.1f})")
    print(f"Dipindahkan : {len(buang)} gambar easy negative -> {UNUSED_DIR}")
    print("-" * 72)

    if not args.apply:
        print("\n[SIMULASI] Belum ada yang berubah. Tambahkan --apply untuk menjalankan.")
        return

    os.makedirs(UNUSED_DIR, exist_ok=True)
    dipindah = 0
    for name in buang:
        src = os.path.join(UNKNOWN_DIR, name)
        dst = os.path.join(UNUSED_DIR, name)
        n = 1
        while os.path.exists(dst):
            stem, ext = os.path.splitext(name)
            dst = os.path.join(UNUSED_DIR, f"{stem}__{n}{ext}")
            n += 1
        shutil.move(src, dst)
        dipindah += 1

    sisa = len(list_images(UNKNOWN_DIR))
    print(f"\n[SELESAI] {dipindah} gambar dipindahkan.")
    print(f"[SELESAI] Sekarang: hadi {n_hadi}, unknown {sisa}")
    print()
    print("Langkah berikutnya:")
    print("  1. python scripts/clean_dataset.py --apply   # nomori ulang")
    print("  2. python scripts/split_dataset.py           # split baru")
    print("  3. python scripts/audit_dataset.py           # pastikan bersih")
    print()
    print(f"Gambar yang dipindah TIDAK dihapus - ada di {UNUSED_DIR}")


if __name__ == "__main__":
    main()