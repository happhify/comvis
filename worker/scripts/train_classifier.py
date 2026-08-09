import os
import shutil
from pathlib import Path

import torch
from ultralytics import YOLO


DATASET_DIR = "datasets/classifier"

# Kalau kamu memang pakai yolov8m-cls.pt, biarkan ini.
# Kalau mau lebih ringan, ganti ke "yolov8n-cls.pt".
BASE_MODEL = "yolov8m-cls.pt"

PROJECT_DIR = "runs/classifier"
RUN_NAME = "hadi_unknown"

OUTPUT_MODEL_PATH = "models/body_best.pt"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def count_images(folder):
    valid_ext = (".jpg", ".jpeg", ".png", ".bmp")

    if not os.path.exists(folder):
        return 0

    return len([
        filename for filename in os.listdir(folder)
        if filename.lower().endswith(valid_ext)
    ])


def check_dataset():
    required_dirs = [
        os.path.join(DATASET_DIR, "train", "hadi"),
        os.path.join(DATASET_DIR, "train", "unknown"),
        os.path.join(DATASET_DIR, "val", "hadi"),
        os.path.join(DATASET_DIR, "val", "unknown"),
    ]

    dataset_ok = True

    for folder in required_dirs:
        image_count = count_images(folder)

        print(f"[INFO] {folder}: {image_count} gambar")

        if image_count == 0:
            print(f"[ERROR] Folder kosong atau tidak ditemukan: {folder}")
            dataset_ok = False

    return dataset_ok


def get_device():
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        print(f"[INFO] GPU terdeteksi: {gpu_name}")
        return 0

    print("[WARNING] GPU tidak terdeteksi. Training pakai CPU.")
    return "cpu"


def find_latest_best_model(run_name):
    possible_paths = list(Path("runs").rglob(f"{run_name}/weights/best.pt"))

    if len(possible_paths) == 0:
        return None

    possible_paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    return str(possible_paths[0])


def main():
    print("[INFO] Mulai training classifier Hadi vs Unknown...")

    dataset_ok = check_dataset()

    if not dataset_ok:
        print("[ERROR] Dataset belum siap.")
        print("[INFO] Jalankan dulu:")
        print("       python scripts/split_dataset.py")
        return

    device = get_device()

    print(f"[INFO] Loading base model: {BASE_MODEL}")
    model = YOLO(BASE_MODEL)

    model.train(
        data=DATASET_DIR,
        epochs=50,
        imgsz=224,
        batch=32,
        patience=10,
        device=device,
        project=PROJECT_DIR,
        name=RUN_NAME,
        exist_ok=True,
    )

    best_model_path = find_latest_best_model(RUN_NAME)

    if best_model_path is None:
        print("[ERROR] best.pt tidak ditemukan setelah training.")
        print("[INFO] Cek manual di folder runs/")
        return

    ensure_dir("models")

    shutil.copy2(best_model_path, OUTPUT_MODEL_PATH)

    print("=" * 60)
    print("[DONE] Training selesai.")
    print(f"[INFO] best.pt ditemukan di : {best_model_path}")
    print(f"[INFO] Model disalin ke    : {OUTPUT_MODEL_PATH}")
    print("[NEXT] Jalankan:")
    print("       python scripts/test_classifier.py")


if __name__ == "__main__":
    main()