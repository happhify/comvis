# Archive

Script hasil investigasi/tuning satu-kali yang sudah selesai (threshold tuning, long-run false-positive test, audit hasil sortir manual). Tidak dipakai rutin dan tidak di-import oleh kode lain — disimpan sebagai referensi kalau perlu mengulang analisis serupa.

- `sort_dataset.py` — versi lama `label_hadi.py`, sudah digantikan (tidak punya proteksi anti-duplikat/override).
- `validate_threshold.py`, `analyze_threshold.py` — analisis trade-off precision/recall untuk `verified_threshold`.
- `analyze_sort_result.py` — audit hasil sortir manual (melacak crop lewat hash).
- `evaluate_negative_only.py`, `evaluate_positive_test.py`, `review_false_positive_candidates.py` — evaluasi false positive/recall dari sesi long-run test tanpa target di depan kamera.
