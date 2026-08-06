"""
scripts/sort_dataset.py  (versi perbaikan)

PERBAIKAN dari versi lama:
- Nomor file baru diambil dari NOMOR TERTINGGI yang sudah ada,
  bukan dari JUMLAH file. Versi lama menimpa file kalau penomoran
  punya celah (mis. ada file yang pernah dihapus).
- Tidak pernah menimpa file yang sudah ada (dicek dulu).
- Setiap penyimpanan diverifikasi; kalau gagal, dilaporkan jelas.
- Di akhir ditampilkan ringkasan berapa yang benar-benar bertambah.

Tombol: h = Hadi | u = Unknown | s = Skip | q = Quit
"""

import os
import shutil

import cv2


SOURCE_DIR = "outputs/crops"
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"

VALID_EXT = (".jpg", ".jpeg", ".png")


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def get_image_files(folder):
    files = [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in VALID_EXT
    ]
    files.sort()
    return files


def count_images(folder):
    return len(get_image_files(folder))


def scan_highest_index(target_dir, prefix):
    """
    Cari NOMOR TERTINGGI yang sudah dipakai, mis. unknown_0253.jpg -> 253.
    Ini kunci perbaikannya: tidak lagi memakai jumlah file.
    """
    highest = 0

    for filename in os.listdir(target_dir):
        name, ext = os.path.splitext(filename)

        if ext.lower() not in VALID_EXT:
            continue
        if not name.startswith(prefix + "_"):
            continue

        try:
            number = int(name[len(prefix) + 1:])
        except ValueError:
            continue

        if number > highest:
            highest = number

    return highest


def next_free_path(target_dir, prefix, counter):
    """
    Nama berikutnya yang BELUM dipakai. Kalau ternyata sudah ada
    (misal sisa file lama), nomornya dilewati - tidak pernah menimpa.
    """
    while True:
        counter += 1
        candidate = os.path.join(target_dir, f"{prefix}_{counter:04d}.jpg")

        if not os.path.exists(candidate):
            return candidate, counter


def save_crop(source_path, target_dir, prefix, counter):
    """Salin 1 crop. Return (berhasil, counter_baru, target_path)."""
    target_path, counter = next_free_path(target_dir, prefix, counter)

    try:
        shutil.copy2(source_path, target_path)
    except Exception as error:
        print(f"[ERROR] Gagal menyalin ke {target_path}: {error}")
        return False, counter, target_path

    if not os.path.exists(target_path):
        print(f"[ERROR] File tidak terbentuk: {target_path}")
        return False, counter, target_path

    return True, counter, target_path


def main():
    ensure_dir(SOURCE_DIR)
    ensure_dir(HADI_DIR)
    ensure_dir(UNKNOWN_DIR)

    image_files = get_image_files(SOURCE_DIR)

    if len(image_files) == 0:
        print("[ERROR] Tidak ada gambar di outputs/crops.")
        print("[INFO] Jalankan dulu main.py sampai crop person tersimpan.")
        return

    counters = {
        "hadi": scan_highest_index(HADI_DIR, "hadi"),
        "unknown": scan_highest_index(UNKNOWN_DIR, "unknown"),
    }
    before = {"hadi": count_images(HADI_DIR), "unknown": count_images(UNKNOWN_DIR)}
    saved = {"hadi": 0, "unknown": 0, "skip": 0}

    print("[INFO] Mulai sorting dataset.")
    print(f"[INFO] Sumber: {SOURCE_DIR} ({len(image_files)} gambar)")
    print(f"[INFO] Sekarang -> hadi: {before['hadi']} file (nomor tertinggi {counters['hadi']}), "
          f"unknown: {before['unknown']} file (nomor tertinggi {counters['unknown']})")
    print("[INFO] Tombol: h = Hadi | u = Unknown | s = Skip | q = Quit")

    for filename in image_files:
        source_path = os.path.join(SOURCE_DIR, filename)
        image = cv2.imread(source_path)

        if image is None:
            print(f"[WARNING] Gagal membaca gambar: {source_path}")
            continue

        preview = image.copy()
        cv2.putText(
            preview,
            "h=Hadi | u=Unknown | s=Skip | q=Quit",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        cv2.imshow("Sort Dataset", preview)

        key = cv2.waitKey(0) & 0xFF

        if key == ord("h"):
            ok, counters["hadi"], target_path = save_crop(
                source_path, HADI_DIR, "hadi", counters["hadi"]
            )
            if ok:
                saved["hadi"] += 1
                print(f"[HADI] {filename} -> {target_path}")

        elif key == ord("u"):
            ok, counters["unknown"], target_path = save_crop(
                source_path, UNKNOWN_DIR, "unknown", counters["unknown"]
            )
            if ok:
                saved["unknown"] += 1
                print(f"[UNKNOWN] {filename} -> {target_path}")

        elif key == ord("s"):
            saved["skip"] += 1
            print(f"[SKIP] {filename}")

        elif key == ord("q"):
            print("[INFO] Sorting dihentikan.")
            break

        else:
            saved["skip"] += 1
            print(f"[SKIP] Tombol tidak dikenal untuk file: {filename}")

    cv2.destroyAllWindows()

    after = {"hadi": count_images(HADI_DIR), "unknown": count_images(UNKNOWN_DIR)}

    print("=" * 60)
    print("[DONE] Sorting dataset selesai.")
    print(f"  Hadi    : {before['hadi']} -> {after['hadi']}  (+{after['hadi'] - before['hadi']}, disimpan {saved['hadi']})")
    print(f"  Unknown : {before['unknown']} -> {after['unknown']}  (+{after['unknown'] - before['unknown']}, disimpan {saved['unknown']})")
    print(f"  Skip    : {saved['skip']}")
    print("=" * 60)

    if saved["hadi"] + saved["unknown"] > 0 and \
       (after["hadi"] - before["hadi"]) + (after["unknown"] - before["unknown"]) == 0:
        print("[PERINGATAN] Tidak ada file yang benar-benar bertambah. Cek izin folder / antivirus.")


if __name__ == "__main__":
    main()