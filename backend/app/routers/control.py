from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models.schemas import ControlRequest
from app.shared_state import shared_state

router = APIRouter(prefix="/api/control", tags=["control"])


@router.get("")
def get_control(user=Depends(get_current_user)):
    """Semua user login boleh MELIHAT status saklar."""
    return shared_state.get_control()


@router.post("")
def set_control(payload: ControlRequest,
                user=Depends(get_current_user)):
    """
    Pindah kamera (camera_id): semua user login boleh, itu cuma
    ganti tontonan, bukan perintah operasional.

    Matikan/nyalakan deteksi (detection_enabled): cuma admin/super_admin,
    karena itu memengaruhi apa yang tercatat di log & statistik.
    """
    is_admin = user["role"] in ("admin", "super_admin")

    if payload.detection_enabled is not None and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Hanya admin yang boleh mengubah status deteksi.",
        )

    updates = {}
    if payload.detection_enabled is not None:
        updates["detection_enabled"] = payload.detection_enabled
    if payload.camera_id:
        updates["camera_id"] = payload.camera_id

    shared_state.set_control(updates)
    return shared_state.get_control()
