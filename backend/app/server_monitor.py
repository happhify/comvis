import shutil
import subprocess
from pathlib import Path

import psutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def safe_float(value, default=None):
    """
    Convert value ke float secara aman.
    Kalau gagal, return default.
    """
    try:
        return float(str(value).strip())
    except Exception:
        return default


def get_cpu_usage():
    """
    Mengambil penggunaan CPU dalam persen.
    """
    return round(psutil.cpu_percent(interval=0.1), 2)


def get_ram_usage():
    """
    Mengambil informasi penggunaan RAM.
    """
    ram = psutil.virtual_memory()

    return {
        "percent": round(ram.percent, 2),
        "used_gb": round(ram.used / (1024 ** 3), 2),
        "total_gb": round(ram.total / (1024 ** 3), 2),
    }


def get_disk_usage(path=PROJECT_ROOT):
    """
    Mengambil informasi penggunaan disk.
    Default path adalah root project.
    """
    disk = shutil.disk_usage(path)

    used = disk.used
    total = disk.total

    percent = (used / total) * 100 if total > 0 else 0

    return {
        "percent": round(percent, 2),
        "used_gb": round(used / (1024 ** 3), 2),
        "total_gb": round(total / (1024 ** 3), 2),
    }


def get_gpu_usage():
    """
    Mengambil informasi GPU menggunakan nvidia-smi.

    Data yang diambil:
    - name
    - utilization.gpu
    - memory.used
    - memory.total
    - temperature.gpu

    Kalau nvidia-smi tidak tersedia, return N/A.
    """

    command = [
        "nvidia-smi",
        "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]

    try:
        result = subprocess.check_output(
            command,
            stderr=subprocess.DEVNULL,
            timeout=2,
            text=True,
        )

        lines = result.strip().splitlines()

        if not lines:
            return {
                "available": False,
                "name": "N/A",
                "gpu_percent": None,
                "vram_used_gb": None,
                "vram_total_gb": None,
                "temperature": None,
            }

        # Untuk prototype, ambil GPU pertama saja.
        # Kalau nanti ada lebih dari 1 GPU, bisa dikembangkan.
        first_gpu = lines[0]
        parts = [part.strip() for part in first_gpu.split(",")]

        if len(parts) < 5:
            return {
                "available": False,
                "name": "N/A",
                "gpu_percent": None,
                "vram_used_gb": None,
                "vram_total_gb": None,
                "temperature": None,
            }

        gpu_name = parts[0]
        gpu_percent = safe_float(parts[1], default=None)
        memory_used_mb = safe_float(parts[2], default=None)
        memory_total_mb = safe_float(parts[3], default=None)
        temperature = safe_float(parts[4], default=None)

        vram_used_gb = None
        vram_total_gb = None

        if memory_used_mb is not None:
            vram_used_gb = round(memory_used_mb / 1024, 2)

        if memory_total_mb is not None:
            vram_total_gb = round(memory_total_mb / 1024, 2)

        return {
            "available": True,
            "name": gpu_name,
            "gpu_percent": gpu_percent,
            "vram_used_gb": vram_used_gb,
            "vram_total_gb": vram_total_gb,
            "temperature": temperature,
        }

    except FileNotFoundError:
        return {
            "available": False,
            "name": "N/A",
            "gpu_percent": None,
            "vram_used_gb": None,
            "vram_total_gb": None,
            "temperature": None,
        }

    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "name": "N/A",
            "gpu_percent": None,
            "vram_used_gb": None,
            "vram_total_gb": None,
            "temperature": None,
        }

    except Exception:
        return {
            "available": False,
            "name": "N/A",
            "gpu_percent": None,
            "vram_used_gb": None,
            "vram_total_gb": None,
            "temperature": None,
        }


def get_server_stats():
    """
    Menggabungkan semua data server monitoring.
    """
    return {
        "cpu": {
            "percent": get_cpu_usage(),
        },
        "ram": get_ram_usage(),
        "disk": get_disk_usage(),
        "gpu": get_gpu_usage(),
    }