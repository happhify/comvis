import os
import random
import shutil


RAW_DATASET = {
    "hadi": "datasets/known/hadi",
    "unknown": "datasets/unknown",
}

OUTPUT_DIR = "datasets/classifier"

TRAIN_RATIO = 0.8

VALID_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def is_image_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in VALID_EXTENSIONS


def clear_output_dir():
    if os.path.exists(OUTPUT_DIR):
        print(f"[INFO] Menghapus folder lama: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)

    ensure_dir(OUTPUT_DIR)


def copy_files(files, source_dir, target_dir):
    ensure_dir(target_dir)

    for filename in files:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)

        shutil.copy2(source_path, target_path)


def split_class(label, source_dir):
    print("=" * 60)
    print(f"[INFO] Memproses class: {label}")
    print(f"[INFO] Source: {source_dir}")

    if not os.path.exists(source_dir):
        print(f"[ERROR] Folder tidak ditemukan: {source_dir}")
        return

    files = [
        filename
        for filename in os.listdir(source_dir)
        if is_image_file(filename)
    ]

    if len(files) == 0:
        print(f"[ERROR] Tidak ada gambar di folder: {source_dir}")
        return

    random.shuffle(files)

    train_count = int(len(files) * TRAIN_RATIO)

    train_files = files[:train_count]
    val_files = files[train_count:]

    train_target_dir = os.path.join(OUTPUT_DIR, "train", label)
    val_target_dir = os.path.join(OUTPUT_DIR, "val", label)

    copy_files(train_files, source_dir, train_target_dir)
    copy_files(val_files, source_dir, val_target_dir)

    print(f"[INFO] Total gambar : {len(files)}")
    print(f"[INFO] Train        : {len(train_files)}")
    print(f"[INFO] Val          : {len(val_files)}")


def main():
    random.seed(42)

    clear_output_dir()

    for label, source_dir in RAW_DATASET.items():
        split_class(label, source_dir)

    print("=" * 60)
    print("[DONE] Split dataset selesai.")
    print(f"[INFO] Dataset classifier tersimpan di: {OUTPUT_DIR}")
    print("[NEXT] Jalankan training dengan scripts/train_classifier.py")


if __name__ == "__main__":
    main()