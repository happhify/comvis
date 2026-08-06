"""
scripts/clean_dataset.py

Membereskan dua akar masalah di folder dataset:
1. DUPLIKAT  - gambar dengan isi identik (penyebab kebocoran train/val)
2. PENOMORAN - nama campur aduk (hadi10.jpg, frame_000080_...jpg,
               hadi_0115.jpg) yang membuat sort_dataset.py versi lama
               menimpa file

Yang dilakukan:
- Duplikat DIPINDAH (bukan dihapus) ke datasets/_duplicates/<kelas>/
- Sisanya dinomori ulang rapi: hadi_0001.jpg, hadi_0002.jpg, ...

AMAN: secara default hanya SIMULASI (dry run). Tidak ada yang berubah
sampai kamu menambahkan --apply.

    python scripts/clean_dataset.py            # lihat rencananya dulu
    python scripts/clean_dataset.py --apply    # baru dijalankan
"""

import argparse
import hashlib
import os
import shutil

CLASSES = {
    "hadi": "datasets/known/hadi",
    "unknown": "datasets/unknown",
}
QUARANTINE_ROOT = "datasets/_duplicates"
VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in VALID_EXT
    )


def file_hash(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_class(label, folder, apply_changes):
    print()
    print("=" * 70)
    print(f"KELAS: {label}   ({folder})")
    print("=" * 70)

    if not os.path.isdir(folder):
        print("[ERROR] Folder tidak ada, dilewati.")
        return

    files = list_images(folder)
    print(f"Jumlah awal : {len(files)} gambar")

    # ---------- 1. Cari duplikat ----------
    seen = {}
    keep = []
    duplicates = []

    for name in files:
        path = os.path.join(folder, name)
        try:
            h = file_hash(path)
        except Exception as e:
            print(f"[WARNING] Gagal membaca {name}: {e}")
            continue

        if h in seen:
            duplicates.append((name, seen[h]))
        else:
            seen[h] = name
            keep.append(name)

    print(f"Duplikat    : {len(duplicates)} file (isi sama dengan file lain)")
    print(f"Dipertahankan: {len(keep)} gambar unik")

    quarantine = os.path.join(QUARANTINE_ROOT, label)

    if duplicates:
        print(f"\n  Duplikat akan DIPINDAH ke: {quarantine}")
        for name, asli in duplicates[:5]:
            print(f"    {name}  (sama dengan {asli})")
        if len(duplicates) > 5:
            print(f"    ... dan {len(duplicates) - 5} lainnya")

    # ---------- 2. Rencana penomoran ulang ----------
    perlu_rename = sum(
        1 for i, name in enumerate(keep, start=1)
        if name != f"{label}_{i:04d}.jpg"
    )
    print(f"\nPenomoran ulang: {perlu_rename} dari {len(keep)} file akan berganti nama")
    print(f"  Hasil akhir : {label}_0001.jpg ... {label}_{len(keep):04d}.jpg")

    if not apply_changes:
        print("\n[DRY RUN] Belum ada yang diubah. Tambahkan --apply untuk menjalankan.")
        return

    # ---------- 3. Eksekusi ----------
    os.makedirs(quarantine, exist_ok=True)

    dipindah = 0
    for name, _ in duplicates:
        src = os.path.join(folder, name)
        dst = os.path.join(quarantine, name)
        n = 1
        while os.path.exists(dst):          # jangan menimpa di karantina
            stem, ext = os.path.splitext(name)
            dst = os.path.join(quarantine, f"{stem}__{n}{ext}")
            n += 1
        shutil.move(src, dst)
        dipindah += 1

    # Rename 2 tahap supaya tidak bentrok nama
    sementara = []
    for i, name in enumerate(keep, start=1):
        src = os.path.join(folder, name)
        tmp = os.path.join(folder, f"__tmp_{i:06d}.jpg")
        os.rename(src, tmp)
        sementara.append(tmp)

    for i, tmp in enumerate(sementara, start=1):
        final = os.path.join(folder, f"{label}_{i:04d}.jpg")
        os.rename(tmp, final)

    akhir = list_images(folder)
    print(f"\n[SELESAI] {dipindah} duplikat dipindah, {len(akhir)} gambar dinomori ulang.")
    print(f"[SELESAI] Sekarang: {label}_0001.jpg ... {label}_{len(akhir):04d}.jpg")


def main():
    parser = argparse.ArgumentParser(
        description="Bersihkan duplikat & rapikan penomoran dataset."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Benar-benar jalankan. Tanpa ini hanya simulasi.")
    args = parser.parse_args()

    print()
    print("=" * 70)
    print("BERSIHKAN DATASET" + ("  [MENJALANKAN]" if args.apply else "  [SIMULASI / DRY RUN]"))
    print("=" * 70)

    for label, folder in CLASSES.items():
        clean_class(label, folder, args.apply)

    print()
    print("=" * 70)
    if args.apply:
        print("Langkah berikutnya:")
        print("  1. python scripts/audit_dataset.py     # pastikan duplikat & celah hilang")
        print("  2. python scripts/split_dataset.py     # split ulang (kebocoran hilang)")
        print("  3. python scripts/audit_dataset.py     # pastikan train/val bersih")
        print()
        print("Duplikat TIDAK dihapus, hanya dipindah ke datasets/_duplicates/")
        print("Kalau semua aman, folder itu boleh kamu hapus manual.")
    else:
        print("Ini baru simulasi. Jalankan lagi dengan --apply kalau rencananya sudah cocok.")
    print("=" * 70)


if __name__ == "__main__":
    main()