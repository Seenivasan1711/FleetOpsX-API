from datetime import datetime
from app.integrations.base_adapter import BaseAdapter
from app.schemas.order import OrderCreate


class GenericAdapter(BaseAdapter):
    """Flexible field-mapping adapter — reads from a flat dict with standard field names.

    Expected canonical field names (all optional except delivery_address):
      delivery_address, delivery_latitude, delivery_longitude,
      scheduled_date (ISO string), priority, weight_kg, quantity_units,
      external_ref, notes
    """

    def transform(self, raw: dict) -> OrderCreate:
        scheduled_date = datetime.now()
        raw_date = raw.get("scheduled_date", "")
        if raw_date:
            try:
                scheduled_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            except ValueError:
                pass

        def _float(key: str):
            try:
                return float(raw[key]) if raw.get(key) is not None else None
            except (TypeError, ValueError):
                return None

        def _int(key: str):
            try:
                return int(raw[key]) if raw.get(key) is not None else None
            except (TypeError, ValueError):
                return None

        return OrderCreate(
            delivery_address=str(raw.get("delivery_address", "Unknown address")),
            delivery_latitude=_float("delivery_latitude"),
            delivery_longitude=_float("delivery_longitude"),
            scheduled_date=scheduled_date,
            priority=str(raw.get("priority", "NORMAL")).upper(),
            weight_kg=_float("weight_kg"),
            quantity_units=_int("quantity_units"),
            external_ref=str(raw.get("external_ref", "")) or None,
            notes=str(raw.get("notes", "")) or None,
        )
