"""
app/validation_reader.py  (FILE BARU - Tahap 10)

Menyediakan "status validasi model" untuk dashboard:
1. Apakah positive test Hadi sudah dilakukan (untuk sekarang: BELUM)
2. Apakah ada kandidat false positive di negative_only_summary.csv

Prinsip project: lebih baik Unverified daripada salah Verified Hadi.
Selama positive test belum final, dashboard wajib menampilkan warning.
"""

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEGATIVE_SUMMARY_PATH = PROJECT_ROOT / "outputs" / "logs" / "negative_only_summary.csv"

# ============================================================
# Setelah Tahap 11 (positive test Hadi) selesai DAN hasilnya
# dinyatakan bagus, ubah nilai ini menjadi True.
# Selama False, dashboard selalu menampilkan warning kuning.
# ============================================================
POSITIVE_TEST_DONE = False


def _to_int(value, default=None):
    """Convert nilai ke int secara aman. Gagal -> default."""
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def read_false_positive_candidate(path=NEGATIVE_SUMMARY_PATH):
    """
    Mencari nilai false_positive_candidate di negative_only_summary.csv.

    Toleran terhadap 2 kemungkinan bentuk CSV:
    1. Bentuk lebar  : ada KOLOM bernama false_positive_candidate
       contoh: total_rows,verified_rows,false_positive_candidate
               1523,3,3
    2. Bentuk panjang: ada BARIS "false_positive_candidate,<angka>"
       contoh: metric,value
               false_positive_candidate,3

    Return None kalau file tidak ada / nilainya tidak ketemu.
    None artinya "tidak tahu", bukan "nol".
    """
    path = Path(path)
    if not path.exists():
        return None

    try:
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            rows = [row for row in csv.reader(f) if row]
    except Exception:
        return None

    if not rows:
        return None

    header = [str(cell).strip().lower() for cell in rows[0]]

    # Bentuk 1: sebagai kolom
    if "false_positive_candidate" in header:
        idx = header.index("false_positive_candidate")

        # PENTING: dibaca dari BAWAH ke atas supaya yang dipakai adalah
        # evaluasi TERBARU. Versi lama membaca dari atas, jadi angkanya
        # terkunci pada hasil evaluasi pertama walau model sudah diganti.
        for row in reversed(rows[1:]):
            if len(row) > idx:
                value = _to_int(row[idx])
                if value is not None:
                    return value
        return None

    # Bentuk 2: sebagai baris key,value (juga dari yang terbaru)
    for row in reversed(rows):
        for i, cell in enumerate(row):
            if str(cell).strip().lower() == "false_positive_candidate":
                if len(row) > i + 1:
                    return _to_int(row[i + 1])

    return None


def get_validation_status():
    """
    Dipanggil endpoint /api/validation-status.
    Mengembalikan daftar warning yang harus tampil di dashboard.
    """
    fp_candidate = read_false_positive_candidate()

    warnings = []

    if not POSITIVE_TEST_DONE:
        warnings.append(
            "Positive test Hadi belum final. "
            "Hasil 'Verified Hadi' belum bisa dianggap final."
        )

    if fp_candidate is not None and fp_candidate > 0:
        warnings.append(
            f"Negative-only test menemukan {fp_candidate} kandidat false positive. "
            "Hasil 'Verified Hadi' belum bisa dianggap final."
        )

    return {
        "positive_test_done": POSITIVE_TEST_DONE,
        "negative_summary_available": fp_candidate is not None,
        "false_positive_candidate": fp_candidate,
        "warnings": warnings,
        # "crit" (merah) kalau ada kandidat false positive, selain itu "warn" (kuning)
        "level": "crit" if (fp_candidate or 0) > 0 else "warn",
    }