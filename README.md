# ComVis — Employee Detection Dashboard

Sistem deteksi kehadiran karyawan dari CCTV: RTSP camera → YOLO person detection → classifier identitas ("Hadi" vs "Unknown") → dashboard web real-time, lengkap dengan statistik, riwayat deteksi, dan status absensi harian.

Status project: **prototype internal** (PUSDATIN), masih tahap penyempurnaan akurasi model dan perluasan fitur.

## Fitur utama

- **Live Monitor** — video real-time dengan bounding box (nama, ID tracking, confidence), status kamera, statistik langsung (FPS, jumlah orang di frame, dsb).
- **Multi-kamera dengan switch manual** — ~20 kamera bisa didaftarkan, tapi cuma **satu yang aktif/streaming** dalam satu waktu (hemat GPU tunggal). Ganti kamera lewat tombol "Switch camera" di sidebar, tanpa perlu restart apa pun.
- **Analytics** — grafik orang per jam/hari, ringkasan mingguan, riwayat deteksi (dengan filter tanggal/status + export CSV).
- **Absensi harian** — status "Present since HH:MM" / "Not yet arrived today" per pegawai, dihitung dari sesi "verified" pertama & terakhir hari itu. Lihat bagian [Fitur Absensi](#fitur-absensi) untuk detail & keterbatasannya.
- **Auth & role** — login dengan session token, 3 role (`user`, `admin`, `super_admin`), manajemen user dari dashboard (khusus `super_admin`).
- **Retraining pipeline** — kumpulkan crop dari kamera asli, label manual, retrain classifier — lihat [Melatih ulang classifier](#melatih-ulang-classifier-hadi-vs-unknown).

## Arsitektur

```
RTSP camera → worker (YOLO detect + classify) → backend (FastAPI) → frontend (React)
                                                        ↑
                                    config/camera.yaml, config/employees.yaml
```

- **worker** — baca stream RTSP, deteksi orang (YOLOv8), klasifikasi identitas (Hadi/Unknown) pakai model custom, kirim frame + statistik ke backend. Hanya SATU kamera aktif/streaming pada satu waktu; kamera lain bisa dipilih ganti dari dashboard. Bisa juga dijalankan native (di luar Docker) untuk preview cepat tanpa web — lihat [Preview kamera tanpa web](#preview-kamera-tanpa-web-native).
- **backend** — FastAPI: auth, proxy stream MJPEG, statistik, riwayat deteksi, absensi, kontrol kamera aktif. Simpan data di SQLite (`data/`) dan file (`outputs/`).
- **frontend** — dashboard React (live video, statistik, riwayat, absensi, manajemen user), di-serve lewat nginx yang juga jadi reverse proxy ke backend (satu origin, satu port 80).

Detail tiap servis (routing, module internal) ada di komentar masing-masing file, bukan diulang di sini supaya dokumentasi tidak basi.

## Menjalankan (Docker)

Butuh Docker Desktop dengan GPU passthrough (NVIDIA) aktif kalau mau pakai GPU untuk worker.

```bash
cp .env.example .env
# edit .env, isi RTSP_URL dengan alamat kamera asli

docker compose up -d --build
```

- Dashboard: http://localhost
- Backend API: http://localhost:8000

Saat pertama kali jalan, backend otomatis membuat 3 akun default (`superadmin`, `admin`, `user` — password sama dengan username). **Ganti password-nya** dari folder `worker/`: `python scripts/manage_users.py reset-password --username <nama>`, sebelum dipakai orang lain.

## Menambah kamera

1. Tambah variabel RTSP baru di `.env`, misal `RTSP_URL_2=rtsp://...`.
2. Daftarkan di `config/camera.yaml` bagian `cameras.list`:
   ```yaml
   - id: "kamera_2"
     name: "Nama yang tampil di dashboard"
     rtsp_env_key: "RTSP_URL_2"
   ```
3. `docker compose restart worker`. Kamera baru langsung muncul di dashboard, tinggal pilih lewat tombol "Switch camera" di sidebar.

`config/camera.yaml` dan `outputs/` di-mount sebagai volume, jadi perubahan konfigurasi/model tidak perlu rebuild image — cukup restart container yang relevan.

## Fitur Absensi

Kartu/tabel "Attendance Today" di halaman Analytics, dihitung dari `outputs/logs/detection_log.csv` (bukan sistem tracking terpisah).

**Cara kerja per pegawai** — diatur di `config/employees.yaml`:

```yaml
employees:
  - id: "hadi"
    name: "Hadi"
    source: "real"     # status dihitung dari detection_log.csv sungguhan

  - id: "karyawan_2"
    name: "Karyawan 2"
    source: "dummy"    # placeholder - classifier belum bisa kenali orang ini
    dummy_status: "present"
    dummy_arrived_at: "08:05"
    dummy_last_seen: "12:40"
```

- `source: "real"` — statusnya dihitung dari sesi "verified" pertama/terakhir hari ini. **Baru "Hadi" yang punya ini**, karena classifier saat ini cuma bisa membedakan Hadi vs Unknown (belum multi-kelas).
- `source: "dummy"` — nilai tetap (`dummy_status`/`dummy_arrived_at`/`dummy_last_seen`), ditandai tag **"DEMO DATA"** di dashboard supaya tidak disalahartikan sebagai data asli. Placeholder sampai classifier di-retrain jadi multi-kelas dan bisa mengenali pegawai lain.
- Tambah/edit pegawai tinggal edit file YAML ini, tidak perlu ubah kode (config di-mount live, tapi butuh restart backend untuk baca ulang kalau di-cache — cek dengan reload dashboard).

**Keterbatasan penting (jujur, bukan disembunyikan):**
- Sistem cuma mengawasi **1 dari ~20 kamera** sekaligus. "Not yet arrived" berarti belum terdeteksi di kamera yang *sedang* aktif — BUKAN bukti orangnya tidak ada di gedung.
- Akurasi classifier masih dalam penyempurnaan (lihat bagian retraining). Selama itu, kemungkinan ada "Not yet arrived" palsu karena confidence belum cukup tinggi untuk status "verified".
- `detection_log.csv` tumbuh terus tanpa rotasi (satu baris per orang per frame) — sudah dioptimalkan supaya query absensi tidak ikut melambat seiring file membesar (baca dari ekor file, bukan scan penuh), tapi tetap sesuatu yang perlu diawasi kalau file makin besar.

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

## Preview kamera tanpa web (native)

Buat lihat preview kamera langsung (jendela `cv2.imshow`) tanpa jalanin backend/frontend/nginx — lebih ringan buat GPU 4GB:

```bash
docker compose stop worker   # hindari 2 proses rebutan GPU/koneksi RTSP yang sama
cd worker
python main.py               # HEADLESS tidak di-set -> otomatis buka jendela preview, tekan 'q' buat keluar
```

`worker/config` dan `worker/outputs` di-setup sebagai directory junction (`mklink /J`) yang menunjuk ke `config/` dan `outputs/` di root project, supaya path relatif di `main.py` (`config/camera.yaml`, `outputs/...`) tetap resolve dengan benar walau dijalankan dari luar Docker — layout-nya sama persis kayak di dalam container.

Setelah selesai, nyalakan lagi worker Docker-nya: `docker compose start worker`.

## Testing

Backend dan worker punya test suite pytest terpisah (masing-masing servis punya dependency sendiri).

**Backend** (butuh Python biasa, tanpa GPU):
```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt pytest
./.venv/Scripts/python -m pytest
```

**Worker** (butuh torch+CUDA - kalau sudah ada venv native buat preview/retraining seperti di atas, pakai itu saja):
```bash
cd worker
pip install pytest   # sekali saja, ke venv yang sama dipakai buat preview native
python -m pytest
```

Test difokuskan ke logic yang murni/deterministik dan langsung berkaitan dengan ketepatan absensi & deteksi: status klasifikasi (verified/unknown), IoU tracking & TTL cache, agregasi sesi riwayat dari CSV, status absensi harian, auth (hash password, session, role). Tidak mencakup integrasi RTSP/GPU/browser — itu tetap perlu dicek manual.

## Struktur folder

```
backend/    FastAPI app (routers, auth, shared state, agregasi riwayat/absensi)
worker/     Video pipeline (detection, classification, training scripts)
frontend/   React dashboard
config/     camera.yaml (daftar kamera), employees.yaml (daftar pegawai buat absensi)
docker/     Konfigurasi nginx (reverse proxy + SPA)
outputs/    Video hasil, crop, log deteksi (runtime, tidak di-commit)
data/       Database SQLite auth (runtime, tidak di-commit)
```

## Environment variables

Lihat `.env.example`. Intinya: satu variabel RTSP URL per kamera, dipetakan lewat `rtsp_env_key` di `config/camera.yaml`.
