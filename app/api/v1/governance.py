"""Governance API — P4-E4.

POST   /governance/data-export              — trigger async GDPR data export
GET    /governance/data-export/{task_id}    — poll export status / download URL
PATCH  /governance/retention               — set data retention policy (days)
GET    /governance/retention               — read current retention config
GET    /governance/roles                   — list RBAC roles for tenant
POST   /governance/roles                   — create custom RBAC role
DELETE /governance/roles/{role_id}         — delete non-system role
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.models.tenant import TenantConfig
from app.schemas.audit import (
    DataExportRequest,
    DataExportStatus,
    RbacRoleIn,
    RbacRoleOut,
    RetentionConfigIn,
    RetentionConfigOut,
)
from app.services import rbac_service

router = APIRouter(prefix="/governance", tags=["Governance"])


# ─── Data export ──────────────────────────────────────────────────────────────

@router.post("/data-export", response_model=DataExportStatus, status_code=202)
def trigger_data_export(
    _body: DataExportRequest = DataExportRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("governance:admin")),
):
    """Queue a full-tenant GDPR data export (Celery). Returns task_id to poll."""
    from app.workers.tasks import data_export_task
    result = data_export_task.apply_async(args=[str(current_user.tenant_id)])
    return DataExportStatus(task_id=result.id, status="PENDING")


@router.get("/data-export/{task_id}", response_model=DataExportStatus)
def get_export_status(
    task_id: str,
    current_user=Depends(require_permission("governance:admin")),
):
    """Poll data export task status."""
    from app.workers.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)

    if result.state == "SUCCESS":
        return DataExportStatus(
            task_id=task_id,
            status="SUCCESS",
            download_url=result.result.get("download_url") if isinstance(result.result, dict) else None,
        )
    if result.state == "FAILURE":
        return DataExportStatus(task_id=task_id, status="FAILURE", error=str(result.result))

    return DataExportStatus(task_id=task_id, status=result.state)


# ─── Retention policy ─────────────────────────────────────────────────────────

@router.get("/retention", response_model=RetentionConfigOut)
def get_retention(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("governance:admin")),
):
    cfg = db.execute(
        select(TenantConfig).where(
            TenantConfig.tenant_id == current_user.tenant_id,
            TenantConfig.key == "retention_days",
        )
    ).scalar_one_or_none()

    return RetentionConfigOut(
        retention_days=int(cfg.value) if cfg else 365,
        updated_at=cfg.updated_at if cfg else None,
    )


@router.patch("/retention", response_model=RetentionConfigOut)
def set_retention(
    body: RetentionConfigIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("governance:admin")),
):
    cfg = db.execute(
        select(TenantConfig).where(
            TenantConfig.tenant_id == current_user.tenant_id,
            TenantConfig.key == "retention_days",
        )
    ).scalar_one_or_none()

    if cfg:
        cfg.value = str(body.retention_days)
    else:
        cfg = TenantConfig(
            tenant_id=current_user.tenant_id,
            key="retention_days",
            value=str(body.retention_days),
        )
        db.add(cfg)

    db.commit()
    db.refresh(cfg)
    return RetentionConfigOut(retention_days=body.retention_days, updated_at=cfg.updated_at)


# ─── RBAC role management ─────────────────────────────────────────────────────

@router.get("/roles", response_model=list[RbacRoleOut])
def list_roles(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("rbac:manage")),
):
    return rbac_service.list_roles(db, current_user.tenant_id)


@router.post("/roles", response_model=RbacRoleOut, status_code=201)
def create_role(
    body: RbacRoleIn,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("rbac:manage")),
):
    role = rbac_service.create_role(
        db=db,
        tenant_id=current_user.tenant_id,
        name=body.name,
        permissions=body.permissions,
    )
    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("rbac:manage")),
):
    deleted = rbac_service.delete_role(db, role_id, current_user.tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Role not found or is a system role")
    db.commit()
