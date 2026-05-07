from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.availability import FleetAvailabilityResponse
from app.services import availability_service

router = APIRouter(prefix="/fleet", tags=["Fleet"])


@router.get("/availability", response_model=FleetAvailabilityResponse)
def get_fleet_availability(
    for_date: date = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    target_date = for_date or date.today()
    return availability_service.get_fleet_availability(db, tenant_id, target_date)
