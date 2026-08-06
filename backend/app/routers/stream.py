from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.deps import get_current_user
from app.shared_state import shared_state
from app.video_stream import mjpeg_generator

router = APIRouter(prefix="/api", tags=["stream"])


@router.post("/frame")
async def receive_frame(request: Request):
    """
    Endpoint internal untuk menerima frame JPEG dari worker (main.py).

    Worker akan mengirim annotated_frame yang sudah diubah menjadi JPEG.
    """
    frame_bytes = await request.body()

    if not frame_bytes:
        return {
            "status": "error",
            "message": "Frame kosong.",
        }

    shared_state.update_frame(frame_bytes)

    return {
        "status": "ok",
        "message": "Frame diterima.",
    }


@router.get("/frame-status")
def frame_status(user=Depends(get_current_user)):
    """
    Endpoint debug untuk mengecek apakah FastAPI sudah menerima frame.
    """
    return shared_state.get_frame_status()


@router.get("/stream")
def stream(user=Depends(get_current_user)):
    """
    Endpoint MJPEG stream untuk React dashboard.

    (Sebelumnya /video_feed, dipindah ke bawah /api/ supaya nginx cukup
    satu aturan "/api/ -> backend", dengan proxy_buffering dimatikan
    khusus untuk path ini karena formatnya multipart MJPEG streaming.)
    """
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
