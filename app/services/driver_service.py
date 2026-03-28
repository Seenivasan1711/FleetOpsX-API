from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.driver import Driver
from app.schemas.driver import DriverCreate, DriverUpdate


def create_driver(db: Session, tenant_id: str, data: DriverCreate) -> Driver:
    obj = Driver(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_driver(db: Session, tenant_id: str, driver_id: UUID) -> Optional[Driver]:
    return db.execute(
        select(Driver).where(Driver.id == driver_id, Driver.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()


def list_drivers(
    db: Session,
    tenant_id: str,
    active_only: bool = False,
    depot_id: Optional[UUID] = None,
) -> list[Driver]:
    q = select(Driver).where(Driver.tenant_id == UUID(tenant_id))
    if active_only:
        q = q.where(Driver.is_active == True)
    if depot_id:
        q = q.where(Driver.home_depot_id == depot_id)
    return list(db.execute(q).scalars().all())


def update_driver(db: Session, tenant_id: str, driver_id: UUID, data: DriverUpdate) -> Optional[Driver]:
    obj = get_driver(db, tenant_id, driver_id)
    if not obj:
        return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_driver(db: Session, tenant_id: str, driver_id: UUID) -> bool:
    obj = get_driver(db, tenant_id, driver_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
