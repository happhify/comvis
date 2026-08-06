"""
scripts/validate_threshold.py

Memvalidasi usulan verified_threshold pada JENDELA WAKTU ketika target
DIPASTIKAN TIDAK ADA di frame (mis. long run test).

Kenapa jendela seperti itu berharga: kalau target tidak ada, maka SETIAP
baris 'Verified <target>' pasti salah. Ground truth-nya otomatis, tidak
perlu penilaian manual sama sekali.

Yang dihitung: kalau ambang dinaikkan, berapa banyak false positive yang
lenyap. (Biaya recall-nya tidak terlihat di sini - itu diukur dari data
positif, terpisah.)

Contoh:
  python scripts/validate_threshold.py --start "2026-07-21 11:04:21" --end "2026-07-21 11:36:16"
"""

import argparse
import csv
import os
from datetime import datetime

LOG_PATH = "outputs/logs/detection_log.csv"


def parse_dt(text):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(str(text).strip(), fmt)
        except ValueError:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Validasi ambang pada jendela tanpa target di frame."
    )
    parser.add_argument("--start", required=True, help='"YYYY-MM-DD HH:MM:SS"')
    parser.add_argument("--end", required=True, help='"YYYY-MM-DD HH:MM:SS"')
    parser.add_argument("--target-label", default="hadi")
    args = parser.parse_args()

    start_dt, end_dt = parse_dt(args.start), parse_dt(args.end)
    target = args.target_label.lower().strip()

    print()
    print("=" * 72)
    print("VALIDASI AMBANG - jendela TANPA target di frame")
    print("=" * 72)
    print(f"Jendela : {args.start}  ->  {args.end}")
    print(f"Target  : {target}")

    if start_dt is None or end_dt is None or end_dt <= start_dt:
        print("[ERROR] Format waktu salah, atau --end tidak lebih lambat dari --start.")
        return

    if not os.path.exists(LOG_PATH):
        print(f"[ERROR] {LOG_PATH} tidak ditemukan.")
        return

    total_rows = 0
    fp_conf = []

    with open(LOG_PATH, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ts = parse_dt(row.get("timestamp", ""))
            if ts is None or ts < start_dt or ts > end_dt:
                continue

            total_rows += 1

            status = str(row.get("identity_status", "")).lower().strip()
            label = str(row.get("identity_label", "")).lower().strip()

            if status == "verified" and label == target:
                try:
                    fp_conf.append(float(row["recognition_confidence"]))
                except (KeyError, ValueError, TypeError):
                    pass

    print(f"\nBaris deteksi di jendela : {total_rows:,}")
    print(f"Baris 'Verified {target}'   : {len(fp_conf):,}   <-- SEMUANYA false positive")

    if total_rows == 0:
        print("\n[ERROR] Tidak ada baris di jendela itu. Cek jamnya.")
        return

    if not fp_conf:
        print("\n[BAGUS] Tidak ada false positive sama sekali di jendela ini.")
        return

    rate = len(fp_conf) / total_rows * 100
    print(f"Tingkat false positive   : {rate:.2f}% dari seluruh deteksi")

    s = sorted(fp_conf)
    n = len(s)
    print(f"\nConfidence false positive:")
    print(f"  min {s[0]:.4f} | p25 {s[n//4]:.4f} | median {s[n//2]:.4f} | "
          f"p75 {s[3*n//4]:.4f} | max {s[-1]:.4f}")

    print()
    print("-" * 72)
    print("Kalau verified_threshold dinaikkan:")
    print("-" * 72)
    print(f"{'AMBANG':>10}{'FP tersisa':>14}{'FP lenyap':>13}{'% lenyap':>12}")
    print("-" * 72)

    for ambang in (0.97, 0.98, 0.99, 0.9924, 0.995, 0.9966, 0.9984, 0.9994, 1.0):
        sisa = sum(1 for c in s if c >= ambang)
        lenyap = n - sisa
        print(f"{ambang:>10.4f}{sisa:>14,}{lenyap:>13,}{lenyap / n * 100:>11.1f}%")

    print("-" * 72)

    sisa_995 = sum(1 for c in s if c >= 0.995)
    print()
    print("=" * 72)
    print("KESIMPULAN")
    print("=" * 72)
    print(f"Pada ambang 0.9700 (sekarang) : {n:,} false positive")
    print(f"Pada ambang 0.9950 (usulan)   : {sisa_995:,} false positive "
          f"({(n - sisa_995) / n * 100:.1f}% lenyap)")
    print()
    if sisa_995 / n > 0.5:
        print("Ambang 0.995 TIDAK banyak menolong pada data baru ini.")
        print("Sebagian besar false positive punya confidence sangat tinggi.")
        print("-> Retrain dengan hard negative jadi satu-satunya jalan.")
    else:
        print("Ambang 0.995 memangkas cukup banyak false positive pada data baru.")
        print("Tetap perlu dicek biaya recall-nya dari data positif.")
    print("=" * 72)


if __name__ == "__main__":
    main()