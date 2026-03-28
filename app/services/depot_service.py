from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.depot import Depot
from app.schemas.depot import DepotCreate, DepotUpdate


def create_depot(db: Session, tenant_id: str, data: DepotCreate) -> Depot:
    obj = Depot(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_depot(db: Session, tenant_id: str, depot_id: UUID) -> Optional[Depot]:
    return db.execute(
        select(Depot).where(Depot.id == depot_id, Depot.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()


def list_depots(db: Session, tenant_id: str, active_only: bool = False) -> list[Depot]:
    q = select(Depot).where(Depot.tenant_id == UUID(tenant_id))
    if active_only:
        q = q.where(Depot.is_active == True)
    return list(db.execute(q).scalars().all())


def update_depot(db: Session, tenant_id: str, depot_id: UUID, data: DepotUpdate) -> Optional[Depot]:
    obj = get_depot(db, tenant_id, depot_id)
    if not obj:
        return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_depot(db: Session, tenant_id: str, depot_id: UUID) -> bool:
    obj = get_depot(db, tenant_id, depot_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
