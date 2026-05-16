from uuid import UUID
from typing import Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate


def create_order(db: Session, tenant_id: str, data: OrderCreate) -> Order:
    obj = Order(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_order(db: Session, tenant_id: str, order_id: UUID) -> Optional[Order]:
    return db.execute(
        select(Order)
        .options(joinedload(Order.assigned_driver))
        .where(Order.id == order_id, Order.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()


def list_orders(
    db: Session,
    tenant_id: str,
    plan_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[str] = None,
    unassigned_only: bool = False,
) -> list[Order]:
    q = select(Order).options(joinedload(Order.assigned_driver)).where(Order.tenant_id == UUID(tenant_id))
    if plan_date:
        day_start = datetime.combine(plan_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        q = q.where(Order.scheduled_date >= day_start, Order.scheduled_date < day_end)
    elif date_from or date_to:
        if date_from:
            q = q.where(Order.scheduled_date >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            q = q.where(Order.scheduled_date < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1))
    if status:
        q = q.where(Order.status == status)
    if unassigned_only:
        q = q.where(Order.assigned_driver_id == None)
    q = q.order_by(Order.scheduled_date)
    return list(db.execute(q).scalars().all())


def update_order(db: Session, tenant_id: str, order_id: UUID, data: OrderUpdate) -> Optional[Order]:
    obj = get_order(db, tenant_id, order_id)
    if not obj:
        return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit()
    db.refresh(obj)
    return obj


def delete_order(db: Session, tenant_id: str, order_id: UUID) -> bool:
    obj = get_order(db, tenant_id, order_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
