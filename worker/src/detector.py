import os
from ultralytics import YOLO


class PersonDetector:
    def __init__(
        self,
        model_path="models/yolov8m.pt",
        confidence_threshold=0.35,
        device="cpu",
    ):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device = device

        if os.path.exists(self.model_path):
            print(f"[INFO] Loading YOLO model dari: {self.model_path}")
            self.model = YOLO(self.model_path)
        else:
            print(f"[WARNING] Model tidak ditemukan di: {self.model_path}")
            print("[INFO] Mencoba memakai yolov8n.pt default.")
            print("[INFO] Jika belum ada, Ultralytics akan mencoba download otomatis.")
            self.model = YOLO("yolov8n.pt")

        print("[INFO] YOLO PersonDetector siap digunakan.")

    def detect_person(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            classes=[0],
            device=self.device,
            verbose=False,
        )

        detections = []

        if len(results) == 0:
            return detections

        result = results[0]

        if result.boxes is None:
            return detections

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())

            detection = {
                "class_id": class_id,
                "label": "person",
                "confidence": confidence,
                "bbox": [x1, y1, x2, y2],
            }

            detections.append(detection)

        return detections