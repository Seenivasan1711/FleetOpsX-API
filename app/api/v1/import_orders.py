from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services import import_service

router = APIRouter(prefix="/import", tags=["Import"])


@router.post("/orders")
async def import_orders(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are accepted")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB guard
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    result = import_service.import_orders_from_excel(
        db, str(current_user.tenant_id), contents
    )
    return result
