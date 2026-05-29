from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class LearningPatternOut(BaseModel):
    id: UUID
    pattern_type: str
    pattern_text: str
    trigger_conditions: Optional[Dict[str, Any]]
    times_observed: int
    status: str
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    note: Optional[str] = None
