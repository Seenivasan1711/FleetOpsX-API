from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.driver import DriverCreate, DriverUpdate, DriverResponse
from app.services import driver_service

router = APIRouter(prefix="/drivers", tags=["Drivers"])


@router.post("/", response_model=DriverResponse, status_code=201)
def create_driver(
    data: DriverCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return driver_service.create_driver(db, tenant_id, data)


@router.get("/", response_model=List[DriverResponse])
def list_drivers(
    active_only: bool = False,
    depot_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return driver_service.list_drivers(db, tenant_id, active_only=active_only, depot_id=depot_id)


@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(
    driver_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = driver_service.get_driver(db, tenant_id, driver_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Driver not found")
    return obj


@router.patch("/{driver_id}", response_model=DriverResponse)
def update_driver(
    driver_id: UUID,
    data: DriverUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = driver_service.update_driver(db, tenant_id, driver_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Driver not found")
    return obj


@router.delete("/{driver_id}", status_code=204)
def delete_driver(
    driver_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    if not driver_service.delete_driver(db, tenant_id, driver_id):
        raise HTTPException(status_code=404, detail="Driver not found")
