"""
scripts/longrun_monitor.py  (Tahap F - Long Run Test)

Memantau sistem SELAMA berjalan (bukan cuma ringkasan di akhir seperti
RuntimeMonitor). Tujuannya melihat TREN: apakah RAM merangkak naik,
FPS turun setelah sekian menit, log membengkak seberapa cepat.

Cara pakai (jalankan di terminal ke-3, saat backend + main.py sudah jalan):

    python scripts/longrun_monitor.py --minutes 45

Script ini hanya MEMBACA (login lalu polling endpoint dashboard).
Tidak mengubah apa pun di sistem deteksi.

Hasil:
- outputs/logs/longrun_monitor.csv   (time-series tiap sampel)
- ringkasan + peringatan dicetak di akhir
"""

from pathlib import Path
from datetime import datetime
import argparse
import csv
import time

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT_DIR / "outputs" / "logs" / "detection_log.csv"
MONITOR_CSV = ROOT_DIR / "outputs" / "logs" / "longrun_monitor.csv"

FIELDS = [
    "timestamp", "elapsed_sec", "camera_status", "fps", "people_in_frame",
    "total_detections", "cpu_percent", "ram_percent", "ram_used_gb",
    "gpu_percent", "vram_used_gb", "gpu_temp", "log_size_mb",
]


def login(base_url, username, password):
    res = requests.post(
        f"{base_url}/api/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if res.status_code == 401:
        raise RuntimeError("Username/password salah.")
    res.raise_for_status()
    return res.json()["token"]


def get_json(base_url, path, token):
    res = requests.get(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def log_size_mb():
    if not LOG_PATH.exists():
        return 0.0
    return round(LOG_PATH.stat().st_size / (1024 * 1024), 3)


def num(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def take_sample(base_url, token, started_at):
    stats = get_json(base_url, "/api/stats", token)
    server = get_json(base_url, "/api/server-stats", token)

    gpu = server.get("gpu") or {}
    ram = server.get("ram") or {}
    cpu = server.get("cpu") or {}

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - started_at, 1),
        "camera_status": stats.get("camera_status", "-"),
        "fps": round(num(stats.get("fps")), 2),
        "people_in_frame": int(num(stats.get("people_in_frame"))),
        "total_detections": int(num(stats.get("total_detections"))),
        "cpu_percent": round(num(cpu.get("percent")), 2),
        "ram_percent": round(num(ram.get("percent")), 2),
        "ram_used_gb": round(num(ram.get("used_gb")), 2),
        "gpu_percent": round(num(gpu.get("gpu_percent")), 2),
        "vram_used_gb": round(num(gpu.get("vram_used_gb")), 2),
        "gpu_temp": round(num(gpu.get("temperature")), 1),
        "log_size_mb": log_size_mb(),
    }


def avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def print_summary(rows):
    if not rows:
        print("[WARNING] Tidak ada sampel terkumpul.")
        return

    n = len(rows)
    duration_min = rows[-1]["elapsed_sec"] / 60.0

    fps_all = [r["fps"] for r in rows]
    ram_all = [r["ram_percent"] for r in rows]
    cpu_all = [r["cpu_percent"] for r in rows]
    vram_all = [r["vram_used_gb"] for r in rows]
    temp_all = [r["gpu_temp"] for r in rows]

    # Bandingkan seperlima awal vs seperlima akhir untuk melihat tren
    k = max(1, n // 5)
    fps_early, fps_late = avg(fps_all[:k]), avg(fps_all[-k:])
    fps_change = ((fps_late - fps_early) / fps_early * 100) if fps_early > 0 else 0.0
    fps_drop = -fps_change  # positif = FPS TURUN

    ram_start, ram_end, ram_peak = ram_all[0], ram_all[-1], max(ram_all)
    log_start, log_end = rows[0]["log_size_mb"], rows[-1]["log_size_mb"]
    log_growth = log_end - log_start
    log_per_hour = (log_growth / duration_min * 60) if duration_min > 0 else 0.0

    status_counts = {}
    for r in rows:
        status_counts[r["camera_status"]] = status_counts.get(r["camera_status"], 0) + 1

    print()
    print("=" * 70)
    print("[HASIL LONG RUN TEST]")
    print("=" * 70)
    print(f"Durasi                 : {duration_min:.1f} menit ({n} sampel)")
    print(f"Status kamera          : {status_counts}")
    print("-" * 70)
    print(f"FPS rata-rata          : {avg(fps_all):.2f}  (min {min(fps_all):.2f} / max {max(fps_all):.2f})")
    print(f"FPS awal vs akhir      : {fps_early:.2f}  ->  {fps_late:.2f}   ({fps_change:+.1f}%)")
    print(f"CPU rata-rata / puncak : {avg(cpu_all):.1f}% / {max(cpu_all):.1f}%")
    print(f"RAM awal/puncak/akhir  : {ram_start:.1f}% / {ram_peak:.1f}% / {ram_end:.1f}%")
    print(f"VRAM puncak            : {max(vram_all):.2f} GB")
    if max(temp_all) > 0:
        print(f"Suhu GPU puncak        : {max(temp_all):.0f} C")
    print(f"Log detection          : {log_start:.2f} MB -> {log_end:.2f} MB "
          f"(+{log_growth:.2f} MB, ~{log_per_hour:.1f} MB/jam)")
    print("-" * 70)

    warnings = []
    if fps_drop > 15:
        warnings.append(f"FPS turun {fps_drop:.0f}% dari awal ke akhir - cek beban/termal.")
    if ram_end - ram_start > 5:
        warnings.append(f"RAM naik {ram_end - ram_start:.1f} poin selama run - curigai kebocoran memori.")
    if ram_peak >= 92:
        warnings.append(f"RAM sempat {ram_peak:.1f}% - mendekati penuh, risiko lag/crash.")
    if log_per_hour > 100:
        warnings.append(f"Log tumbuh ~{log_per_hour:.0f} MB/jam - pertimbangkan rotasi detection_log.csv.")
    if any(s != "LIVE" for s in status_counts):
        warnings.append(f"Status kamera tidak selalu LIVE: {status_counts}")

    if warnings:
        print("[PERHATIAN]")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("[OK] Tidak ada gejala mencurigakan: FPS stabil, RAM tidak merangkak, kamera LIVE terus.")

    print("=" * 70)
    print(f"[INFO] Time-series -> {MONITOR_CSV}")


def main():
    parser = argparse.ArgumentParser(description="Long run monitor (Tahap F).")
    parser.add_argument("--minutes", type=float, default=45, help="Lama pemantauan (menit). Default 45")
    parser.add_argument("--interval", type=float, default=15, help="Jarak antar sampel (detik). Default 15")
    parser.add_argument("--username", default="admin", help="Akun untuk login. Default admin")
    parser.add_argument("--password", default="admin", help="Password akun tersebut")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Alamat backend")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print("=" * 70)
    print("[INFO] Long Run Monitor")
    print("=" * 70)
    print(f"Target   : {base_url}")
    print(f"Durasi   : {args.minutes} menit, sampel tiap {args.interval} detik")
    print("Tekan Ctrl+C untuk berhenti lebih awal (ringkasan tetap dicetak).")
    print("=" * 70)

    try:
        token = login(base_url, args.username, args.password)
    except requests.exceptions.ConnectionError:
        print("[ERROR] Tidak bisa menghubungi backend. Pastikan uvicorn jalan di port 8000.")
        return
    except Exception as e:
        print(f"[ERROR] Gagal login: {e}")
        return

    MONITOR_CSV.parent.mkdir(parents=True, exist_ok=True)
    file_exists = MONITOR_CSV.exists() and MONITOR_CSV.stat().st_size > 0

    started_at = time.time()
    stop_at = started_at + args.minutes * 60
    rows = []

    with open(MONITOR_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()

        try:
            while time.time() < stop_at:
                try:
                    row = take_sample(base_url, token, started_at)
                except Exception as e:
                    print(f"  [WARN] gagal ambil sampel: {e}")
                    time.sleep(args.interval)
                    continue

                rows.append(row)
                writer.writerow(row)
                f.flush()

                print(f"  [{row['elapsed_sec']:>7.1f}s] {row['camera_status']:<8} "
                      f"FPS {row['fps']:>5.1f} | CPU {row['cpu_percent']:>5.1f}% | "
                      f"RAM {row['ram_percent']:>5.1f}% | VRAM {row['vram_used_gb']:>4.2f}GB | "
                      f"log {row['log_size_mb']:>7.2f}MB")

                remaining = stop_at - time.time()
                if remaining <= 0:
                    break
                time.sleep(min(args.interval, remaining))

        except KeyboardInterrupt:
            print("\n[INFO] Dihentikan manual (Ctrl+C).")

    print_summary(rows)


if __name__ == "__main__":
    main()