from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.services import export_service

router = APIRouter(prefix="/export", tags=["Export"])

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/orders")
def export_orders(
    plan_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    data = export_service.orders_to_excel(
        db, str(current_user.tenant_id),
        plan_date=plan_date, date_from=date_from, date_to=date_to,
    )
    if plan_date:
        filename = f"orders-{plan_date}.xlsx"
    elif date_from or date_to:
        filename = f"orders-{date_from or 'start'}_{date_to or 'end'}.xlsx"
    else:
        filename = "orders-all.xlsx"
    return Response(
        content=data,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/plan/{plan_id}")
def export_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    data = export_service.plan_to_excel(db, str(current_user.tenant_id), plan_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return Response(
        content=data,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename=plan_{plan_id}.xlsx"},
    )


@router.get("/template")
def download_template():
    data = export_service.orders_import_template()
    return Response(
        content=data,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": "attachment; filename=orders_import_template.xlsx"},
    )
