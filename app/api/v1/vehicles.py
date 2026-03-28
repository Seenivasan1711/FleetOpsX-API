from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from app.services import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.post("/", response_model=VehicleResponse, status_code=201)
def create_vehicle(
    data: VehicleCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return vehicle_service.create_vehicle(db, tenant_id, data)


@router.get("/", response_model=List[VehicleResponse])
def list_vehicles(
    active_only: bool = False,
    depot_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return vehicle_service.list_vehicles(db, tenant_id, active_only=active_only, depot_id=depot_id)


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = vehicle_service.get_vehicle(db, tenant_id, vehicle_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return obj


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: UUID,
    data: VehicleUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = vehicle_service.update_vehicle(db, tenant_id, vehicle_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return obj


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    if not vehicle_service.delete_vehicle(db, tenant_id, vehicle_id):
        raise HTTPException(status_code=404, detail="Vehicle not found")
