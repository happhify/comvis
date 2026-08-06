"""
app/model_quality.py  (Tahap Kualitas Model)

Menyediakan data "Kualitas Model" untuk dashboard:
- Ambang (threshold) yang SEDANG dipakai, dibaca dari config/camera.yaml
- Hasil negative-only test terakhir  (outputs/logs/negative_only_summary.csv)
- Hasil positive test terakhir       (outputs/logs/positive_test_summary.csv)
- Kesimpulan jujur: boleh / belum boleh menganggap 'Verified' final

Semua read-only. Kalau file belum ada -> ditandai "belum tersedia",
BUKAN diisi angka karangan.
"""

import csv
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "camera.yaml"
NEGATIVE_SUMMARY = PROJECT_ROOT / "outputs" / "logs" / "negative_only_summary.csv"
POSITIVE_SUMMARY = PROJECT_ROOT / "outputs" / "logs" / "positive_test_summary.csv"

# Setelah positive test Hadi selesai DAN hasilnya dinyatakan bagus, ubah
# nilai ini menjadi True. Selama False, verdict selalu "belum final".
POSITIVE_TEST_DONE = False


def _to_float(value, default=None):
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _to_int(value, default=None):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def _last_row(path):
    """Baris terakhir (paling baru) dari CSV ber-header. None kalau tidak ada."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return None
    return rows[-1] if rows else None


def read_thresholds():
    """Ambang yang sedang dipakai, langsung dari config/camera.yaml."""
    if not CONFIG_PATH.exists():
        return {"available": False}

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return {"available": False}

    rec = cfg.get("recognition") or {}
    det = cfg.get("detection") or {}
    rt = cfg.get("realtime") or {}

    return {
        "available": True,
        "verified_threshold": rec.get("verified_threshold"),
        "unknown_threshold": rec.get("unknown_threshold"),
        "min_margin": rec.get("min_margin"),
        "min_crop_width": rec.get("min_crop_width"),
        "min_crop_height": rec.get("min_crop_height"),
        "detection_confidence": det.get("confidence_threshold"),
        "recognition_interval": rt.get("recognition_interval"),
        "cache_ttl_frames": rt.get("cache_ttl_frames"),
        "cache_iou_threshold": rt.get("cache_iou_threshold"),
    }


def read_negative_test():
    row = _last_row(NEGATIVE_SUMMARY)
    if row is None:
        return {"available": False}

    return {
        "available": True,
        "generated_at": row.get("generated_at"),
        "target_label": row.get("target_label"),
        "total_rows": _to_int(row.get("total_detection_rows")),
        "verified_target_rows": _to_int(row.get("total_verified_target")),
        "false_positive_candidate": _to_int(row.get("false_positive_candidate")),
        "false_positive_rate": _to_float(row.get("false_positive_rate")),
        "evaluation_status": row.get("evaluation_status"),
        "window_start": row.get("log_start_time"),
        "window_end": row.get("log_end_time"),
    }


def read_positive_test():
    row = _last_row(POSITIVE_SUMMARY)
    if row is None:
        return {"available": False}

    return {
        "available": True,
        "generated_at": row.get("generated_at"),
        "target_label": row.get("target_label"),
        "num_windows": _to_int(row.get("num_windows")),
        "windows": row.get("windows"),
        "total_rows": _to_int(row.get("total_detection_rows")),
        "verified_target_rows": _to_int(row.get("verified_target_rows")),
        "verified_nontarget_rows": _to_int(row.get("verified_nontarget_rows")),
        "unverified_rows": _to_int(row.get("unverified_rows")),
        "unknown_rows": _to_int(row.get("unknown_rows")),
        "verified_target_rate": _to_float(row.get("verified_target_rate")),
        "unverified_rate": _to_float(row.get("unverified_rate")),
        "unknown_rate": _to_float(row.get("unknown_rate")),
        "evaluation_status": row.get("evaluation_status"),
    }


def build_verdict(negative, positive):
    """Kesimpulan jujur - sengaja tidak melebih-lebihkan."""
    fp = negative.get("false_positive_candidate") if negative.get("available") else None

    if not POSITIVE_TEST_DONE:
        if fp is not None and fp > 0:
            return {
                "level": "crit",
                "title": "Belum layak dianggap final",
                "detail": (
                    f"Negative-only test menemukan {fp} kandidat false positive, "
                    "dan positive test belum dinyatakan selesai. "
                    "Label 'Verified' masih mungkin salah."
                ),
            }
        return {
            "level": "warn",
            "title": "Belum tervalidasi penuh",
            "detail": (
                "Positive test belum dinyatakan selesai, jadi label 'Verified' "
                "belum bisa dianggap final."
            ),
        }

    if fp is not None and fp > 0:
        return {
            "level": "crit",
            "title": "Masih ada kandidat false positive",
            "detail": (
                f"Positive test sudah selesai, tetapi negative test masih menemukan "
                f"{fp} kandidat false positive."
            ),
        }

    return {
        "level": "ok",
        "title": "Tervalidasi (batas prototype)",
        "detail": (
            "Positive test selesai dan negative test tidak menemukan kandidat "
            "false positive."
        ),
    }


def get_model_quality():
    """Dipanggil endpoint /api/model-quality."""
    negative = read_negative_test()
    positive = read_positive_test()

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "positive_test_done": POSITIVE_TEST_DONE,
        "principle": (
            "Lebih baik Unverified daripada salah Verified. "
            "Sistem sengaja dibuat konservatif."
        ),
        "thresholds": read_thresholds(),
        "negative_test": negative,
        "positive_test": positive,
        "verdict": build_verdict(negative, positive),
    }