"""
Planning Runs API — AI-1 E6.

GET  /plan/runs            — list recent runs for tenant
GET  /plan/runs/{run_id}   — full run status + checkpoints + error_info
POST /plan/runs/{run_id}/resume — re-dispatch a FAILED / BLOCKED run
"""
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.planning_run import PlanningRun

router = APIRouter(prefix="/plan/runs", tags=["Planning Runs"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CheckpointOut(BaseModel):
    agent_name: str
    phase: int
    status: str
    elapsed_ms: int
    output_preview: str
    warnings: List[str]
    completed_at: str


class PlanningRunOut(BaseModel):
    id: UUID
    plan_date: date
    session_id: Optional[UUID]
    status: str
    current_phase: Optional[int]
    current_agent: Optional[str]
    checkpoints: List[Dict[str, Any]]
    error_info: Optional[Dict[str, Any]]
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_row(cls, row: PlanningRun) -> "PlanningRunOut":
        return cls(
            id=row.id,
            plan_date=row.plan_date,
            session_id=row.session_id,
            status=row.status,
            current_phase=row.current_phase,
            current_agent=row.current_agent,
            checkpoints=row.checkpoints or [],
            error_info=row.error_info,
            started_at=row.started_at.isoformat() if row.started_at else None,
            completed_at=row.completed_at.isoformat() if row.completed_at else None,
        )


class ResumeOut(BaseModel):
    run_id: str
    resumed_from: str
    status: str


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=List[PlanningRunOut])
def list_runs(
    plan_date: Optional[date] = Query(None),
    run_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """List recent planning runs for the current tenant, newest first."""
    q = (
        select(PlanningRun)
        .where(PlanningRun.tenant_id == current_user.tenant_id)
        .order_by(PlanningRun.started_at.desc().nullslast())
        .limit(limit)
    )
    if plan_date:
        q = q.where(PlanningRun.plan_date == plan_date)
    if run_status:
        q = q.where(PlanningRun.status == run_status.upper())

    rows = db.execute(q).scalars().all()
    return [PlanningRunOut.from_orm_row(r) for r in rows]


@router.get("/{run_id}", response_model=PlanningRunOut)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return full run status, checkpoint history, and error info."""
    row = db.execute(
        select(PlanningRun).where(
            PlanningRun.id == run_id,
            PlanningRun.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Planning run not found")

    return PlanningRunOut.from_orm_row(row)


@router.get("/{run_id}/agents")
def get_run_agents(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Return the checkpoint detail for every agent that ran in this planning run.
    Includes status, elapsed_ms, output_preview, warnings, and progress_pct.
    Useful as a REST fallback when the WebSocket was not connected.
    """
    row = db.execute(
        select(PlanningRun).where(
            PlanningRun.id == run_id,
            PlanningRun.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Planning run not found")

    return {
        "run_id": str(run_id),
        "status": row.status,
        "agents": row.checkpoints or [],
        "error_info": row.error_info,
    }


@router.post("/{run_id}/resume", response_model=ResumeOut)
def resume_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Re-dispatch a FAILED or BLOCKED_WAITING_USER run.
    Creates a new run_id and enqueues a Celery task with the original params.
    """
    from app.planners.runner import resume_run as _resume

    try:
        result = _resume(
            db=db,
            run_id=str(run_id),
            tenant_id=str(current_user.tenant_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ResumeOut(**result)
