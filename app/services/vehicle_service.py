from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


def create_vehicle(db: Session, tenant_id: str, data: VehicleCreate) -> Vehicle:
    obj = Vehicle(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_vehicle(db: Session, tenant_id: str, vehicle_id: UUID) -> Optional[Vehicle]:
    return db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()


def list_vehicles(
    db: Session,
    tenant_id: str,
    active_only: bool = False,
    depot_id: Optional[UUID] = None,
) -> list[Vehicle]:
    q = select(Vehicle).where(Vehicle.tenant_id == UUID(tenant_id))
    if active_only:
        q = q.where(Vehicle.is_active == True)
    if depot_id:
        q = q.where(Vehicle.home_depot_id == depot_id)
    return list(db.execute(q).scalars().all())


def update_vehicle(db: Session, tenant_id: str, vehicle_id: UUID, data: VehicleUpdate) -> Optional[Vehicle]:
    obj = get_vehicle(db, tenant_id, vehicle_id)
    if not obj:
        return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_vehicle(db: Session, tenant_id: str, vehicle_id: UUID) -> bool:
    obj = get_vehicle(db, tenant_id, vehicle_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
