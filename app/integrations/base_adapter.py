from abc import ABC, abstractmethod
from app.schemas.order import OrderCreate


class BaseAdapter(ABC):
    """Normalize a partner's raw payload into the canonical OrderCreate schema."""

    @abstractmethod
    def transform(self, raw: dict) -> OrderCreate:
        ...
