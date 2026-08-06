# ComVis — Employee Detection Dashboard

Sistem deteksi kehadiran karyawan dari CCTV: RTSP camera → YOLO person detection → classifier "Hadi vs Unknown" → dashboard web real-time.

## Arsitektur

```
RTSP camera → worker (YOLO detect + classify) → backend (FastAPI) → frontend (React)
                                                        ↑
                                              config/camera.yaml (daftar kamera)
```

- **worker** — baca stream RTSP, deteksi orang (YOLOv8), klasifikasi identitas (Hadi/Unknown) pakai model custom, kirim frame + statistik ke backend. Hanya SATU kamera aktif/streaming pada satu waktu (hemat GPU); kamera lain bisa dipilih ganti dari dashboard.
- **backend** — FastAPI: auth, proxy stream MJPEG, statistik, riwayat deteksi, kontrol kamera aktif. Simpan data di SQLite (`data/`) dan file (`outputs/`).
- **frontend** — dashboard React (live video, statistik, riwayat, manajemen user), di-serve lewat nginx yang juga jadi reverse proxy ke backend (satu origin, satu port 80).

## Menjalankan (Docker)

Butuh Docker Desktop dengan GPU passthrough (NVIDIA) aktif kalau mau pakai GPU untuk worker.

```bash
cp .env.example .env
# edit .env, isi RTSP_URL dengan alamat kamera asli

docker compose up -d --build
```

- Dashboard: http://localhost
- Backend API: http://localhost:8000

## Menambah kamera

1. Tambah variabel RTSP baru di `.env`, misal `RTSP_URL_2=rtsp://...`.
2. Daftarkan di `config/camera.yaml` bagian `cameras.list`:
   ```yaml
   - id: "kamera_2"
     name: "Nama yang tampil di dashboard"
     rtsp_env_key: "RTSP_URL_2"
   ```
3. `docker compose restart worker` (atau tunggu, config di-mount live — tergantung apakah worker sudah baca ulang). Kamera baru langsung muncul di dashboard, tinggal pilih lewat tombol "Switch camera" di sidebar.

`config/camera.yaml` dan `outputs/` di-mount sebagai volume, jadi perubahan konfigurasi/model tidak perlu rebuild image — cukup restart container yang relevan.

## Melatih ulang classifier (Hadi vs Unknown)

Kalau akurasi turun (kondisi cahaya/sudut kamera baru, dll), kumpulkan data dari kamera yang sedang dipakai lalu retrain:

1. Aktifkan `output.save_crops: true` di `config/camera.yaml` — worker otomatis nyimpen crop orang yang terdeteksi ke `outputs/crops/`.
2. Biarkan berjalan beberapa hari sampai crop-nya cukup variatif (jarak/sudut/pencahayaan berbeda-beda).
3. Di mesin lokal (bukan di container — butuh GUI), dari folder `worker/`:
   ```bash
   python scripts/label_hadi.py       # sortir crop -> datasets/known/hadi & datasets/unknown
   python scripts/split_dataset.py    # split train/val 80/20
   python scripts/train_classifier.py # training, hasil ditulis ke models/body_best.pt
   ```
4. `docker compose restart worker` — model baru langsung dipakai (tidak perlu rebuild, `worker/models` di-mount).

Script pendukung lain ada di `worker/scripts/` (audit dataset, balance kelas, review manual, dst — lihat komentar di masing-masing file). Script hasil investigasi/tuning yang sudah selesai dipindah ke `worker/scripts/archive/`.

## Struktur folder

```
backend/    FastAPI app (routers, auth, shared state)
worker/     Video pipeline (detection, classification, training scripts)
frontend/   React dashboard
config/     camera.yaml — daftar kamera & parameter deteksi/klasifikasi
docker/     Konfigurasi nginx (reverse proxy + SPA)
outputs/    Video hasil, crop, log deteksi (runtime, tidak di-commit)
data/       Database SQLite auth (runtime, tidak di-commit)
```

## Environment variables

Lihat `.env.example`. Intinya: satu variabel RTSP URL per kamera, dipetakan lewat `rtsp_env_key` di `config/camera.yaml`.
