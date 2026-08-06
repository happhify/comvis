"""
scripts/audit_dataset.py

Pemeriksaan MENYELURUH sebelum training. READ-ONLY:
tidak mengubah, memindah, atau menghapus apa pun.

Yang diperiksa:
1. outputs/crops        - semua kategori nama file (apa adanya, tidak menebak)
                          + file yang polanya tidak dikenal
2. datasets/known/hadi  - jumlah, celah penomoran, nama menyimpang,
   datasets/unknown       file duplikat (isi identik)
3. datasets/classifier  - jumlah train/val + cek KEBOCORAN
                          (file sama muncul di train DAN val)

Jalankan: python scripts/audit_dataset.py
"""

import hashlib
import os
import re
from collections import Counter, defaultdict

CROPS_DIR = "outputs/crops"
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"
CLASSIFIER_DIR = "datasets/classifier"

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")

# kamera_1_20260720_083503_frame_9960_person_0_unknown_unknown_conf_1.00.jpg
CROP_PATTERN = re.compile(
    r"^(?P<camera>.+?)_(?P<date>\d{8})_(?P<time>\d{6})"
    r"_frame_(?P<frame>\d+)_person_(?P<person>\d+)"
    r"_(?P<status>[a-z]+)_(?P<label>.+?)_conf_(?P<conf>[\d.]+)$"
)

problems = []


def line(char="-", n=70):
    print(char * n)


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


# ============================================================
# 1. outputs/crops
# ============================================================
def audit_crops():
    print()
    line("=")
    print("1. OUTPUTS/CROPS")
    line("=")

    files = list_images(CROPS_DIR)
    if not files:
        print(f"[INFO] Tidak ada gambar di {CROPS_DIR}.")
        return

    print(f"Total file gambar : {len(files)}")

    kategori = Counter()
    tak_dikenal = []
    tanggal = Counter()
    conf_verified = []

    for name in files:
        stem = os.path.splitext(name)[0]
        m = CROP_PATTERN.match(stem)

        if not m:
            tak_dikenal.append(name)
            continue

        status = m.group("status")
        label = m.group("label")
        kategori[(status, label)] += 1
        tanggal[m.group("date")] += 1

        if status == "verified":
            try:
                conf_verified.append(float(m.group("conf")))
            except ValueError:
                pass

    print()
    print("Kategori berdasarkan nama file (status + label):")
    total_dikenal = 0
    for (status, label), jumlah in kategori.most_common():
        pola = f"*_{status}_{label}_*"
        print(f"  {jumlah:>6}  {status:<11} {label:<16}  filter: {pola}")
        total_dikenal += jumlah

    print(f"\n  {total_dikenal:>6}  TOTAL cocok pola")
    print(f"  {len(tak_dikenal):>6}  TIDAK cocok pola")

    if tak_dikenal:
        problems.append(
            f"{len(tak_dikenal)} file di outputs/crops tidak mengikuti pola nama. "
            "File ini TIDAK akan tersaring oleh --filter."
        )
        print("\n  Contoh nama yang tidak cocok (maks 10):")
        for name in tak_dikenal[:10]:
            print(f"    - {name}")

    if tanggal:
        print(f"\nRentang tanggal crop: {min(tanggal)} s/d {max(tanggal)} "
              f"({len(tanggal)} hari berbeda)")
        for tgl, jumlah in sorted(tanggal.items()):
            print(f"    {tgl}: {jumlah}")

    if conf_verified:
        rata = sum(conf_verified) / len(conf_verified)
        print(f"\nConfidence crop 'verified': min {min(conf_verified):.2f} / "
              f"rata-rata {rata:.2f} / max {max(conf_verified):.2f}")


# ============================================================
# 2. Folder dataset
# ============================================================
def audit_dataset_folder(folder, prefix):
    print()
    line("=")
    print(f"2. {folder}")
    line("=")

    if not os.path.isdir(folder):
        print("[ERROR] Folder tidak ada.")
        problems.append(f"Folder {folder} tidak ditemukan.")
        return

    files = list_images(folder)
    print(f"Jumlah gambar : {len(files)}")

    nomor = []
    menyimpang = []

    for name in files:
        stem, _ = os.path.splitext(name)
        if not stem.startswith(prefix + "_"):
            menyimpang.append(name)
            continue
        try:
            nomor.append(int(stem[len(prefix) + 1:]))
        except ValueError:
            menyimpang.append(name)

    if nomor:
        nomor.sort()
        tertinggi = nomor[-1]
        print(f"Nomor terendah : {nomor[0]}")
        print(f"Nomor tertinggi: {tertinggi}")

        hilang = sorted(set(range(1, tertinggi + 1)) - set(nomor))
        if hilang:
            print(f"CELAH penomoran : {len(hilang)} nomor hilang "
                  f"(contoh: {hilang[:10]}{' ...' if len(hilang) > 10 else ''})")
            print("  -> Inilah yang membuat sort_dataset.py versi lama menimpa file.")
            problems.append(
                f"{folder}: ada {len(hilang)} celah penomoran "
                f"(jumlah file {len(nomor)}, nomor tertinggi {tertinggi})."
            )
        else:
            print("CELAH penomoran : tidak ada (rapat 1..N)")

    if menyimpang:
        print(f"Nama menyimpang : {len(menyimpang)} file")
        for name in menyimpang[:10]:
            print(f"    - {name}")
        problems.append(f"{folder}: {len(menyimpang)} file tidak mengikuti pola '{prefix}_XXXX'.")

    # duplikat isi
    hashes = defaultdict(list)
    for name in files:
        h = file_hash(os.path.join(folder, name))
        if h:
            hashes[h].append(name)

    duplikat = {h: names for h, names in hashes.items() if len(names) > 1}
    total_kelebihan = sum(len(v) - 1 for v in duplikat.values())

    if duplikat:
        print(f"DUPLIKAT isi    : {len(duplikat)} kelompok, {total_kelebihan} file berlebih")
        for names in list(duplikat.values())[:5]:
            print(f"    - {names[:4]}{' ...' if len(names) > 4 else ''}")
        problems.append(
            f"{folder}: {total_kelebihan} gambar duplikat (isi identik). "
            "Duplikat membuat model bias ke gambar itu."
        )
    else:
        print("DUPLIKAT isi    : tidak ada")

    return set(hashes.keys())


# ============================================================
# 3. Hasil split
# ============================================================
def audit_split():
    print()
    line("=")
    print(f"3. {CLASSIFIER_DIR} (hasil split)")
    line("=")

    if not os.path.isdir(CLASSIFIER_DIR):
        print("[INFO] Belum ada. Jalankan scripts/split_dataset.py kalau perlu.")
        return

    hash_per_split = {}

    for split in ("train", "val"):
        for kelas in ("hadi", "unknown"):
            folder = os.path.join(CLASSIFIER_DIR, split, kelas)
            files = list_images(folder)
            print(f"{split:<6} / {kelas:<8}: {len(files)} gambar")

            hs = set()
            for name in files:
                h = file_hash(os.path.join(folder, name))
                if h:
                    hs.add(h)
            hash_per_split[(split, kelas)] = hs

    print()
    for kelas in ("hadi", "unknown"):
        train_h = hash_per_split.get(("train", kelas), set())
        val_h = hash_per_split.get(("val", kelas), set())
        bocor = train_h & val_h

        if bocor:
            print(f"[BAHAYA] Kelas '{kelas}': {len(bocor)} gambar SAMA ada di train DAN val.")
            problems.append(
                f"Kebocoran data kelas '{kelas}': {len(bocor)} gambar identik "
                "ada di train dan val. Akurasi validasi jadi terlalu bagus (palsu)."
            )
        else:
            print(f"[OK] Kelas '{kelas}': tidak ada gambar yang bocor antara train dan val.")


def main():
    print()
    line("=")
    print("AUDIT DATASET - read only, tidak mengubah apa pun")
    line("=")

    audit_crops()
    audit_dataset_folder(HADI_DIR, "hadi")
    audit_dataset_folder(UNKNOWN_DIR, "unknown")
    audit_split()

    print()
    line("=")
    print("RINGKASAN")
    line("=")

    if not problems:
        print("Tidak ditemukan masalah. Dataset siap.")
    else:
        print(f"Ditemukan {len(problems)} hal yang perlu diperhatikan:\n")
        for i, p in enumerate(problems, 1):
            print(f"  {i}. {p}")

    print()
    print("Catatan: script ini tidak memeriksa gambar rusak/terbaca atau tidak.")
    print("Untuk itu jalankan: python scripts/check_dataset.py")
    line("=")


if __name__ == "__main__":
    main()
    