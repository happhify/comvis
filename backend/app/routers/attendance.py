from fastapi import APIRouter, Depends

from app.attendance_reader import get_attendance_today_all
from app.deps import get_current_user

router = APIRouter(prefix="/api", tags=["attendance"])


@router.get("/attendance-today")
def attendance_today(user=Depends(get_current_user)):
    return get_attendance_today_all()
