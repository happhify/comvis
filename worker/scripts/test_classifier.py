import os
import cv2
import torch
from ultralytics import YOLO


MODEL_PATH = "models/body_best.pt"

TEST_DIRS = {
    "hadi": "datasets/classifier/val/hadi",
    "unknown": "datasets/classifier/val/unknown",
}


def get_device():
    if torch.cuda.is_available():
        return 0
    return "cpu"


def get_image_files(folder):
    valid_ext = (".jpg", ".jpeg", ".png", ".bmp")

    if not os.path.exists(folder):
        return []

    return [
        os.path.join(folder, filename)
        for filename in os.listdir(folder)
        if filename.lower().endswith(valid_ext)
    ]


def predict_image(model, image_path, device):
    results = model.predict(
        source=image_path,
        device=device,
        verbose=False,
    )

    result = results[0]

    probs = result.probs

    top1_index = int(probs.top1)
    top1_conf = float(probs.top1conf)

    class_name = result.names[top1_index]

    return class_name, top1_conf


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Model tidak ditemukan: {MODEL_PATH}")
        print("[INFO] Jalankan dulu training:")
        print("       python scripts/train_classifier.py")
        return

    device = get_device()

    print(f"[INFO] Loading classifier: {MODEL_PATH}")
    print(f"[INFO] Device: {device}")

    model = YOLO(MODEL_PATH)

    total = 0
    correct = 0

    for true_label, folder in TEST_DIRS.items():
        image_files = get_image_files(folder)

        print("=" * 60)
        print(f"[TEST] Folder: {folder}")
        print(f"[TEST] True label: {true_label}")
        print(f"[TEST] Total gambar: {len(image_files)}")

        for image_path in image_files:
            pred_label, confidence = predict_image(
                model=model,
                image_path=image_path,
                device=device,
            )

            filename = os.path.basename(image_path)

            is_correct = pred_label == true_label

            if is_correct:
                correct += 1

            total += 1

            status = "BENAR" if is_correct else "SALAH"

            print(
                f"{filename} | "
                f"pred={pred_label} | "
                f"conf={confidence:.4f} | "
                f"{status}"
            )

    print("=" * 60)

    if total > 0:
        accuracy = correct / total
        print(f"[RESULT] Correct : {correct}/{total}")
        print(f"[RESULT] Accuracy: {accuracy:.2%}")
    else:
        print("[ERROR] Tidak ada gambar untuk testing.")


if __name__ == "__main__":
    main()