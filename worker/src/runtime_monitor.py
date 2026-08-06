import csv
import json
from pathlib import Path
from datetime import datetime


class RuntimeMonitor:
    """
    RuntimeMonitor dipakai untuk mencatat performa selama program berjalan.

    Yang dicatat:
    - durasi program
    - total frame
    - total deteksi
    - rata-rata FPS
    - FPS min/max
    - failed read
    - jumlah status identity
    - jumlah data dari cache dan classifier asli
    """

    def __init__(
        self,
        camera_name="kamera_1",
        source_type="unknown",
        summary_json_path="outputs/logs/runtime_summary.json",
        summary_csv_path="outputs/logs/runtime_summary.csv",
    ):
        self.camera_name = camera_name
        self.source_type = source_type

        self.summary_json_path = Path(summary_json_path)
        self.summary_csv_path = Path(summary_csv_path)

        self.start_time = datetime.now()
        self.end_time = None

        self.total_frames = 0
        self.total_failed_reads = 0
        self.total_detections = 0

        self.fps_values = []

        self.status_counts = {
            "verified": 0,
            "unknown": 0,
            "unverified": 0,
            "person": 0,
            "other": 0,
        }

        self.cache_true = 0
        self.cache_false = 0

    def add_failed_read(self):
        """
        Dipanggil saat reader.read() gagal membaca frame.
        """
        self.total_failed_reads += 1

    def update_frame(self, frame_id, fps, detections):
        """
        Dipanggil setiap frame berhasil diproses.
        """
        self.total_frames = frame_id

        if fps is not None and fps > 0:
            self.fps_values.append(float(fps))

        detection_count = len(detections)
        self.total_detections += detection_count

        for detection in detections:
            status = str(detection.get("status", "other")).lower().strip()

            if status in self.status_counts:
                self.status_counts[status] += 1
            else:
                self.status_counts["other"] += 1

            from_cache = detection.get("from_cache", False)

            if str(from_cache).lower() == "true":
                self.cache_true += 1
            else:
                self.cache_false += 1

    def get_summary(self):
        """
        Menghasilkan ringkasan runtime dalam bentuk dictionary.
        """
        self.end_time = datetime.now()

        duration_seconds = (self.end_time - self.start_time).total_seconds()

        if self.fps_values:
            avg_fps = sum(self.fps_values) / len(self.fps_values)
            min_fps = min(self.fps_values)
            max_fps = max(self.fps_values)
        else:
            avg_fps = 0.0
            min_fps = 0.0
            max_fps = 0.0

        total_cache_data = self.cache_true + self.cache_false

        if total_cache_data > 0:
            cache_rate = self.cache_true / total_cache_data * 100
        else:
            cache_rate = 0.0

        summary = {
            "camera_name": self.camera_name,
            "source_type": self.source_type,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(duration_seconds, 2),
            "total_frames": self.total_frames,
            "total_failed_reads": self.total_failed_reads,
            "total_detections": self.total_detections,
            "avg_fps": round(avg_fps, 2),
            "min_fps": round(min_fps, 2),
            "max_fps": round(max_fps, 2),
            "status_verified": self.status_counts.get("verified", 0),
            "status_unknown": self.status_counts.get("unknown", 0),
            "status_unverified": self.status_counts.get("unverified", 0),
            "status_person": self.status_counts.get("person", 0),
            "status_other": self.status_counts.get("other", 0),
            "from_cache_true": self.cache_true,
            "from_cache_false": self.cache_false,
            "cache_rate_percent": round(cache_rate, 2),
        }

        return summary

    def save_summary(self):
        """
        Menyimpan summary ke JSON dan CSV.
        JSON ditimpa setiap run.
        CSV ditambahkan sebagai histori setiap run.
        """
        summary = self.get_summary()

        self.summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.summary_json_path, "w", encoding="utf-8") as file:
            json.dump(summary, file, indent=4)

        csv_exists = self.summary_csv_path.exists()

        with open(self.summary_csv_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(summary.keys()))

            if not csv_exists:
                writer.writeheader()

            writer.writerow(summary)

        print()
        print("=" * 70)
        print("[RUNTIME SUMMARY]")
        print("=" * 70)
        print(f"Camera              : {summary['camera_name']}")
        print(f"Source type         : {summary['source_type']}")
        print(f"Duration            : {summary['duration_seconds']} detik")
        print(f"Total frames        : {summary['total_frames']}")
        print(f"Total detections    : {summary['total_detections']}")
        print(f"Failed reads        : {summary['total_failed_reads']}")
        print(f"Avg FPS             : {summary['avg_fps']}")
        print(f"Min FPS             : {summary['min_fps']}")
        print(f"Max FPS             : {summary['max_fps']}")
        print(f"Verified            : {summary['status_verified']}")
        print(f"Unknown             : {summary['status_unknown']}")
        print(f"Unverified          : {summary['status_unverified']}")
        print(f"From cache True     : {summary['from_cache_true']}")
        print(f"From cache False    : {summary['from_cache_false']}")
        print(f"Cache rate          : {summary['cache_rate_percent']}%")
        print("-" * 70)
        print(f"[DONE] Summary JSON : {self.summary_json_path}")
        print(f"[DONE] Summary CSV  : {self.summary_csv_path}")