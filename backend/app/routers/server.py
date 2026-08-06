from fastapi import APIRouter, Depends

from app.deps import require_role
from app.server_monitor import get_server_stats

router = APIRouter(prefix="/api", tags=["server"])


@router.get("/server-stats")
def server_stats(user=Depends(require_role("admin", "super_admin"))):
    """
    Endpoint monitoring server/laptop.

    Untuk tahap awal:
    - CPU real
    - RAM real
    - Disk real
    - GPU masih N/A agar tidak error
    """
    return get_server_stats()
