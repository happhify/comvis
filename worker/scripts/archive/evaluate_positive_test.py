"""
scripts/evaluate_positive_test.py

Positive test: merangkum perilaku sistem saat TARGET (default: hadi)
BERADA di depan kamera, pada SATU ATAU BEBERAPA jendela waktu.

Dipakai kalau kamu hanya bisa "solo" (cuma target di frame) dalam burst
pendek 1-2 menit. Catat tiap burst, lalu masukkan semuanya:

  python scripts/evaluate_positive_test.py \
      --window "2026-07-15 10:03:00" "2026-07-15 10:04:30" \
      --window "2026-07-15 10:07:00" "2026-07-15 10:08:30"

Masih mendukung mode satu jendela lama:
  python scripts/evaluate_positive_test.py --start "..." --end "..."

Yang diukur (gabungan semua jendela):
- Verified target  (benar dikenali)                 -> "true positive"
- Unverified       (target ada tapi sistem ragu)    -> konservatif, WAJAR
- Unknown          (target dianggap bukan employee) -> terlewat

Sistem sengaja konservatif: lebih baik target Unverified daripada orang
lain salah jadi Verified. Angka Unverified yang cukup tinggi itu normal.
"""

from pathlib import Path
from datetime import datetime
import argparse

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]

LOG_PATH = ROOT_DIR / "outputs" / "logs" / "detection_log.csv"
SUMMARY_PATH = ROOT_DIR / "outputs" / "logs" / "positive_test_summary.csv"
MISSED_PATH = ROOT_DIR / "outputs" / "logs" / "positive_test_missed.csv"


def find_column(df, candidates):
    if df is None or df.empty:
        return None
    lower_map = {str(col).lower().strip(): col for col in df.columns}
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lower_map:
            return lower_map[key]
    return None


def normalize_text_series(series):
    return series.fillna("").astype(str).str.lower().str.strip()


def parse_dt(text):
    if text is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(str(text).strip(), fmt)
        except ValueError:
            continue
    return None


def stats_of(numeric_series):
    values = pd.to_numeric(numeric_series, errors="coerce").dropna()
    if values.empty:
        return "-", "-", "-"
    return (round(float(values.mean()), 4),
            round(float(values.max()), 4),
            round(float(values.min()), 4))


def count_status(status_series, label_series, target_label):
    verified = status_series.eq("verified")
    unverified = status_series.eq("unverified")
    unknown = status_series.eq("unknown")
    target = label_series.eq(target_label)
    return {
        "total": int(len(status_series)),
        "verified": int(verified.sum()),
        "verified_target": int((verified & target).sum()),
        "verified_nontarget": int((verified & ~target).sum()),
        "unverified": int(unverified.sum()),
        "unknown": int(unknown.sum()),
        "mask_verified_target": verified & target,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Positive test evaluation (target di frame, satu/beberapa jendela)."
    )
    parser.add_argument("--window", nargs=2, action="append", metavar=("MULAI", "SELESAI"),
                        help='Satu jendela solo: --window "MULAI" "SELESAI". Boleh diulang.')
    parser.add_argument("--start", help='(mode 1 jendela) "YYYY-MM-DD HH:MM:SS"')
    parser.add_argument("--end", help='(mode 1 jendela) "YYYY-MM-DD HH:MM:SS"')
    parser.add_argument("--target-label", default="hadi",
                        help="Label employee yang diuji. Default: hadi")
    args = parser.parse_args()

    target_label = args.target_label.lower().strip()
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Kumpulkan jendela dari --window (boleh banyak) atau --start/--end (satu)
    raw_windows = []
    if args.window:
        raw_windows = args.window
    elif args.start and args.end:
        raw_windows = [[args.start, args.end]]

    print("=" * 70)
    print("[INFO] Positive Test Evaluation")
    print("=" * 70)
    print(f"[INFO] Target label : {target_label}")
    print(f"[INFO] Jumlah jendela: {len(raw_windows)}")
    print(f"[INFO] Log path     : {LOG_PATH}")
    print("=" * 70)

    if not raw_windows:
        print('[ERROR] Beri jendela waktu: --window "MULAI" "SELESAI" (boleh diulang),')
        print('        atau mode lama: --start "..." --end "..."')
        return

    windows = []
    for w in raw_windows:
        s, e = parse_dt(w[0]), parse_dt(w[1])
        if s is None or e is None:
            print(f'[ERROR] Format waktu salah pada jendela: {w}. Contoh: "2026-07-15 10:03:00"')
            return
        if e <= s:
            print(f"[ERROR] SELESAI harus lebih lambat dari MULAI pada jendela: {w}")
            return
        windows.append((s, e, w[0], w[1]))

    if not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0:
        print("[ERROR] detection_log.csv tidak ada atau kosong. Jalankan main.py dulu.")
        return

    try:
        df = pd.read_csv(LOG_PATH)
    except Exception as e:
        print("[ERROR] Gagal membaca detection_log.csv")
        print(e)
        return

    if df.empty:
        print("[ERROR] detection_log.csv tidak punya baris data.")
        return

    timestamp_col = find_column(df, ["timestamp", "time", "datetime", "created_at"])
    status_col = find_column(df, ["identity_status", "status", "recognition_status"])
    label_col = find_column(df, ["identity_label", "identity_raw_label", "raw_label",
                                 "classifier_label", "pred_label", "label"])
    confidence_col = find_column(df, ["recognition_confidence", "identity_confidence",
                                      "classifier_confidence", "recognition_conf"])
    margin_col = find_column(df, ["recognition_margin", "identity_margin",
                                  "classifier_margin", "margin"])
    camera_col = find_column(df, ["camera_name", "camera", "nama_kamera"])
    frame_col = find_column(df, ["frame_id", "frame", "frame_number", "frame_index"])
    cache_col = find_column(df, ["from_cache", "is_from_cache", "recognition_from_cache"])

    if timestamp_col is None:
        print("[ERROR] Kolom timestamp tidak ditemukan; tidak bisa filter jendela waktu.")
        return
    if status_col is None:
        print("[ERROR] Kolom identity_status/status tidak ditemukan.")
        return

    ts = pd.to_datetime(df[timestamp_col], errors="coerce")

    # Gabungan (union) semua jendela
    union_mask = pd.Series(False, index=df.index)
    per_window = []
    for (s, e, ss, ee) in windows:
        wmask = ts.notna() & (ts >= pd.Timestamp(s)) & (ts <= pd.Timestamp(e))
        union_mask = union_mask | wmask
        sub = df[wmask]
        if sub.empty:
            per_window.append((ss, ee, None))
        else:
            c = count_status(normalize_text_series(sub[status_col]),
                             normalize_text_series(sub[label_col]) if label_col is not None
                             else pd.Series([""] * len(sub), index=sub.index),
                             target_label)
            per_window.append((ss, ee, c))

    win = df[union_mask].copy()
    if win.empty:
        print("[ERROR] Tidak ada baris log pada jendela-jendela itu.")
        print("        - Pastikan jam tiap --window sesuai jam kamu solo di frame.")
        print("        - Pastikan main.py berjalan & mencatat log saat itu.")
        return

    status_series = normalize_text_series(win[status_col])
    label_series = (normalize_text_series(win[label_col]) if label_col is not None
                    else pd.Series([""] * len(win), index=win.index))

    c = count_status(status_series, label_series, target_label)
    total = c["total"]
    tp = c["verified_target"]
    verified_rows = c["verified"]
    unverified_rows = c["unverified"]
    unknown_rows = c["unknown"]
    verified_nontarget_rows = c["verified_nontarget"]
    verified_target_mask = c["mask_verified_target"]

    verified_target_rate = tp / total
    unverified_rate = unverified_rows / total
    unknown_rate = unknown_rows / total

    missed_df = win[~verified_target_mask].copy()

    if verified_nontarget_rows > 0:
        evaluation_status = "WARNING_VERIFIED_WRONG_LABEL"
        recommendation = ("Ada baris Verified berlabel BUKAN target di jendela solo. "
                          "Perlu cek manual (harusnya tidak terjadi kalau benar-benar solo).")
    elif tp == 0:
        evaluation_status = "WARNING_NO_VERIFIED_TARGET"
        recommendation = ("Target tidak pernah Verified pada jendela ini. Cek jarak/pose/cahaya. "
                          "JANGAN ubah threshold dulu; bahas dulu di Tahap C.")
    else:
        evaluation_status = "OK_POSITIVE_MEASURED"
        recommendation = (
            f"Target Verified pada {verified_target_rate:.1%} baris; "
            f"Unverified {unverified_rate:.1%}, Unknown {unknown_rate:.1%}. "
            "Unverified tinggi itu sifat konservatif dan wajar. "
            "Bandingkan dengan negative test di Tahap C."
        )

    avg_conf, max_conf, min_conf = (stats_of(win[confidence_col])
                                    if confidence_col is not None else ("-", "-", "-"))
    avg_margin, max_margin, min_margin = (stats_of(win[margin_col])
                                          if margin_col is not None else ("-", "-", "-"))
    if confidence_col is not None and tp > 0:
        tgt_avg_conf, _, tgt_min_conf = stats_of(win.loc[verified_target_mask, confidence_col])
    else:
        tgt_avg_conf, tgt_min_conf = "-", "-"

    cache_true = cache_false = cache_rate = "-"
    if cache_col is not None:
        cache_series = normalize_text_series(win[cache_col])
        ct = int(cache_series.isin(["true", "1", "yes"]).sum())
        cf = int(cache_series.isin(["false", "0", "no"]).sum())
        cache_true, cache_false = ct, cf
        if ct + cf > 0:
            cache_rate = round(ct / (ct + cf), 4)

    unique_frames = int(win[frame_col].nunique()) if frame_col is not None else "-"
    camera_summary = "-"
    if camera_col is not None:
        camera_summary = str(win[camera_col].astype(str).value_counts().to_dict())

    windows_text = " ; ".join(f"{ss}->{ee}" for (_, _, ss, ee) in windows)

    MISSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    missed_df.to_csv(MISSED_PATH, index=False)

    summary_row = {
        "generated_at": generated_at,
        "target_label": target_label,
        "assumption": "target_in_frame",
        "num_windows": len(windows),
        "windows": windows_text,
        "total_detection_rows": total,
        "unique_frames": unique_frames,
        "verified_rows": verified_rows,
        "verified_target_rows": tp,
        "verified_nontarget_rows": verified_nontarget_rows,
        "unverified_rows": unverified_rows,
        "unknown_rows": unknown_rows,
        "verified_target_rate": round(verified_target_rate, 6),
        "unverified_rate": round(unverified_rate, 6),
        "unknown_rate": round(unknown_rate, 6),
        "avg_recognition_confidence": avg_conf,
        "max_recognition_confidence": max_conf,
        "min_recognition_confidence": min_conf,
        "verified_target_avg_confidence": tgt_avg_conf,
        "verified_target_min_confidence": tgt_min_conf,
        "avg_recognition_margin": avg_margin,
        "max_recognition_margin": max_margin,
        "min_recognition_margin": min_margin,
        "from_cache_true": cache_true,
        "from_cache_false": cache_false,
        "cache_rate": cache_rate,
        "camera_summary": camera_summary,
        "evaluation_status": evaluation_status,
        "recommendation": recommendation,
    }

    summary_df = pd.DataFrame([summary_row])
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SUMMARY_PATH.exists() and SUMMARY_PATH.stat().st_size > 0:
        old = pd.read_csv(SUMMARY_PATH)
        pd.concat([old, summary_df], ignore_index=True).to_csv(SUMMARY_PATH, index=False)
    else:
        summary_df.to_csv(SUMMARY_PATH, index=False)

    print()
    print("[INFO] Rincian per jendela")
    print("-" * 70)
    for i, (ss, ee, cc) in enumerate(per_window, 1):
        if cc is None:
            print(f"  Jendela {i} ({ss} -> {ee}): TIDAK ada baris log")
        else:
            print(f"  Jendela {i} ({ss} -> {ee}): total {cc['total']}, "
                  f"Verified-tgt {cc['verified_target']}, "
                  f"Unverified {cc['unverified']}, Unknown {cc['unknown']}")

    print()
    print("[INFO] Hasil GABUNGAN")
    print("-" * 70)
    print(f"Total baris (gabungan)     : {total}")
    print(f"Unique frames              : {unique_frames}")
    print(f"Verified (target)          : {tp}   ({verified_target_rate:.1%})")
    print(f"Unverified                 : {unverified_rows}   ({unverified_rate:.1%})")
    print(f"Unknown                    : {unknown_rows}   ({unknown_rate:.1%})")
    print(f"Verified label BUKAN target: {verified_nontarget_rows}")
    print(f"Confidence (verified tgt)  : avg {tgt_avg_conf} / min {tgt_min_conf}")
    print(f"Evaluation status          : {evaluation_status}")
    print()
    print(f"[INFO] Summary -> {SUMMARY_PATH}")
    print(f"[INFO] Missed  -> {MISSED_PATH}")
    print("=" * 70)
    print()
    print("[CATATAN]")
    print(recommendation)


if __name__ == "__main__":
    main()
    