import io
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from app.models.order import Order
from app.models.route_plan import RoutePlan, Route, RouteStop


_HEADER_FILL = PatternFill("solid", fgColor="1E40AF")
_HEADER_FONT = Font(bold=True, color="FFFFFF")


def _style_header(ws, headers: list[str]):
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(col)].width = max(len(h) + 4, 14)


def orders_to_excel(db: Session, tenant_id: str) -> bytes:
    orders = db.execute(
        select(Order).where(Order.tenant_id == UUID(tenant_id))
    ).scalars().all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"

    headers = [
        "ID", "External Ref", "Delivery Address", "Weight (kg)",
        "Time Window Start", "Time Window End", "Scheduled Date",
        "Status", "Priority", "Requires Refrigeration", "Notes",
    ]
    _style_header(ws, headers)

    for order in orders:
        ws.append([
            str(order.id),
            order.external_ref or "",
            order.delivery_address,
            order.weight_kg,
            str(order.time_window_start) if order.time_window_start else "",
            str(order.time_window_end) if order.time_window_end else "",
            order.scheduled_date.strftime("%Y-%m-%d") if order.scheduled_date else "",
            order.status,
            order.priority,
            "Yes" if order.requires_refrigeration else "No",
            order.notes or "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def plan_to_excel(db: Session, tenant_id: str, plan_id: UUID) -> bytes | None:
    plan = db.execute(
        select(RoutePlan).where(
            RoutePlan.id == plan_id,
            RoutePlan.tenant_id == UUID(tenant_id),
        )
    ).scalar_one_or_none()
    if not plan:
        return None

    wb = Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    for route in plan.routes:
        driver_name = route.driver.name if route.driver else "Unassigned"
        ws = wb.create_sheet(title=driver_name[:31])  # Excel sheet name max 31 chars

        headers = ["Stop #", "Order ID", "Delivery Address", "Status", "Est. Arrival", "Weight (kg)", "Priority"]
        _style_header(ws, headers)

        for stop in route.stops:
            order = stop.order
            ws.append([
                stop.sequence,
                str(stop.order_id),
                order.delivery_address if order else "",
                stop.status,
                stop.estimated_arrival or "",
                order.weight_kg if order else "",
                order.priority if order else "",
            ])

    if not wb.sheetnames:
        ws = wb.create_sheet("No Routes")
        ws.append(["No routes in this plan"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def orders_import_template() -> bytes:
    """Return a blank orders import template with headers and sample row."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders Import"

    headers = [
        "external_ref", "delivery_address", "delivery_latitude", "delivery_longitude",
        "scheduled_date", "time_window_start", "time_window_end",
        "weight_kg", "priority", "requires_refrigeration", "notes",
    ]
    _style_header(ws, headers)

    # sample row
    ws.append([
        "ORD-001",
        "123 MG Road, Bangalore",
        "12.9716",
        "77.5946",
        "2026-05-06",
        "09:00",
        "17:00",
        "5.0",
        "NORMAL",
        "No",
        "Leave at door",
    ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
