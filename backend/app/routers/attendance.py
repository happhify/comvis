from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.history_reader import get_attendance_today

router = APIRouter(prefix="/api", tags=["attendance"])


@router.get("/attendance-today")
def attendance_today(user=Depends(get_current_user)):
    return get_attendance_today()
