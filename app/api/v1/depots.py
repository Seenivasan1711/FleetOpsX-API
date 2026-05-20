from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_tenant_id
from app.schemas.depot import DepotCreate, DepotUpdate, DepotResponse
from app.services import depot_service, export_service, import_service

router = APIRouter(prefix="/depots", tags=["Depots"])


@router.post("/", response_model=DepotResponse, status_code=201)
def create_depot(
    data: DepotCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return depot_service.create_depot(db, tenant_id, data)


@router.get("/", response_model=List[DepotResponse])
def list_depots(
    active_only: bool = False,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    return depot_service.list_depots(db, tenant_id, active_only=active_only)


@router.get("/export", response_class=Response)
def export_depots(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    data = export_service.depots_to_csv(db, UUID(tenant_id))
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=depots.csv"},
    )


@router.post("/import")
def import_depots(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    content = file.file.read()
    return import_service.import_depots_from_csv(db, UUID(tenant_id), content)


@router.get("/{depot_id}", response_model=DepotResponse)
def get_depot(
    depot_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = depot_service.get_depot(db, tenant_id, depot_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Depot not found")
    return obj


@router.patch("/{depot_id}", response_model=DepotResponse)
def update_depot(
    depot_id: UUID,
    data: DepotUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    obj = depot_service.update_depot(db, tenant_id, depot_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Depot not found")
    return obj


@router.delete("/{depot_id}", status_code=204)
def delete_depot(
    depot_id: UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    if not depot_service.delete_depot(db, tenant_id, depot_id):
        raise HTTPException(status_code=404, detail="Depot not found")
