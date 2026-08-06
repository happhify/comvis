import os
import numpy as np
from ultralytics import YOLO


class EmployeeClassifier:
    def __init__(
        self,
        model_path="models/body_best.pt",
        device="cpu",
        verified_threshold=0.97,
        unknown_threshold=0.70,
        min_margin=0.40,
    ):
        self.model_path = model_path
        self.device = device
        self.verified_threshold = verified_threshold
        self.unknown_threshold = unknown_threshold
        self.min_margin = min_margin

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Model classifier tidak ditemukan: {self.model_path}"
            )

        print(f"[INFO] Loading employee classifier dari: {self.model_path}")
        self.model = YOLO(self.model_path)

        print("[INFO] EmployeeClassifier siap digunakan.")
        print(f"[INFO] Recognition device     : {self.device}")
        print(f"[INFO] Verified threshold    : {self.verified_threshold}")
        print(f"[INFO] Unknown threshold     : {self.unknown_threshold}")
        print(f"[INFO] Minimum margin        : {self.min_margin}")

    def predict(self, crop_image):
        if crop_image is None or crop_image.size == 0:
            return self._unknown_result("empty_crop")

        try:
            results = self.model.predict(
                source=crop_image,
                device=self.device,
                verbose=False,
            )

            if len(results) == 0:
                return self._unknown_result("no_result")

            result = results[0]

            if result.probs is None:
                return self._unknown_result("no_probs")

            probs_array = result.probs.data.cpu().numpy()

            sorted_indices = np.argsort(probs_array)[::-1]

            top1_index = int(sorted_indices[0])
            top1_conf = float(probs_array[top1_index])
            top1_label = str(result.names[top1_index]).lower().strip()

            if len(sorted_indices) > 1:
                top2_index = int(sorted_indices[1])
                top2_conf = float(probs_array[top2_index])
                top2_label = str(result.names[top2_index]).lower().strip()
            else:
                top2_conf = 0.0
                top2_label = "none"

            margin = top1_conf - top2_conf

            status = self._convert_to_status(
                pred_label=top1_label,
                confidence=top1_conf,
                margin=margin,
            )

            return {
                "raw_label": top1_label,
                "confidence": top1_conf,
                "top2_label": top2_label,
                "top2_confidence": top2_conf,
                "margin": margin,
                "status": status,
                "display_label": self._get_display_label(
                    status=status,
                    confidence=top1_conf,
                    margin=margin,
                ),
            }

        except Exception as error:
            print(f"[WARNING] Classifier gagal prediksi: {error}")
            return self._unknown_result("prediction_error")

    def _convert_to_status(self, pred_label, confidence, margin):
        """
        Cuma 2 kemungkinan hasil: "verified" (Hadi) atau "unknown".
        Semua yang dulunya "unverified" (crop kecil/buram, margin tipis,
        prediksi gagal, dst) sekarang dianggap "unknown" - lebih baik
        dibilang Unknown daripada salah bilang Hadi.
        """
        if (
            pred_label == "hadi"
            and confidence >= self.verified_threshold
            and margin >= self.min_margin
        ):
            return "verified"

        return "unknown"

    def _get_display_label(self, status, confidence, margin):
        if status == "verified":
            return f"Hadi {confidence:.2f}"

        return f"Unknown {confidence:.2f}"

    def _unknown_result(self, reason):
        return {
            "raw_label": reason,
            "confidence": 0.0,
            "top2_label": "none",
            "top2_confidence": 0.0,
            "margin": 0.0,
            "status": "unknown",
            "display_label": "Unknown 0.00",
        }