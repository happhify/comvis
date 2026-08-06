from fastapi import APIRouter, Depends, Request

from app.deps import get_current_user
from app.shared_state import shared_state

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
def get_stats(user=Depends(get_current_user)):
    """
    Mengambil statistik realtime dari shared_state.

    Jika worker (main.py) belum jalan, endpoint tetap mengembalikan data
    default WAITING.
    """
    return shared_state.get_stats()


@router.post("/stats-update")
async def update_stats(request: Request):
    """
    Endpoint internal untuk menerima statistik realtime dari worker (main.py).

    CATATAN: sengaja TIDAK dikunci login karena dipanggil oleh worker yang
    jalan di host (mengakses backend lewat port yang di-publish), bukan
    dari browser.
    """
    payload = await request.json()

    shared_state.update_stats(payload)

    # Jawaban ini "ditumpangi" saklar kontrol, supaya worker tahu
    # perintah terbaru dari dashboard tanpa perlu request tambahan.
    return {
        "status": "ok",
        "message": "Stats diterima.",
        "control": shared_state.get_control(),
    }
