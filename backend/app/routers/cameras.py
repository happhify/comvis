"""
app/routers/cameras.py

Daftar kamera yang bisa dipilih dari dashboard (config/camera.yaml ->
cameras.list), digabung dengan info kamera yang SEDANG aktif di worker
(shared_state) supaya sidebar tahu kamera mana yang lagi live.
"""

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.shared_state import shared_state

router = APIRouter(prefix="/api", tags=["cameras"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "camera.yaml"


def _read_cameras_config():
    if not CONFIG_PATH.exists():
        return {"default": None, "list": []}

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return {"default": None, "list": []}

    cameras = cfg.get("cameras") or {}
    return {
        "default": cameras.get("default"),
        "list": cameras.get("list") or [],
    }


@router.get("/cameras")
def list_cameras(user=Depends(get_current_user)):
    cfg = _read_cameras_config()
    control = shared_state.get_control()
    stats = shared_state.get_stats()

    active_camera_id = control.get("camera_id") or cfg.get("default")

    cameras = [
        {"id": cam.get("id"), "name": cam.get("name", cam.get("id"))}
        for cam in cfg.get("list", [])
        if cam.get("id")
    ]

    return {
        "status": "ok",
        "active_camera_id": active_camera_id,
        # Nama & status kamera yang BENERAN lagi jalan di worker sekarang -
        # bisa beda sesaat dari active_camera_id selagi proses pindah kamera.
        "live_camera_name": stats.get("camera_name"),
        "live_camera_status": stats.get("camera_status"),
        "cameras": cameras,
    }
