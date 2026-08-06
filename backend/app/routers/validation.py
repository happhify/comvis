from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.model_quality import get_model_quality
from app.validation_reader import get_validation_status

router = APIRouter(prefix="/api", tags=["validation"])


@router.get("/validation-status")
def validation_status(user=Depends(get_current_user)):
    """
    Status validasi model untuk warning di dashboard (Tahap 10):
    - positive test Hadi sudah/belum final
    - kandidat false positive dari negative_only_summary.csv
    """
    return get_validation_status()


@router.get("/model-quality")
def model_quality(user=Depends(get_current_user)):
    """
    Ringkasan kualitas & validasi model:
    - ambang yang sedang dipakai (config/camera.yaml)
    - hasil negative-only test & positive test terakhir
    - kesimpulan jujur apakah 'Verified' sudah boleh dianggap final
    """
    return get_model_quality()
