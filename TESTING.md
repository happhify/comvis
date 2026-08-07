# Panduan Testing ComVis (untuk pemula)

Panduan ini nuntun kamu nyoba SEMUA fitur yang ada di dashboard ini secara manual, langkah per langkah, dari yang paling dasar (login) sampai yang teknis (automated test, retraining). Nggak perlu pengalaman coding buat sebagian besar bagian ini — cukup ikuti langkahnya dan bandingkan sama "Hasil yang diharapkan".

## 0. Persiapan awal

1. Pastikan **Docker Desktop** sudah nyala.
2. Buka terminal di folder project ini (`comvis-docker`), jalankan:
   ```bash
   docker compose up -d --build
   ```
   Tunggu sampai selesai (bisa beberapa menit pertama kali).
3. Cek semua servis nyala:
   ```bash
   docker compose ps
   ```
   **Hasil yang diharapkan**: ada 3 baris (`backend`, `worker`, `frontend`), semua statusnya `Up`.
4. Buka browser ke **http://localhost**.

Kalau ada langkah di bawah yang hasilnya beda dari yang diharapkan, itu tandanya ada yang perlu dicek/dilaporkan.

---

## 1. Login & Role (Auth)

Ada 3 akun bawaan (dibuat otomatis saat backend pertama kali jalan):

| Username     | Password     | Role          |
|--------------|--------------|---------------|
| `user`       | `user`       | User biasa    |
| `admin`      | `admin`      | Admin         |
| `superadmin` | `superadmin` | Super Admin   |

**Langkah:**
1. Login pakai `user` / `user`.
   **Hasil yang diharapkan**: masuk ke halaman Live Monitor. Sidebar cuma ada menu **"Live Monitor"** dan **"Analytics"** — TIDAK ada menu "Users", dan TIDAK ada tombol "Detection ON/OFF" di header.
2. Klik **"Log out"**, login lagi pakai `admin` / `admin`.
   **Hasil yang diharapkan**: sekarang ada tombol **"Detection ON/OFF"** di header Live Monitor. Menu "Users" masih belum ada.
3. Logout, login pakai `superadmin` / `superadmin`.
   **Hasil yang diharapkan**: sidebar sekarang ada menu **"Users"** juga.
4. Coba login pakai password salah.
   **Hasil yang diharapkan**: muncul pesan error, tidak masuk.

---

## 2. Live Monitor (video real-time + deteksi)

1. Login (role apapun), pastikan ada di halaman **Live Monitor**.
2. **Hasil yang diharapkan** salah satu dari ini:
   - Video muncul dan bergerak (kamera lagi konek), ATAU
   - Tulisan "Backend online, waiting for frames from main.py..." (worker belum kirim frame — cek `docker compose logs worker`).
3. Kalau ada orang di depan kamera, muncul **kotak (bounding box)** di sekitar orangnya:
   - **Hijau** = dikenali sebagai "Hadi", label-nya `Hadi #<id> <confidence>` misal `Hadi #3 0.98`.
   - **Merah** = "Unknown" (bukan Hadi / belum yakin), label `Unknown #<id> <confidence>`.
4. Cek panel **Detection Stats**: angka "Active employees" / "Active unknown" / "People in frame" berubah sesuai orang yang lewat kamera.
5. Cek panel **Recent Activity**: orang yang lagi di frame masuk bagian **ACTIVE**, yang sudah keluar frame pindah ke **PAST**.

---

## 3. Ganti kamera

1. Di sidebar bagian "Camera", lihat kamera yang lagi aktif sekarang.
2. Klik **"Switch camera (N)"**.
3. Pilih kamera lain dari daftar yang muncul.
4. **Hasil yang diharapkan**: video berganti dalam ~5–10 detik, status kamera sempat "WAITING" lalu balik jadi "LIVE" begitu berhasil konek ke kamera baru.

Kalau mau nambah kamera baru buat dites, lihat bagian "Menambah kamera" di `README.md`.

---

## 4. Kontrol deteksi ON/OFF (khusus admin & super_admin)

1. Login sebagai `admin` (atau `superadmin`).
2. Klik tombol **"Detection ON"** di header Live Monitor.
3. **Hasil yang diharapkan**: tombol berubah jadi **"Detection OFF"**, video tetap jalan tapi kotak deteksi (bounding box) hilang — YOLO & classifier dilewati sementara.
4. Klik lagi buat nyalain deteksi kembali.
5. **Test batasan akses**: login sebagai `user` biasa — tombol ini seharusnya TIDAK muncul sama sekali di UI-nya (fitur khusus admin ke atas).

---

## 5. Analytics

1. Klik menu **"Analytics"** di sidebar.
2. Cek 4 kartu ringkasan di atas: *People (last 7 days)*, *Average per day*, *Busiest day*, *Busiest hour today* — harus ada angkanya (bukan "-") kalau sudah ada data deteksi.
3. Cek grafik **"People per Hour"** (batang per jam) dan panel **"Daily Stats"** (7–14 hari terakhir).
4. Scroll ke tabel **"Attendance Today"**:
   - Baris **Hadi** → status "PRESENT"/"ABSENT" dihitung dari kamera SUNGGUHAN.
   - Baris **Karyawan 2/3/4** → ada tag **"DEMO DATA"** di sebelah namanya — ini data contoh, BUKAN data asli (classifier belum bisa mengenali mereka).
   - **Hasil yang diharapkan**: kalau Hadi baru saja lewat kamera dan ke-*verified*, "Arrived"/"Last Seen" dia harus nunjukin jam sekarang (WIB), bukan jam yang aneh/beda 7 jam.
5. Scroll ke **"Detection History"**:
   - Ganti filter tanggal & status (All / Employee / Unknown), tabel harus ikut berubah.
   - Klik **"Export CSV"** — harus ke-download file CSV berisi data sesuai filter yang aktif.

---

## 6. Manajemen User (khusus super_admin)

1. Login sebagai `superadmin`, buka menu **"Users"**.
2. **Tambah user baru** — isi username/password/role, submit.
   **Hasil yang diharapkan**: user baru langsung muncul di tabel tanpa reload halaman.
3. Buka tab/browser lain (atau incognito), coba login pakai user baru itu.
   **Hasil yang diharapkan**: berhasil login, menu yang muncul sesuai role yang dipilih tadi.
4. Balik ke tab superadmin, coba **ganti role** user itu, lalu **reset password**-nya.
5. **Hapus** user itu.
   **Hasil yang diharapkan**: hilang dari tabel, dan sesi login user itu (kalau masih ada yang login) langsung tidak valid lagi.
6. **Test batasan akses**: login sebagai `admin` biasa (bukan superadmin) — menu "Users" seharusnya tidak muncul di sidebar-nya.

---

## 7. Preview kamera tanpa web (opsional, agak teknis)

Buat lihat preview kamera langsung tanpa buka browser (jendela `cv2.imshow`):

```bash
docker compose stop worker
cd worker
python main.py
```

**Hasil yang diharapkan**: muncul jendela preview video dengan kotak deteksi, sama persis kayak yang di dashboard, cuma di luar browser. Tekan `q` buat keluar. Jangan lupa nyalain lagi worker Docker-nya setelah selesai: `docker compose start worker`.

---

## 8. Automated test suite (buat developer/technical report)

Ini test otomatis yang ngecek logic inti (bukan lewat browser) — cocok buat bukti teknis di laporan.

**Backend:**
```bash
cd backend
python -m venv .venv          # sekali saja
./.venv/Scripts/pip install -r requirements.txt pytest
./.venv/Scripts/python -m pytest -v
```
**Hasil yang diharapkan**: semua test **PASSED** (saat ini 56 test — status/login/kehadiran/riwayat dsb).

**Worker:**
```bash
cd worker
pip install pytest   # ke venv yang sudah ada torch/CUDA-nya
python -m pytest -v
```
**Hasil yang diharapkan**: semua test **PASSED** (saat ini 45 test — logic klasifikasi, tracking, dll).

Test-test ini sengaja TIDAK butuh kamera/GPU/browser — jalan murni dari logic Python, jadi bisa dites di komputer manapun.

---

## 9. Retraining classifier (opsional, expert — butuh waktu berhari-hari)

Ini bukan sesuatu yang bisa dites sekali duduk, tapi alurnya:
1. Aktifkan `output.save_crops: true` di `config/camera.yaml`.
2. Biarkan jalan beberapa hari (ngumpulin crop orang dari kamera asli).
3. `python scripts/label_hadi.py` (native, butuh GUI) → sortir manual crop Hadi vs bukan.
4. `python scripts/split_dataset.py` → `python scripts/train_classifier.py`.
5. `docker compose restart worker` → model baru langsung dipakai.

Detail lengkap ada di `README.md` bagian "Melatih ulang classifier".

---

## Ringkasan cepat (checklist)

- [ ] Semua container `Up` (`docker compose ps`)
- [ ] Login 3 role, menu yang muncul beda-beda sesuai role
- [ ] Video Live Monitor muncul, bounding box + label benar
- [ ] Switch camera berhasil, status LIVE
- [ ] Detection ON/OFF (admin) berfungsi, tidak muncul buat user biasa
- [ ] Analytics: grafik, Attendance Today (Hadi asli vs Karyawan dummy), Detection History + export
- [ ] Users: tambah/ubah role/reset password/hapus (superadmin)
- [ ] `pytest` backend & worker semua PASSED
