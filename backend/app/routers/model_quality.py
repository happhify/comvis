from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.model_quality import get_model_quality

router = APIRouter(prefix="/api", tags=["model-quality"])


@router.get("/model-quality")
def model_quality(user=Depends(get_current_user)):
    """
    Ringkasan kualitas & validasi model:
    - ambang yang sedang dipakai (config/camera.yaml)
    - hasil negative-only test & positive test terakhir
    - kesimpulan jujur apakah 'Verified' sudah boleh dianggap final
    """
    return get_model_quality()
