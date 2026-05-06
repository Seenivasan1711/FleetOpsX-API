import io
from datetime import datetime, time
from typing import Any
from uuid import UUID
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.order import Order


_REQUIRED = {"delivery_address", "scheduled_date"}
_PRIORITY_VALUES = {"LOW", "NORMAL", "HIGH", "CRITICAL"}


def _parse_time(val: Any) -> time | None:
    if not val:
        return None
    if isinstance(val, time):
        return val
    s = str(val).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    return None


def _parse_float(val: Any) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("yes", "true", "1")


def import_orders_from_excel(db: Session, tenant_id: str, file_bytes: bytes) -> dict:
    wb = load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"created": 0, "errors": ["Empty file"]}

    headers = [str(h).strip().lower() if h else "" for h in rows[0]]
    created = 0
    errors: list[str] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        row_data = dict(zip(headers, row))

        # validate required
        missing = [f for f in _REQUIRED if not row_data.get(f)]
        if missing:
            errors.append(f"Row {row_idx}: missing required fields: {', '.join(missing)}")
            continue

        # parse scheduled_date
        raw_date = row_data.get("scheduled_date")
        if isinstance(raw_date, datetime):
            scheduled_date = raw_date
        else:
            try:
                scheduled_date = datetime.strptime(str(raw_date).strip(), "%Y-%m-%d")
            except ValueError:
                errors.append(f"Row {row_idx}: invalid scheduled_date '{raw_date}' (expected YYYY-MM-DD)")
                continue

        priority = str(row_data.get("priority") or "NORMAL").strip().upper()
        if priority not in _PRIORITY_VALUES:
            priority = "NORMAL"

        try:
            order = Order(
                tenant_id=UUID(tenant_id),
                external_ref=str(row_data.get("external_ref") or "").strip() or None,
                delivery_address=str(row_data["delivery_address"]).strip(),
                delivery_latitude=_parse_float(row_data.get("delivery_latitude")),
                delivery_longitude=_parse_float(row_data.get("delivery_longitude")),
                scheduled_date=scheduled_date,
                time_window_start=_parse_time(row_data.get("time_window_start")),
                time_window_end=_parse_time(row_data.get("time_window_end")),
                weight_kg=_parse_float(row_data.get("weight_kg")),
                priority=priority,
                requires_refrigeration=_parse_bool(row_data.get("requires_refrigeration")),
                notes=str(row_data.get("notes") or "").strip() or None,
                status="PENDING",
            )
            db.add(order)
            created += 1
        except Exception as exc:
            errors.append(f"Row {row_idx}: {exc}")

    if created:
        db.commit()

    return {"created": created, "errors": errors}
