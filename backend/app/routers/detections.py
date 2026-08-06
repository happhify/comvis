import csv as _csv
import io as _io

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.deps import get_current_user
from app.history_reader import history_rows_for_csv, read_history
from app.log_reader import read_recent_detections

router = APIRouter(prefix="/api", tags=["detections"])


@router.get("/recent-detections")
def recent_detections(limit: int = 10, user=Depends(get_current_user)):
    """
    Mengambil riwayat deteksi terbaru dari outputs/logs/detection_log.csv.
    """
    limit = max(1, min(limit, 100))

    return read_recent_detections(limit=limit)


@router.get("/detection-history")
def detection_history(date: str | None = None, status: str = "all",
                      limit: int = 30, offset: int = 0,
                      user=Depends(get_current_user)):
    """Riwayat deteksi (kejadian per orang) dengan filter tanggal & status."""
    return read_history(date_text=date, status=status, limit=limit, offset=offset)


@router.get("/detection-history/export")
def detection_history_export(date: str | None = None, status: str = "all",
                             user=Depends(get_current_user)):
    """Ekspor riwayat sesuai filter sebagai berkas CSV."""
    rows = history_rows_for_csv(date_text=date, status=status)
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["Jam masuk", "Jam keluar", "Durasi (detik)", "Kamera",
                "Status", "Label", "Keyakinan", "Frame"])
    for s in rows:
        w.writerow([s["first_seen"], s["last_seen"], s["duration_seconds"], s["camera"],
                    s["status"], s["identity_label"], s["confidence"], s["frames"]])
    fname = f"riwayat_{date or 'semua'}.csv"
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={fname}"})
