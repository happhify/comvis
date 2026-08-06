import os
import cv2


DATASET_DIRS = {
    "hadi": "datasets/known/hadi",
    "unknown": "datasets/unknown",
}


VALID_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp"]


def is_image_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in VALID_EXTENSIONS


def check_folder(label, folder_path):
    print("=" * 60)
    print(f"[CHECK] Label: {label}")
    print(f"[CHECK] Folder: {folder_path}")

    if not os.path.exists(folder_path):
        print(f"[ERROR] Folder tidak ditemukan: {folder_path}")
        return {
            "label": label,
            "total_files": 0,
            "valid_images": 0,
            "broken_images": 0,
        }

    files = os.listdir(folder_path)
    image_files = [f for f in files if is_image_file(f)]

    total_files = len(image_files)
    valid_images = 0
    broken_images = 0

    if total_files == 0:
        print("[WARNING] Tidak ada file gambar di folder ini.")
        return {
            "label": label,
            "total_files": 0,
            "valid_images": 0,
            "broken_images": 0,
        }

    for filename in image_files:
        image_path = os.path.join(folder_path, filename)
        image = cv2.imread(image_path)

        if image is None:
            broken_images += 1
            print(f"[BROKEN] Gagal dibaca: {image_path}")
        else:
            valid_images += 1

    print(f"[INFO] Total file gambar : {total_files}")
    print(f"[INFO] Gambar valid      : {valid_images}")
    print(f"[INFO] Gambar rusak      : {broken_images}")

    if valid_images < 50:
        print("[WARNING] Jumlah gambar masih sedikit. Minimal awal disarankan 50 gambar.")
    else:
        print("[OK] Jumlah gambar cukup untuk prototype awal.")

    return {
        "label": label,
        "total_files": total_files,
        "valid_images": valid_images,
        "broken_images": broken_images,
    }


def main():
    print("[INFO] Mulai cek dataset...")

    results = []

    for label, folder_path in DATASET_DIRS.items():
        result = check_folder(label, folder_path)
        results.append(result)

    print("=" * 60)
    print("[SUMMARY] Ringkasan Dataset")

    for result in results:
        print(
            f"{result['label']}: "
            f"{result['valid_images']} valid, "
            f"{result['broken_images']} rusak"
        )

    hadi_count = results[0]["valid_images"]
    unknown_count = results[1]["valid_images"]

    print("=" * 60)

    if hadi_count > 0 and unknown_count > 0:
        print("[OK] Dataset punya minimal 2 kelas: hadi dan unknown.")
        print("[NEXT] Dataset siap masuk tahap split train/val.")
    else:
        print("[ERROR] Dataset belum siap.")
        print("[INFO] Pastikan folder hadi dan unknown sama-sama punya gambar valid.")


if __name__ == "__main__":
    main()