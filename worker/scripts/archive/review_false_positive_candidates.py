from pathlib import Path
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]

CANDIDATES_PATH = ROOT_DIR / "outputs" / "logs" / "negative_only_candidates.csv"
SUMMARY_PATH = ROOT_DIR / "outputs" / "logs" / "false_positive_review_summary.csv"


def main():
    print("=" * 70)
    print("[INFO] Review False Positive Candidates")
    print("=" * 70)

    if not CANDIDATES_PATH.exists():
        print("[ERROR] File negative_only_candidates.csv tidak ditemukan.")
        print()
        print("Solusi:")
        print("1. Jalankan scripts/evaluate_negative_only.py dulu.")
        print("2. Pastikan ada kandidat false positive.")
        return

    if CANDIDATES_PATH.stat().st_size == 0:
        print("[INFO] File candidates ada, tetapi kosong.")
        print("[INFO] Artinya tidak ada kandidat false positive.")
        return

    df = pd.read_csv(CANDIDATES_PATH)

    if df.empty:
        print("[INFO] Tidak ada kandidat false positive.")
        return

    print(f"[INFO] Total kandidat false positive: {len(df)}")
    print()

    print("[INFO] Kolom tersedia:")
    for col in df.columns:
        print(f"- {col}")

    print()

    # Ringkasan status
    if "identity_status" in df.columns:
        print("[INFO] Jumlah berdasarkan identity_status:")
        print(df["identity_status"].value_counts())
        print()

    # Ringkasan label
    if "identity_label" in df.columns:
        print("[INFO] Jumlah berdasarkan identity_label:")
        print(df["identity_label"].value_counts())
        print()

    # Ringkasan frame
    if "frame_id" in df.columns:
        print("[INFO] Top 20 frame_id dengan kandidat terbanyak:")
        print(df["frame_id"].value_counts().head(20))
        print()

    # Ringkasan confidence
    if "recognition_confidence" in df.columns:
        conf = pd.to_numeric(df["recognition_confidence"], errors="coerce").dropna()

        if not conf.empty:
            print("[INFO] Confidence kandidat false positive:")
            print(f"Rata-rata : {conf.mean():.4f}")
            print(f"Tertinggi : {conf.max():.4f}")
            print(f"Terendah  : {conf.min():.4f}")
            print()

    # Ringkasan margin
    if "recognition_margin" in df.columns:
        margin = pd.to_numeric(df["recognition_margin"], errors="coerce").dropna()

        if not margin.empty:
            print("[INFO] Margin kandidat false positive:")
            print(f"Rata-rata : {margin.mean():.4f}")
            print(f"Tertinggi : {margin.max():.4f}")
            print(f"Terendah  : {margin.min():.4f}")
            print()

    # Ringkasan cache
    if "from_cache" in df.columns:
        print("[INFO] Jumlah berdasarkan from_cache:")
        print(df["from_cache"].value_counts())
        print()

    # Simpan ringkasan sederhana
    summary_rows = []

    summary_rows.append({
        "metric": "total_false_positive_candidates",
        "value": len(df),
    })

    if "frame_id" in df.columns:
        summary_rows.append({
            "metric": "unique_frame_id",
            "value": df["frame_id"].nunique(),
        })

    if "recognition_confidence" in df.columns:
        conf = pd.to_numeric(df["recognition_confidence"], errors="coerce").dropna()
        if not conf.empty:
            summary_rows.extend([
                {"metric": "avg_recognition_confidence", "value": round(conf.mean(), 4)},
                {"metric": "max_recognition_confidence", "value": round(conf.max(), 4)},
                {"metric": "min_recognition_confidence", "value": round(conf.min(), 4)},
            ])

    if "recognition_margin" in df.columns:
        margin = pd.to_numeric(df["recognition_margin"], errors="coerce").dropna()
        if not margin.empty:
            summary_rows.extend([
                {"metric": "avg_recognition_margin", "value": round(margin.mean(), 4)},
                {"metric": "max_recognition_margin", "value": round(margin.max(), 4)},
                {"metric": "min_recognition_margin", "value": round(margin.min(), 4)},
            ])

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print(f"[INFO] Summary disimpan ke: {SUMMARY_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()