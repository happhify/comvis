# Rencana: Multi-kamera CONCURRENT (bukan switch)

Status: **rencana, belum dikerjakan.** Ditulis supaya bisa langsung eksekusi
kapan saja tanpa perlu re-analisis dari nol.

## Tujuan

Sekarang: cuma 1 kamera aktif/streaming sekaligus, gonta-ganti pakai
"Switch camera" (lihat README bagian Arsitektur).

Target baru: **2+ kamera jalan BERSAMAAN** (misal kamera Lobby + kamera
Ruangan sebelah Lobby), supaya begitu orang pindah dari satu area ke area
lain, kamera di area itu langsung ikut mengenali — tidak perlu switch
manual, tidak ada gap waktu.

**Bagian yang TERNYATA sudah otomatis beres** (dicek langsung ke kode,
bukan asumsi): absensi (`backend/app/attendance_reader.py`) dan riwayat
(`history_reader.py`) sudah baca SEMUA baris `detection_log.csv` apa
adanya, tidak difilter ke satu kamera tertentu. Setiap baris log sudah
tercatat dengan nama kameranya masing-masing. Jadi begitu 2 worker
nulis ke log yang sama secara bersamaan, agregasi absensi/riwayat
otomatis benar TANPA perubahan kode di bagian itu.

"Continuity of identity" antar kamera juga tidak butuh re-identification
engine yang rumit: karena sistem ini cuma mengenali identitas SPESIFIK
yang sudah dilatih (Hadi vs Unknown), bukan re-id orang sembarang, maka
classifier yang SAMA dijalankan independen di tiap kamera sudah cukup -
begitu Hadi lewat kamera manapun, classifier di situ akan bilang "Hadi"
sendiri, tanpa perlu "mengirim" identitas dari kamera lain.

## Yang harus diubah (3 bagian)

### 1. Worker: dari "1 proses + switch" jadi "1 proses per kamera"

File: `docker-compose.yml`, `worker/main.py`, `config/camera.yaml`

- Duplikasi service `worker` di `docker-compose.yml` jadi N service
  (misal `worker_lobby`, `worker_ruang`), masing-masing:
  - Environment var baru, misal `PINNED_CAMERA_ID=kamera_1` /
    `PINNED_CAMERA_ID=kamera_2` (baca di `main.py`, override
    `cameras.default` dari config kalau env ini di-set).
  - Kalau `PINNED_CAMERA_ID` di-set: **abaikan** perintah switch kamera
    dari dashboard (`control.get("camera_id")` di `main.py` baris ~631) -
    instance ini permanen di kamera itu. Worker yang TIDAK di-pin
    (kalau masih mau ada slot "switchable" buat sisa ~18 kamera lain)
    tetap pakai logic switch yang sudah ada, tidak usah diubah.
  - Video output path (`output.video_output_path`) dan nama run harus
    unik per kamera supaya tidak saling timpa - kemungkinan perlu
    override lewat env juga, bukan cuma dari `camera.yaml` (karena
    config di-mount shared read-only ke semua worker).
  - `deploy.resources.reservations.devices` (GPU) tetap `count: 1` di
    tiap service - NVIDIA runtime boleh dipakai bersamaan oleh beberapa
    container di 1 GPU fisik, tidak perlu GPU terpisah per kamera.
- `.env`: perlu isi `RTSP_URL_2` sungguhan (sekarang di-comment di
  `.env` - kamera 2 memang belum pernah diaktifkan).

**Estimasi dampak GPU:** sekarang 1 kamera pakai ~377MB VRAM dari 4096MB
(RTX 3050 Laptop) di ~10-30fps tergantung beban. Nambah 1 kamera lagi:
VRAM masih longgar (~750MB-1GB total, aman), tapi **compute (bukan
memori) yang jadi rebutan** - FPS tiap kamera kemungkinan turun karena
GPU yang sama dipakai gantian antar proses. Perlu diukur langsung
begitu jalan (cek `fps` di `/api/stats` tiap kamera), bukan cuma
diasumsikan cukup.

### 2. Backend: `shared_state` dari "1 slot global" jadi "per kamera"

File: `backend/app/shared_state.py`, `routers/stats.py`, `routers/stream.py`,
`routers/control.py`, `video_stream.py`

Sekarang `SharedState` cuma nyimpen SATU `_latest_frame_jpeg` dan SATU
`_stats` untuk seluruh sistem (dicek langsung di kode - tidak ada konsep
`camera_id` sama sekali di dalamnya). Untuk multi-kamera concurrent, ini
harus jadi dict keyed by `camera_id`:

- `_cameras: dict[str, {frame, frame_last_update, stats, ...}]`
- `update_frame(camera_id, frame_jpeg)`, `get_latest_frame(camera_id)`
- `update_stats(camera_id, stats)`, `get_stats(camera_id=None)` - kalau
  `camera_id` tidak dikasih, kembalikan dict semua kamera yang lagi
  aktif (buat kebutuhan grid view di frontend, biar 1x request dapat
  semua).
- Endpoint yang kena dampak:
  - `POST /api/frame` dan `POST /api/stats-update` - worker HARUS
    kirim `camera_id` di payload/query, supaya backend tahu ini punya
    kamera yang mana. **Ini juga berarti `worker/src/dashboard_client.py`
    perlu diubah** buat nyertain `camera_id` di tiap request.
  - `GET /api/stats` - tambah query param opsional `?camera_id=`, kalau
    kosong balikin semua.
  - `GET /api/stream` - tambah query param wajib `?camera_id=` (MJPEG
    generator perlu tahu ambil frame dari kamera mana).
  - `GET/POST /api/control` - `camera_id` di sini SEKARANG artinya
    "kamera aktif satu-satunya", nanti maknanya berubah jadi murni
    preferensi tampilan viewer (opsional, bisa dihapus kalau grid view
    yang dipilih menampilkan semua kamera sekaligus tanpa perlu pilih).
    `detection_enabled` tetap masuk akal sebagai saklar GLOBAL (matiin
    deteksi di semua kamera sekaligus) - tidak perlu diubah jadi
    per-kamera kecuali memang mau kontrol lebih granular.

### 3. Frontend: Live Monitor jadi grid

File: `frontend/src/` (komponen Live Monitor - cek nama pastinya pas
mulai kerjain, belum ditelusuri detail di sesi ini)

- Ganti tampilan video tunggal jadi grid (misal 2 kolom), tiap sel:
  - `<img>` MJPEG dari `/api/stream?camera_id=X` sendiri-sendiri.
  - Panel statistik kecil per kamera (people in frame, active persons)
    dari `/api/stats?camera_id=X` (atau dari respons gabungan
    `/api/stats` tanpa param, di-filter di frontend).
- Sidebar "Camera" & tombol "Switch camera" kemungkinan tidak relevan
  lagi buat kamera yang sudah di-pin concurrent (karena dua-duanya
  SELALU tampil) - cuma relevan kalau masih ada slot kamera
  "switchable" tambahan di luar yang concurrent.

## Urutan pengerjaan yang disarankan

1. Backend dulu (`shared_state.py` + router-router) - paling aman
   dites sendiri dulu pakai `curl`/pytest sebelum worker/frontend ikut
   berubah.
2. Worker (`main.py` + `dashboard_client.py` + `docker-compose.yml`) -
   jalankan 2 service, verifikasi lewat `docker compose logs` &
   `curl /api/stats?camera_id=...` kedua-duanya update independen.
3. Frontend grid - paling terakhir, karena bergantung ke 2 hal di atas
   sudah jadi.
4. Test end-to-end: taruh 1 orang di kamera lobby, pastikan attendance
   ke-update; pindah ke kamera ruang sebelah, pastikan ke-update lagi
   tanpa delay switch manual.

## Checklist validasi sebelum dianggap selesai

- [ ] `docker compose ps` - kedua worker service `Up`, tidak ada restart loop
- [ ] `/api/stats?camera_id=kamera_1` dan `?camera_id=kamera_2` beda isi,
      dua-duanya `camera_status: LIVE` bersamaan
- [ ] FPS kedua kamera diukur, dicek masih cukup buat real-time
      (bukan cuma "jalan", tapi "jalan dengan lancar")
- [ ] `detection_log.csv` ada baris dari 2 nama kamera berbeda dalam
      rentang waktu yang tumpang tindih
- [ ] Attendance Today tetap akurat dengan data dari 2 kamera sekaligus
- [ ] Live Monitor grid nampilin 2 video + statistik masing-masing,
      tidak ada video yang nge-freeze/salah tertukar kamera
- [ ] Backend & worker pytest tetap semua PASSED
