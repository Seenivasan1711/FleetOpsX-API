from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InstructionCreate(BaseModel):
    rule_text: str
    priority: int = Field(default=3, ge=1, le=5)


class InstructionUpdate(BaseModel):
    rule_text: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)


class InstructionOut(BaseModel):
    id: UUID
    rule_text: str
    priority: int
    is_active: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
