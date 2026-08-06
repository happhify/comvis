from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import auth_db
from app.routers import (
    auth,
    cameras,
    control,
    daily_stats,
    detections,
    server,
    stats,
    stream,
    users,
    validation,
)

# Siapkan database auth + user default saat backend pertama jalan
auth_db.init_db()


app = FastAPI(
    title="Comvis RTSP Employee Detection API",
    description="Backend API untuk React dashboard realtime Computer Vision.",
    version="0.1.0",
)


# ============================================================
# CORS Middleware
# ============================================================
# Ini penting agar React dari localhost:5173 bisa fetch ke FastAPI localhost:8000.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Routers
# ============================================================

app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(users.router)
app.include_router(stats.router)
app.include_router(control.router)
app.include_router(detections.router)
app.include_router(validation.router)
app.include_router(daily_stats.router)
app.include_router(server.router)
app.include_router(stream.router)


# ============================================================
# Root endpoint
# ============================================================

@app.get("/")
def root():
    """
    Endpoint testing.
    Dipakai untuk memastikan FastAPI berhasil berjalan.
    """
    return {
        "status": "ok",
        "message": "Backend FastAPI Computer Vision aktif.",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
