from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def create_customer(db: Session, tenant_id: str, data: CustomerCreate) -> Customer:
    obj = Customer(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_customer(db: Session, tenant_id: str, customer_id: UUID) -> Optional[Customer]:
    return db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()


def list_customers(
    db: Session,
    tenant_id: str,
    active_only: bool = False,
    zone: Optional[str] = None,
) -> list[Customer]:
    q = select(Customer).where(Customer.tenant_id == UUID(tenant_id))
    if active_only:
        q = q.where(Customer.is_active == True)
    if zone:
        q = q.where(Customer.zone == zone)
    return list(db.execute(q).scalars().all())


def update_customer(db: Session, tenant_id: str, customer_id: UUID, data: CustomerUpdate) -> Optional[Customer]:
    obj = get_customer(db, tenant_id, customer_id)
    if not obj:
        return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_customer(db: Session, tenant_id: str, customer_id: UUID) -> bool:
    obj = get_customer(db, tenant_id, customer_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
