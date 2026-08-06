from pathlib import Path
from datetime import datetime
import argparse

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]

LOG_PATH = ROOT_DIR / "outputs" / "logs" / "detection_log.csv"
SUMMARY_PATH = ROOT_DIR / "outputs" / "logs" / "negative_only_summary.csv"
CANDIDATES_PATH = ROOT_DIR / "outputs" / "logs" / "negative_only_candidates.csv"


def find_column(df, candidates):
    """
    Mencari kolom berdasarkan beberapa kemungkinan nama.

    Ini dibuat agar script tetap bisa membaca log lama maupun log baru.
    """
    if df is None or df.empty:
        return None

    lower_map = {
        str(col).lower().strip(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lower_map:
            return lower_map[key]

    return None


def normalize_text_series(series):
    """
    Mengubah isi kolom menjadi lowercase dan aman dari NaN.
    """
    return (
        series
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
    )


def parse_dt(text):
    """Ubah teks jadi datetime. Return None kalau kosong/tidak dikenal."""
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(str(text).strip(), fmt)
        except ValueError:
            continue
    return None


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def main():
    parser = argparse.ArgumentParser(
        description="Negative-only evaluation untuk Sistem Deteksi Employee dan Unknown."
    )

    parser.add_argument(
        "--target-label",
        default="hadi",
        help="Label employee yang sedang diuji. Default: hadi"
    )

    parser.add_argument(
        "--start",
        default=None,
        help='Awal jendela waktu: "YYYY-MM-DD HH:MM:SS". Kosong = seluruh log.'
    )

    parser.add_argument(
        "--end",
        default=None,
        help='Akhir jendela waktu: "YYYY-MM-DD HH:MM:SS". Kosong = seluruh log.'
    )

    args = parser.parse_args()

    start_dt = parse_dt(args.start)
    end_dt = parse_dt(args.end)

    if args.start and start_dt is None:
        print('[ERROR] Format --start salah. Contoh: "2026-07-22 10:01:26"')
        return
    if args.end and end_dt is None:
        print('[ERROR] Format --end salah. Contoh: "2026-07-22 10:42:20"')
        return

    target_label = args.target_label.lower().strip()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print("[INFO] Negative-only Evaluation")
    print("=" * 70)
    print(f"[INFO] Target label: {target_label}")
    print(f"[INFO] Log path    : {LOG_PATH}")
    print("=" * 70)

    if not LOG_PATH.exists():
        print("[ERROR] detection_log.csv tidak ditemukan.")
        print()
        print("Solusi:")
        print("1. Jalankan main.py terlebih dahulu.")
        print("2. Pastikan output log tersimpan di outputs/logs/detection_log.csv.")
        return

    if LOG_PATH.stat().st_size == 0:
        print("[ERROR] detection_log.csv ada, tetapi kosong.")
        print()
        print("Solusi:")
        print("1. Jalankan main.py sampai ada deteksi orang.")
        print("2. Jalankan ulang script ini.")
        return

    try:
        df = pd.read_csv(LOG_PATH)
    except Exception as e:
        print("[ERROR] Gagal membaca detection_log.csv")
        print(e)
        return

    if df.empty:
        print("[ERROR] detection_log.csv berhasil dibaca, tetapi tidak memiliki baris data.")
        return

    # ============================================================
    # Cari kolom penting
    # ============================================================

    status_col = find_column(df, [
        "identity_status",
        "status",
        "recognition_status",
    ])

    label_col = find_column(df, [
        "identity_label",
        "identity_raw_label",
        "raw_label",
        "classifier_label",
        "pred_label",
        "label",
    ])

    confidence_col = find_column(df, [
        "recognition_confidence",
        "identity_confidence",
        "classifier_confidence",
        "confidence_recognition",
        "recognition_conf",
    ])

    margin_col = find_column(df, [
        "recognition_margin",
        "identity_margin",
        "classifier_margin",
        "margin",
    ])

    camera_col = find_column(df, [
        "camera_name",
        "camera",
        "nama_kamera",
    ])

    frame_col = find_column(df, [
        "frame_id",
        "frame",
        "frame_number",
        "frame_index",
    ])

    cache_col = find_column(df, [
        "from_cache",
        "is_from_cache",
        "recognition_from_cache",
    ])

    timestamp_col = find_column(df, [
        "timestamp",
        "time",
        "datetime",
        "created_at",
    ])

    # ============================================================
    # (BARU) Batasi ke jendela waktu
    # ============================================================
    # Tanpa ini, log yang sudah berisi banyak hari DAN beberapa versi
    # model akan tercampur jadi satu angka rata-rata yang menyesatkan.
    if timestamp_col is not None:
        parsed_all = pd.to_datetime(df[timestamp_col], errors="coerce")

        if start_dt is not None or end_dt is not None:
            mask = parsed_all.notna()
            if start_dt is not None:
                mask = mask & (parsed_all >= pd.Timestamp(start_dt))
            if end_dt is not None:
                mask = mask & (parsed_all <= pd.Timestamp(end_dt))

            df = df[mask].copy()
            print(f"[INFO] Jendela waktu aktif -> {len(df)} baris dipakai.")

            if df.empty:
                print("[ERROR] Tidak ada baris pada jendela waktu itu.")
                print("        Cek lagi jam --start / --end.")
                return
        else:
            valid_all = parsed_all.dropna()
            if not valid_all.empty and valid_all.dt.date.nunique() > 1:
                print("=" * 70)
                print(f"[PERINGATAN] Log berisi {valid_all.dt.date.nunique()} hari berbeda,")
                print("             kemungkinan dari beberapa versi model.")
                print("             Hasil di bawah adalah RATA-RATA CAMPURAN,")
                print("             bukan ukuran satu model.")
                print("             Pakai --start dan --end untuk membatasi satu run.")
                print("=" * 70)

    if status_col is None:
        print("[ERROR] Kolom identity_status/status tidak ditemukan.")
        print()
        print("Solusi:")
        print("1. Pastikan logger mencatat kolom identity_status.")
        print("2. Jalankan ulang main.py setelah logger diperbaiki.")
        return

    status_series = normalize_text_series(df[status_col])

    if label_col is not None:
        label_series = normalize_text_series(df[label_col])
    else:
        label_series = pd.Series([""] * len(df))

    # ============================================================
    # Aturan negative-only
    # ============================================================
    #
    # Karena Hadi diasumsikan tidak masuk frame:
    # - Baris verified + label hadi = kandidat false positive.
    #
    # Jika label_col tidak ada:
    # - Semua status verified dianggap kandidat, karena kita tidak tahu labelnya.
    # ============================================================

    verified_mask = status_series.eq("verified")

    if label_col is not None:
        verified_target_mask = verified_mask & label_series.eq(target_label)
    else:
        verified_target_mask = verified_mask

    candidates_df = df[verified_target_mask].copy()

    total_detection_rows = len(df)
    total_verified_rows = int(verified_mask.sum())
    total_verified_target = int(verified_target_mask.sum())
    false_positive_candidate = total_verified_target

    if total_detection_rows > 0:
        false_positive_rate = false_positive_candidate / total_detection_rows
    else:
        false_positive_rate = 0.0

    if false_positive_candidate == 0:
        evaluation_status = "PASS_NEGATIVE_ONLY"
        recommendation = "Tidak ada Verified target saat target tidak masuk frame. Negative-only test sementara cukup aman."
    else:
        evaluation_status = "WARNING_FALSE_POSITIVE_CANDIDATE"
        recommendation = "Ada Verified target saat target tidak masuk frame. Perlu cek manual video/crop dan lakukan hard negative mining jika benar false positive."

    # ============================================================
    # Tambahan statistik
    # ============================================================

    avg_confidence = "-"
    max_confidence = "-"
    min_confidence = "-"

    if confidence_col is not None:
        conf_values = pd.to_numeric(df[confidence_col], errors="coerce").dropna()
        if not conf_values.empty:
            avg_confidence = round(float(conf_values.mean()), 4)
            max_confidence = round(float(conf_values.max()), 4)
            min_confidence = round(float(conf_values.min()), 4)

    avg_margin = "-"
    max_margin = "-"
    min_margin = "-"

    if margin_col is not None:
        margin_values = pd.to_numeric(df[margin_col], errors="coerce").dropna()
        if not margin_values.empty:
            avg_margin = round(float(margin_values.mean()), 4)
            max_margin = round(float(margin_values.max()), 4)
            min_margin = round(float(margin_values.min()), 4)

    cache_true = "-"
    cache_false = "-"
    cache_rate = "-"

    if cache_col is not None:
        cache_series = normalize_text_series(df[cache_col])
        cache_true_count = int(cache_series.isin(["true", "1", "yes"]).sum())
        cache_false_count = int(cache_series.isin(["false", "0", "no"]).sum())
        cache_total_known = cache_true_count + cache_false_count

        cache_true = cache_true_count
        cache_false = cache_false_count

        if cache_total_known > 0:
            cache_rate = round(cache_true_count / cache_total_known, 4)

    camera_summary = "-"

    if camera_col is not None:
        camera_counts = df[camera_col].astype(str).value_counts().to_dict()
        camera_summary = str(camera_counts)

    unique_frames = "-"

    if frame_col is not None:
        unique_frames = int(df[frame_col].nunique())

    log_start_time = "-"
    log_end_time = "-"

    if timestamp_col is not None:
        parsed_time = pd.to_datetime(df[timestamp_col], errors="coerce")
        if parsed_time.notna().any():
            valid_time = parsed_time.dropna()
            log_start_time = str(valid_time.min())
            log_end_time = str(valid_time.max())

    # ============================================================
    # Simpan kandidat false positive
    # ============================================================

    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not candidates_df.empty:
        candidates_df.to_csv(CANDIDATES_PATH, index=False)
    else:
        # Tetap buat file kosong dengan header agar jelas bahwa evaluasi sudah jalan
        candidates_df.to_csv(CANDIDATES_PATH, index=False)

    # ============================================================
    # Simpan summary
    # ============================================================

    summary_row = {
        "generated_at": generated_at,
        "target_label": target_label,
        "assumption": "target_not_in_frame",
        "window_start": args.start or "(seluruh log)",
        "window_end": args.end or "(seluruh log)",
        "total_detection_rows": total_detection_rows,
        "unique_frames": unique_frames,
        "total_verified_rows": total_verified_rows,
        "total_verified_target": total_verified_target,
        "false_positive_candidate": false_positive_candidate,
        "false_positive_rate": round(false_positive_rate, 6),
        "evaluation_status": evaluation_status,
        "avg_recognition_confidence": avg_confidence,
        "max_recognition_confidence": max_confidence,
        "min_recognition_confidence": min_confidence,
        "avg_recognition_margin": avg_margin,
        "max_recognition_margin": max_margin,
        "min_recognition_margin": min_margin,
        "from_cache_true": cache_true,
        "from_cache_false": cache_false,
        "cache_rate": cache_rate,
        "camera_summary": camera_summary,
        "log_start_time": log_start_time,
        "log_end_time": log_end_time,
        "recommendation": recommendation,
    }

    summary_df = pd.DataFrame([summary_row])

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if SUMMARY_PATH.exists() and SUMMARY_PATH.stat().st_size > 0:
        old_summary = pd.read_csv(SUMMARY_PATH)
        combined_summary = pd.concat([old_summary, summary_df], ignore_index=True)
        combined_summary.to_csv(SUMMARY_PATH, index=False)
    else:
        summary_df.to_csv(SUMMARY_PATH, index=False)

    # ============================================================
    # Print hasil ke terminal
    # ============================================================

    print()
    print("[INFO] Hasil Negative-only Evaluation")
    print("-" * 70)
    print(f"Target label              : {target_label}")
    print(f"Total detection rows      : {total_detection_rows}")
    print(f"Unique frames             : {unique_frames}")
    print(f"Total verified rows       : {total_verified_rows}")
    print(f"Total verified target     : {total_verified_target}")
    print(f"False positive candidate  : {false_positive_candidate}")
    print(f"False positive rate       : {false_positive_rate:.6f}")
    print(f"Evaluation status         : {evaluation_status}")
    print()
    print(f"[INFO] Summary saved to    : {SUMMARY_PATH}")
    print(f"[INFO] Candidates saved to : {CANDIDATES_PATH}")
    print("=" * 70)

    print()
    print("[CATATAN]")
    print(recommendation)


if __name__ == "__main__":
    main()