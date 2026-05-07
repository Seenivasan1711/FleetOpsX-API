from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from sqlalchemy.orm import Session


class PlannerInterface(ABC):

    @abstractmethod
    def plan_day(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
    ) -> dict[str, Any]:
        """
        Execute planning for a tenant on a given date.
        Returns dict with 'assignments' list and metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def replan(
        self,
        db: Session,
        tenant_id: str,
        plan_date: date,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Re-plan based on real-time context (delays, new orders, cancellations).
        """
        raise NotImplementedError
