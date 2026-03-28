from uuid import UUID
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return order_service.create_order(db, tenant_id, data)


@router.get("/", response_model=List[OrderResponse])
def list_orders(
    plan_date: Optional[date] = None,
    status: Optional[str] = None,
    unassigned_only: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return order_service.list_orders(
        db, tenant_id,
        plan_date=plan_date,
        status=status,
        unassigned_only=unassigned_only,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = order_service.get_order(db, tenant_id, order_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Order not found")
    return obj


@router.patch("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: UUID,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = order_service.update_order(db, tenant_id, order_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Order not found")
    return obj


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    if not order_service.delete_order(db, tenant_id, order_id):
        raise HTTPException(status_code=404, detail="Order not found")
