"""
Planning Instructions API — AI-1 E4.

GET    /plan/instructions        — list all instructions (active or all)
POST   /plan/instructions        — create a new rule
PATCH  /plan/instructions/{id}   — update rule_text or priority
DELETE /plan/instructions/{id}   — delete a rule
PATCH  /plan/instructions/{id}/toggle — toggle is_active
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_dispatcher
from app.models.planning_instruction import PlanningInstruction
from app.schemas.planning_instruction import InstructionCreate, InstructionOut, InstructionUpdate

router = APIRouter(prefix="/plan/instructions", tags=["Planning Instructions"])


@router.get("", response_model=List[InstructionOut])
def list_instructions(
    active_only: bool = Query(True, description="Return only active instructions"),
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    q = select(PlanningInstruction).where(
        PlanningInstruction.tenant_id == current_user.tenant_id
    ).order_by(PlanningInstruction.priority, PlanningInstruction.created_at)

    if active_only:
        q = q.where(PlanningInstruction.is_active == True)

    rows = db.execute(q).scalars().all()
    return [InstructionOut.model_validate(r) for r in rows]


@router.post("", response_model=InstructionOut, status_code=status.HTTP_201_CREATED)
def create_instruction(
    body: InstructionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    row = PlanningInstruction(
        tenant_id=current_user.tenant_id,
        rule_text=body.rule_text,
        priority=body.priority,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return InstructionOut.model_validate(row)


@router.patch("/{instruction_id}", response_model=InstructionOut)
def update_instruction(
    instruction_id: UUID,
    body: InstructionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    row = _get_or_404(db, current_user.tenant_id, instruction_id)
    if body.rule_text is not None:
        row.rule_text = body.rule_text
    if body.priority is not None:
        row.priority = body.priority
    db.commit()
    db.refresh(row)
    return InstructionOut.model_validate(row)


@router.delete("/{instruction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instruction(
    instruction_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    row = _get_or_404(db, current_user.tenant_id, instruction_id)
    db.delete(row)
    db.commit()


@router.patch("/{instruction_id}/toggle", response_model=InstructionOut)
def toggle_instruction(
    instruction_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_dispatcher),
):
    row = _get_or_404(db, current_user.tenant_id, instruction_id)
    row.is_active = not row.is_active
    db.commit()
    db.refresh(row)
    return InstructionOut.model_validate(row)


def _get_or_404(db: Session, tenant_id, instruction_id: UUID) -> PlanningInstruction:
    row = db.execute(
        select(PlanningInstruction).where(
            PlanningInstruction.id == instruction_id,
            PlanningInstruction.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return row
