from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerResponse, status_code=201)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return customer_service.create_customer(db, tenant_id, data)


@router.get("/", response_model=List[CustomerResponse])
def list_customers(
    active_only: bool = False,
    zone: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return customer_service.list_customers(db, tenant_id, active_only=active_only, zone=zone)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = customer_service.get_customer(db, tenant_id, customer_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = customer_service.update_customer(db, tenant_id, customer_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found")
    return obj


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    if not customer_service.delete_customer(db, tenant_id, customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
