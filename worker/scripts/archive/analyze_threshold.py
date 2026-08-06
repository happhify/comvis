"""
scripts/analyze_threshold.py

Menjawab satu pertanyaan: KALAU verified_threshold dinaikkan,
apakah false positive berkurang tanpa mengorbankan terlalu banyak
deteksi yang benar?

Datanya diambil dari crop 'verified_hadi' di outputs/crops:
- confidence dibaca dari NAMA file (..._conf_0.98.jpg)
- benar/salahnya diambil dari hasil sortirmu (dicocokkan lewat hash):
    masuk datasets/known/hadi  -> BENAR Hadi  (true positive)
    masuk datasets/unknown     -> BUKAN Hadi  (false positive)

READ-ONLY.
"""

import csv
import hashlib
import os
import re

CROPS_DIR = "outputs/crops"
HADI_DIR = "datasets/known/hadi"
UNKNOWN_DIR = "datasets/unknown"
LOG_PATH = "outputs/logs/detection_log.csv"
VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp")

CROP_PATTERN = re.compile(
    r"^(?P<camera>.+?)_(?P<date>\d{8})_(?P<time>\d{6})"
    r"_frame_(?P<frame>\d+)_person_(?P<person>\d+)"
    r"_(?P<status>[a-z]+)_(?P<label>.+?)_conf_(?P<conf>[\d.]+)$"
)


def list_images(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if os.path.splitext(f)[1].lower() in VALID_EXT)


def file_hash(path):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return None
    return h.hexdigest()


def hash_set(folder):
    return {file_hash(os.path.join(folder, n)) for n in list_images(folder)}



def load_log_confidence():
    """
    (timestamp, frame_id, detection_id) -> recognition_confidence presisi penuh.
    Nama file crop hanya menyimpan 2 desimal, jadi log jauh lebih akurat.
    """
    if not os.path.exists(LOG_PATH):
        return {}

    mapping = {}
    try:
        with open(LOG_PATH, "r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    key = (row["timestamp"].strip(),
                           int(float(row["frame_id"])),
                           int(float(row["detection_id"])))
                    mapping[key] = float(row["recognition_confidence"])
                except (KeyError, ValueError, TypeError):
                    continue
    except Exception as e:
        print(f"[WARNING] Gagal membaca log: {e}")
        return {}

    return mapping


def crop_key(m):
    """Kunci pencocokan dari nama crop -> sama bentuknya dengan log."""
    d, t = m.group("date"), m.group("time")
    stamp = f"{d[0:4]}-{d[4:6]}-{d[6:8]} {t[0:2]}:{t[2:4]}:{t[4:6]}"
    return (stamp, int(m.group("frame")), int(m.group("person")))

def main():
    print()
    print("=" * 72)
    print("ANALISIS AMBANG (verified_threshold)")
    print("=" * 72)

    hadi_h = hash_set(HADI_DIR)
    unknown_h = hash_set(UNKNOWN_DIR)
    log_conf = load_log_confidence()

    if log_conf:
        print(f"[INFO] Log terbaca: {len(log_conf)} baris (confidence presisi penuh)")
    else:
        print("[WARNING] detection_log.csv tidak terbaca -> pakai 2 desimal dari nama file")

    benar = []   # confidence crop yang BENAR Hadi
    salah = []   # confidence crop yang BUKAN Hadi
    dari_log = 0

    for name in list_images(CROPS_DIR):
        stem = os.path.splitext(name)[0]
        m = CROP_PATTERN.match(stem)
        if not m or m.group("status") != "verified" or m.group("label") != "hadi":
            continue
        try:
            conf = float(m.group("conf"))
        except ValueError:
            continue

        tepat = log_conf.get(crop_key(m))
        if tepat is not None:
            conf = tepat
            dari_log += 1

        h = file_hash(os.path.join(CROPS_DIR, name))
        if h in hadi_h:
            benar.append(conf)
        elif h in unknown_h:
            salah.append(conf)

    if not benar and not salah:
        print("[ERROR] Tidak ada crop 'verified_hadi' yang bisa dicocokkan.")
        print("        Pastikan sudah menjalankan sortir dan dataset masih ada.")
        return

    total_dinilai = len(benar) + len(salah)
    print(f"Crop 'Verified Hadi' yang sudah kamu nilai: {total_dinilai}")
    if log_conf:
        print(f"  Confidence presisi penuh dari log : {dari_log}")
        print(f"  Terpaksa pakai 2 desimal nama file: {total_dinilai - dari_log}")
    print(f"  BENAR Hadi : {len(benar)}")
    print(f"  BUKAN Hadi : {len(salah)}")

    def ringkas(nama, data):
        if not data:
            print(f"  {nama}: (kosong)")
            return
        data = sorted(data)
        n = len(data)
        print(f"  {nama:<12} min {data[0]:.4f} | median {data[n // 2]:.4f} | "
              f"max {data[-1]:.4f} | rata {sum(data) / n:.4f}")

    print("\nSebaran confidence:")
    ringkas("BENAR Hadi", benar)
    ringkas("BUKAN Hadi", salah)

    # ---------- Sweep ambang ----------
    print()
    print("-" * 72)
    print("Kalau verified_threshold dinaikkan:")
    print("-" * 72)
    print(f"{'AMBANG':>8}{'BENAR lolos':>14}{'SALAH lolos':>14}{'PRECISION':>12}{'sisa BENAR':>13}")
    print("-" * 72)

    total_benar = len(benar)
    hasil = []

    # Titik potong yang benar-benar ada di data (bukan angka bulat karangan)
    kandidat = sorted(set(round(c, 4) for c in benar + salah))
    for ambang in kandidat:
        tp = sum(1 for c in benar if c >= ambang)
        fp = sum(1 for c in salah if c >= ambang)
        prec = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0.0
        sisa = tp / total_benar * 100 if total_benar else 0.0
        hasil.append((ambang, tp, fp, prec, sisa))

    # tampilkan maksimal 12 baris supaya terbaca
    tampil = hasil if len(hasil) <= 12 else \
        [hasil[i] for i in sorted(set([0] + [round(k * (len(hasil) - 1) / 10) for k in range(11)]))]
    for ambang, tp, fp, prec, sisa in tampil:
        print(f"{ambang:>8.4f}{tp:>14}{fp:>14}{prec:>11.1f}%{sisa:>12.1f}%")

    print("-" * 72)

    # ---------- Kesimpulan ----------
    print()
    print("=" * 72)
    print("KESIMPULAN")
    print("=" * 72)

    awal = hasil[0]

    # Ambang hanya layak kalau deteksi benar yang tersisa masih >= 70%.
    # Precision tinggi tapi kehilangan sebagian besar deteksi benar itu
    # bukan perbaikan - sistemnya jadi hampir tidak pernah mengenali siapa pun.
    layak = [r for r in hasil if r[4] >= 70.0]
    terbaik = max(layak, key=lambda r: r[3]) if layak else awal

    print(f"Sekarang (ambang {awal[0]:.4f}): precision {awal[3]:.1f}%, "
          f"{awal[2]} false positive, {awal[1]} deteksi benar.")
    print()
    print("Catatan: menaikkan ambang SELALU mengurangi false positive,")
    print("tapi juga membuang deteksi yang benar. Yang dinilai di sini")
    print("adalah apakah pertukarannya sepadan (deteksi benar sisa >= 70%).")

    if terbaik[3] - awal[3] < 5:
        print()
        print("Menaikkan ambang TIDAK banyak menolong.")
        print("Sebabnya: crop yang salah pun punya confidence setinggi yang benar,")
        print("jadi tidak ada garis pemisah yang bisa ditarik.")
        print()
        print("Artinya masalahnya ada di MODEL, bukan di ambang.")
        print("Solusi yang tepat: latih ulang dengan hard negative")
        print("(47 crop salah itu sudah masuk kelas unknown-mu) -> Tahap E.")
    else:
        print()
        print(f"Ambang {terbaik[0]:.4f} memberi precision {terbaik[3]:.1f}% "
              f"({terbaik[2]} false positive, dari {awal[2]}),")
        print(f"dan masih mempertahankan {terbaik[4]:.1f}% deteksi benar "
              f"({terbaik[1]} dari {awal[1]}).")
        print("Pertukaran ini masuk akal - layak dipertimbangkan di Tahap D.")
        print("Tetap perlu retrain juga, karena precision-nya masih jauh dari aman.")

    print("=" * 72)


if __name__ == "__main__":
    main()