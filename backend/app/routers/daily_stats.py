from fastapi import APIRouter, Depends

from app.daily_stats_reader import read_daily_stats, read_hourly_stats
from app.deps import get_current_user

router = APIRouter(prefix="/api", tags=["daily-stats"])


@router.get("/daily-stats")
def daily_stats(days: int = 14, user=Depends(get_current_user)):
    """
    Rekap jumlah orang terdeteksi per hari (Tahap Database).
    Sumber: outputs/comvis_stats.db (SQLite), diisi oleh worker (main.py).
    """
    days = max(1, min(days, 90))
    return read_daily_stats(days=days)


@router.get("/hourly-stats")
def hourly_stats(date: str | None = None, user=Depends(get_current_user)):
    """
    Jumlah orang per jam untuk satu tanggal (default: hari ini).
    Untuk halaman Analitik.
    """
    return read_hourly_stats(date_text=date)
