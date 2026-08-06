import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def calculate_iou(box_a, box_b) -> float:
    """
    Menghitung IoU atau Intersection over Union antara dua bounding box.

    Format box:
    [x1, y1, x2, y2]

    IoU dipakai untuk mengecek apakah box orang di frame sekarang
    kemungkinan besar masih orang yang sama dengan frame sebelumnya.
    """
    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[2], box_b[2])
    y_b = min(box_a[3], box_b[3])

    inter_width = max(0, x_b - x_a)
    inter_height = max(0, y_b - y_a)
    inter_area = inter_width * inter_height

    box_a_area = max(0, box_a[2] - box_a[0]) * max(0, box_a[3] - box_a[1])
    box_b_area = max(0, box_b[2] - box_b[0]) * max(0, box_b[3] - box_b[1])

    union_area = box_a_area + box_b_area - inter_area

    if union_area <= 0:
        return 0.0

    return inter_area / union_area


@dataclass
class RecognitionEntry:
    """
    Menyimpan hasil recognition terakhir untuk satu orang.
    """
    entry_id: int
    bbox: Tuple[int, int, int, int]
    frame_id: int

    identity_status: str = "unknown"
    identity_label: str = "unknown"
    recognition_confidence: float = 0.0
    recognition_margin: float = 0.0

    last_recognition_frame: int = -999999

    # (BARU) Jam dinding, HANYA untuk tampilan "sudah berapa lama di frame".
    # Tidak dipakai sama sekali untuk logika matching / TTL / interval.
    first_seen_ts: float = field(default_factory=time.time)
    last_seen_ts: float = field(default_factory=time.time)


class RecognitionCache:
    """
    Cache sederhana untuk menyimpan label terakhir.

    Tujuannya:
    - classifier tidak perlu jalan setiap frame
    - label terakhir bisa dipakai ulang
    - FPS lebih stabil
    """

    def __init__(
        self,
        recognition_interval: int = 10,
        cache_ttl_frames: int = 30,
        iou_threshold: float = 0.35,
    ):
        self.recognition_interval = max(1, recognition_interval)
        self.cache_ttl_frames = max(1, cache_ttl_frames)
        self.iou_threshold = iou_threshold

        self.entries: Dict[int, RecognitionEntry] = {}
        self.next_entry_id = 1

    def _find_best_match(
        self,
        bbox: Tuple[int, int, int, int],
        frame_id: int
    ) -> Tuple[Optional[int], Optional[RecognitionEntry], float]:
        """
        Mencari entry cache yang paling cocok berdasarkan IoU.
        """
        best_entry_id = None
        best_entry = None
        best_iou = 0.0

        for entry_id, entry in self.entries.items():
            age = frame_id - entry.frame_id

            if age > self.cache_ttl_frames:
                continue

            iou = calculate_iou(bbox, entry.bbox)

            if iou > best_iou:
                best_iou = iou
                best_entry_id = entry_id
                best_entry = entry

        if best_iou >= self.iou_threshold:
            return best_entry_id, best_entry, best_iou

        return None, None, best_iou

    def get_or_create_entry(
        self,
        bbox: Tuple[int, int, int, int],
        frame_id: int
    ) -> Tuple[int, RecognitionEntry, bool]:
        """
        Ambil entry yang cocok.
        Kalau tidak ada, buat entry baru.

        Return:
        - entry_id
        - entry
        - is_new_entry
        """
        entry_id, entry, _ = self._find_best_match(bbox, frame_id)

        if entry is not None:
            entry.bbox = bbox
            entry.frame_id = frame_id
            entry.last_seen_ts = time.time()   # (BARU) catat masih terlihat
            return entry_id, entry, False

        entry_id = self.next_entry_id
        self.next_entry_id += 1

        entry = RecognitionEntry(
            entry_id=entry_id,
            bbox=bbox,
            frame_id=frame_id,
        )

        self.entries[entry_id] = entry

        return entry_id, entry, True

    def should_run_recognition(
        self,
        entry: RecognitionEntry,
        frame_id: int
    ) -> bool:
        """
        Menentukan apakah classifier perlu jalan atau cukup pakai cache.
        """
        if entry.last_recognition_frame < 0:
            return True

        frame_gap = frame_id - entry.last_recognition_frame

        if frame_gap >= self.recognition_interval:
            return True

        return False

    def update_recognition(
        self,
        entry_id: int,
        bbox: Tuple[int, int, int, int],
        frame_id: int,
        identity_status: str,
        identity_label: str,
        recognition_confidence: float,
        recognition_margin: float = 0.0,
    ):
        """
        Update hasil recognition terbaru ke cache.
        """
        if entry_id not in self.entries:
            self.entries[entry_id] = RecognitionEntry(
                entry_id=entry_id,
                bbox=bbox,
                frame_id=frame_id,
            )

        entry = self.entries[entry_id]

        entry.bbox = bbox
        entry.frame_id = frame_id
        entry.identity_status = identity_status
        entry.identity_label = identity_label
        entry.recognition_confidence = float(recognition_confidence)
        entry.recognition_margin = float(recognition_margin)
        entry.last_recognition_frame = frame_id
        entry.last_seen_ts = time.time()   # (BARU)

    def get_display_result(self, entry: RecognitionEntry) -> Dict[str, Any]:
        """
        Mengambil hasil cache untuk ditampilkan di visualizer/log.
        """
        return {
            "identity_status": entry.identity_status,
            "identity_label": entry.identity_label,
            "recognition_confidence": entry.recognition_confidence,
            "recognition_margin": entry.recognition_margin,
            "cache_entry_id": entry.entry_id,
            "from_cache": True,
        }

    def get_active_persons(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        (BARU) Daftar orang yang SEDANG dilacak, untuk panel dashboard.

        Read-only: tidak mengubah isi cache sama sekali.
        Diurutkan dari yang paling lama berada di frame.
        """
        now = time.time()
        people = []

        for entry in self.entries.values():
            duration = max(0.0, now - entry.first_seen_ts)
            people.append({
                "entry_id": entry.entry_id,
                "identity_status": entry.identity_status,
                "identity_label": entry.identity_label,
                "recognition_confidence": round(float(entry.recognition_confidence), 4),
                "first_seen": datetime.fromtimestamp(entry.first_seen_ts).strftime("%H:%M:%S"),
                "duration_seconds": int(duration),
            })

        people.sort(key=lambda p: p["duration_seconds"], reverse=True)
        return people[:limit]

    def cleanup(self, current_frame_id: int):
        """
        Menghapus cache lama agar tidak menumpuk.
        """
        expired_ids = []

        for entry_id, entry in self.entries.items():
            age = current_frame_id - entry.frame_id

            if age > self.cache_ttl_frames:
                expired_ids.append(entry_id)

        for entry_id in expired_ids:
            del self.entries[entry_id]