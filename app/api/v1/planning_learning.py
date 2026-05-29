"""
Planning Learning API — AI-1 E4.

GET   /plan/learning             — list detected patterns (filterable by status)
PATCH /plan/learning/{id}/approve — approve a pattern (loaded in future runs)
PATCH /plan/learning/{id}/reject  — reject a pattern (ignored forever)
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.planning_learning import PlanningLearning
from app.schemas.planning_learning import LearningPatternOut, ReviewRequest

router = APIRouter(prefix="/plan/learning", tags=["Planning Learning"])


@router.get("", response_model=List[LearningPatternOut])
def list_patterns(
    pattern_status: Optional[str] = Query(None, alias="status",
                                          description="PENDING_APPROVAL | APPROVED | REJECTED"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Return detected planning patterns for the tenant, most recent first."""
    q = select(PlanningLearning).where(
        PlanningLearning.tenant_id == current_user.tenant_id
    ).order_by(PlanningLearning.created_at.desc())

    if pattern_status:
        q = q.where(PlanningLearning.status == pattern_status.upper())

    rows = db.execute(q).scalars().all()
    return [LearningPatternOut.model_validate(r) for r in rows]


@router.patch("/{pattern_id}/approve", response_model=LearningPatternOut)
def approve_pattern(
    pattern_id: UUID,
    body: ReviewRequest = ReviewRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """
    Approve a learning pattern.
    Once approved it will be loaded into AgentContext.learning_patterns on every future run.
    """
    row = _get_or_404(db, current_user.tenant_id, pattern_id)
    row.status = "APPROVED"
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return LearningPatternOut.model_validate(row)


@router.patch("/{pattern_id}/reject", response_model=LearningPatternOut)
def reject_pattern(
    pattern_id: UUID,
    body: ReviewRequest = ReviewRequest(),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    """Reject a learning pattern — it will not be surfaced again."""
    row = _get_or_404(db, current_user.tenant_id, pattern_id)
    row.status = "REJECTED"
    row.reviewed_by = current_user.id
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return LearningPatternOut.model_validate(row)


def _get_or_404(db: Session, tenant_id, pattern_id: UUID) -> PlanningLearning:
    row = db.execute(
        select(PlanningLearning).where(
            PlanningLearning.id == pattern_id,
            PlanningLearning.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Learning pattern not found")
    return row
