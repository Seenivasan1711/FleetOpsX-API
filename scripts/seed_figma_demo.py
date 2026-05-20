#!/usr/bin/env python3
"""
FleetOpsX – Figma Design Demo Seed
Populates data that matches the dashboard redesign reference (Figma).

Usage:
  python scripts/seed_figma_demo.py            # seed
  python scripts/seed_figma_demo.py --clean    # remove figma demo data only

To undo everything this script does:
  python scripts/unseed_figma_demo.py
"""
import argparse
import uuid
import sys
import os
from datetime import date, time, datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    Tenant, TenantConfig, Depot, Driver, DriverShift, DriverAvailability,
    Vehicle, VehicleStatus, Customer, Order, User,
)
from app.models.route_plan import RoutePlan, Route, RouteStop

# ── Figma reference data ───────────────────────────────────────────────────────

FIGMA_TENANT_SLUG = "acme-logistics-figma"
TODAY = date.today()

# Drivers visible in the Figma Gantt chart (first 7), rest fill up to 20
FIGMA_DRIVERS = [
    # (name, stops_today, availability_status, shift_start_hour)
    ("Arjun Mehta",   8,  "AVAILABLE",  7),
    ("Priya Sharma",  6,  "AVAILABLE",  7),
    ("Rahul Iyer",    1,  "AVAILABLE",  8),
    ("Sneha Reddy",  11,  "AVAILABLE",  7),
    ("Vikram Singh",  4,  "AVAILABLE",  8),
    ("Ananya Iyer",   1,  "AVAILABLE",  8),
    ("Rohan Das",     7,  "AVAILABLE",  7),
    # remaining 13 — mix of statuses
    ("Kavya Nair",    5,  "AVAILABLE",  8),
    ("Suresh Bhat",   3,  "AVAILABLE",  9),
    ("Meena Pillai",  4,  "AVAILABLE",  8),
    ("Deepak Verma",  6,  "AVAILABLE",  8),
    ("Harish Rao",    2,  "AVAILABLE",  9),
    ("Pooja Gupta",   5,  "AVAILABLE",  8),
    ("Rajan Nair",    0,  "ON_BREAK",   8),   # 1 on break
    ("Swati Joshi",   0,  "OFF_DUTY",   8),   # 1 off duty
    ("Amit Tiwari",   3,  "AVAILABLE",  8),
    ("Lakshmi Devi",  4,  "AVAILABLE",  8),
    ("Nikhil Kumar",  2,  "AVAILABLE",  9),
    ("Preethi Raj",   5,  "AVAILABLE",  8),
    ("Sanjay Hegde",  3,  "AVAILABLE",  8),
]

# Vehicle statuses matching Figma (4 available, 14 in use, 1 maintenance, 1 low fuel)
VEHICLE_STATUSES = (
    ["IN_USE"] * 14 +
    ["AVAILABLE"] * 4 +
    ["MAINTENANCE"] * 1 +
    ["LOW_FUEL"] * 1
)

# Areas around Bangalore used for addresses
AREAS = [
    "HSR Sector 2", "Banaswadi Main Rd", "JP Nagar Phase 7",
    "Koramangala 4th Block", "Indiranagar 12th Main", "Whitefield Main Rd",
    "BTM Layout 2nd Stage", "Jayanagar 3rd Block", "Hebbal Outer Ring Rd",
    "Electronic City Phase 1", "Sarjapur Road", "Marathahalli Bridge",
    "Bellandur Lake Rd", "Banashankari 2nd Stage", "Yelahanka New Town",
    "Malleshwaram 15th Cross", "Rajajinagar 3rd Block", "Basavanagudi",
    "Vijayanagar 4th Stage", "RT Nagar Main Rd",
]

# At-risk orders matching the Figma exactly
AT_RISK_ORDERS = [
    {
        "ref": "ORD-2026-115",
        "address": "42, HSR Sector 2, Bangalore",
        "lat": 12.9141, "lng": 77.6369,
        "time_window_start": time(10, 0), "time_window_end": time(11, 0),
        "priority": "HIGH",
        "delay_minutes": 18,
        "delay_reason": "Driver running 18 min late · Traffic on ORR",
        "ai_suggestion": "Reassign to Ananya Iyer (Electronic City depot)",
    },
    {
        "ref": "ORD-2026-119",
        "address": "Banaswadi Main Rd, Bangalore",
        "lat": 13.0012, "lng": 77.6550,
        "time_window_start": time(11, 0), "time_window_end": time(12, 0),
        "priority": "HIGH",
        "delay_minutes": 12,
        "delay_reason": "Stop window closes 12 min after current ETA",
        "ai_suggestion": "Skip ORD-118 stop, return after delivery",
    },
    {
        "ref": "ORD-2026-103",
        "address": "JP Nagar Phase 7, Bangalore",
        "lat": 12.9010, "lng": 77.5846,
        "time_window_start": time(10, 30), "time_window_end": time(11, 30),
        "priority": "NORMAL",
        "delay_minutes": 7,
        "delay_reason": "Customer rescheduled — earlier time window",
        "ai_suggestion": "Swap with ORD-2026-122 in same area",
    },
]


def _make_stop_times(route_start_hour: int, num_stops: int):
    """Returns list of (start_dt, end_dt) for each stop, evenly spaced."""
    base = datetime.combine(TODAY, time(route_start_hour, 0))
    gap  = 50  # minutes per stop
    times = []
    for i in range(num_stops):
        start = base + timedelta(minutes=i * gap)
        end   = start + timedelta(minutes=30)
        times.append((start, end))
    return times


def seed():
    db = SessionLocal()
    try:
        print("🎨  Seeding Figma demo data for FleetOpsX dashboard redesign...")

        # ── Remove any existing figma demo tenant ─────────────────────────────
        existing = db.execute(
            select(Tenant).where(Tenant.slug == FIGMA_TENANT_SLUG)
        ).scalar_one_or_none()
        if existing:
            print("  ♻️  Existing figma demo tenant found — replacing...")
            db.delete(existing)
            db.flush()

        # ── Tenant ────────────────────────────────────────────────────────────
        tenant = Tenant(
            id=uuid.uuid4(),
            name="Acme Logistics",
            slug=FIGMA_TENANT_SLUG,
            is_active=True,
        )
        db.add(tenant)
        db.flush()
        tid = tenant.id
        print(f"  ✅ Tenant: {tenant.name} ({tid})")

        for key, value in [
            ("business_vertical", "LAST_MILE_PARCEL"),
            ("city", "Bangalore"),
            ("capacity_unit", "WEIGHT_KG"),
        ]:
            db.add(TenantConfig(id=uuid.uuid4(), tenant_id=tid,
                                config_key=key, config_value=value))

        # ── Depots ────────────────────────────────────────────────────────────
        depot_main = Depot(
            id=uuid.uuid4(), tenant_id=tid,
            name="Koramangala Depot", city="Bangalore",
            latitude=12.9352, longitude=77.6245, pincode="560034",
        )
        depot_ec = Depot(
            id=uuid.uuid4(), tenant_id=tid,
            name="Electronic City Depot", city="Bangalore",
            latitude=12.8392, longitude=77.6774, pincode="560100",
        )
        db.add(depot_main)
        db.add(depot_ec)
        db.flush()
        depots = [depot_main, depot_ec]
        print(f"  ✅ 2 depots created")

        # ── Dispatcher user ───────────────────────────────────────────────────
        dispatcher = User(
            id=uuid.uuid4(), tenant_id=tid,
            email="riya@acme-logistics.com",
            hashed_password=hash_password("demo1234"),
            full_name="Riya Dispatcher",
            role="dispatcher",
            is_active=True,
        )
        db.add(dispatcher)
        print(f"  ✅ Dispatcher: {dispatcher.full_name}  (email: {dispatcher.email}  pw: demo1234)")

        # ── Drivers ───────────────────────────────────────────────────────────
        driver_records = []
        on_route_count = 0
        for i, (name, stops, status, shift_h) in enumerate(FIGMA_DRIVERS):
            depot = depots[0] if i < 10 else depots[1]
            driver = Driver(
                id=uuid.uuid4(), tenant_id=tid,
                full_name=name,
                phone=f"98{77000000 + i:08d}",
                email=f"driver{i+1}@acme-figma.com",
                license_class="LMV",
                default_shift_start=time(shift_h, 0),
                default_shift_end=time(18, 0),
                home_depot_id=depot.id,
                is_active=(status != "OFF_DUTY"),
            )
            db.add(driver)
            db.add(DriverShift(
                id=uuid.uuid4(), tenant_id=tid,
                driver_id=driver.id, shift_date=TODAY,
                shift_start=time(shift_h, 0), shift_end=time(18, 0),
                status="WORKING" if status != "OFF_DUTY" else "OFF",
                is_available=(status == "AVAILABLE"),
            ))
            driver_records.append((driver, stops, status))
        db.flush()

        # Create DriverAvailability records (status lives in separate table)
        _avail_map = {"AVAILABLE": "available", "ON_BREAK": "on_break", "OFF_DUTY": "off_duty"}
        for (driver, _, status) in driver_records:
            db.add(DriverAvailability(
                id=uuid.uuid4(), tenant_id=tid,
                driver_id=driver.id,
                date=TODAY,
                shift_start=driver.default_shift_start,
                shift_end=driver.default_shift_end,
                status=_avail_map.get(status, "available"),
                hours_worked_today=0.0,
            ))
        db.flush()
        print(f"  ✅ {len(driver_records)} drivers created")

        # ── Vehicles (statuses matching Figma) ────────────────────────────────
        vehicle_records = []
        for i, vstatus in enumerate(VEHICLE_STATUSES):
            depot = depots[0] if i < 10 else depots[1]
            v = Vehicle(
                id=uuid.uuid4(), tenant_id=tid,
                registration_number=f"KA-{i+1:02d}-FG-{1000+i}",
                vehicle_type="VAN",
                capacity_kg=500.0,
                capacity_units=100,
                home_depot_id=depot.id,
                is_active=True,
            )
            db.add(v)
            vehicle_records.append((v, vstatus))
        db.flush()

        # Create VehicleStatus records (status lives in separate table)
        # LOW_FUEL maps to "available" status with low fuel_level_pct
        _vstatus_map = {
            "IN_USE": "in_use", "AVAILABLE": "available",
            "MAINTENANCE": "maintenance", "LOW_FUEL": "available",
        }
        for (v, vstatus) in vehicle_records:
            db.add(VehicleStatus(
                id=uuid.uuid4(), tenant_id=tid,
                vehicle_id=v.id,
                status=_vstatus_map.get(vstatus, "available"),
                fuel_level_pct=12.0 if vstatus == "LOW_FUEL" else 75.0,
            ))
        db.flush()
        print(f"  ✅ 20 vehicles — 4 available, 14 in use, 1 maintenance, 1 low fuel")

        # ── Customers ─────────────────────────────────────────────────────────
        customers = []
        for i, area in enumerate(AREAS):
            c = Customer(
                id=uuid.uuid4(), tenant_id=tid,
                name=f"Customer {i+1} ({area.split(',')[0]})",
                phone=f"80{77000000 + i:08d}",
                address=f"{10 + i*5}, {area}, Bangalore",
                city="Bangalore",
                pincode=str(560001 + i),
                latitude=round(12.85 + (i % 10) * 0.02, 6),
                longitude=round(77.45 + (i % 10) * 0.03, 6),
                zone="SOUTH" if i < 10 else "NORTH",
            )
            db.add(c)
            customers.append(c)
        db.flush()
        print(f"  ✅ {len(customers)} customers created")

        # ── At-risk orders (created first so we have their IDs) ───────────────
        at_risk_order_records = []
        # Arjun Mehta is driver index 0 — assigned to at-risk orders
        arjun_driver_obj = driver_records[0][0]
        for idx, ar in enumerate(AT_RISK_ORDERS):
            c = Customer(
                id=uuid.uuid4(), tenant_id=tid,
                name=ar["ref"],
                phone="9900000000",
                address=ar["address"],
                city="Bangalore",
                pincode="560001",
                latitude=ar["lat"],
                longitude=ar["lng"],
                zone="SOUTH",
            )
            db.add(c)
            db.flush()

            order = Order(
                id=uuid.uuid4(), tenant_id=tid,
                external_ref=ar["ref"],
                customer_id=c.id,
                delivery_address=ar["address"],
                delivery_latitude=ar["lat"],
                delivery_longitude=ar["lng"],
                scheduled_date=datetime.combine(TODAY, time(8, 0)),
                time_window_start=ar["time_window_start"],
                time_window_end=ar["time_window_end"],
                weight_kg=5.0,
                quantity_units=1,
                priority=ar["priority"],
                status="IN_TRANSIT",
                assigned_driver_id=arjun_driver_obj.id,
                value=round(3000 + idx * 900, 2),
                notes=ar["delay_reason"],
            )
            db.add(order)
            at_risk_order_records.append(order)
        db.flush()
        print(f"  ✅ 3 at-risk orders created (ORD-2026-115, -119, -103 references)")

        # ── Bulk orders (to reach ~118 total) ────────────────────────────────
        # Status distribution across 115 bulk orders:
        #   0–29   → IN_TRANSIT (30) — actively delivering
        #   30–54  → DELIVERED  (25) — completed
        #   55–84  → ASSIGNED   (30) — dispatched but not started
        #   85–104 → DELIVERED  (20) — more completed
        #   105–109 → FAILED    (5)  — failed deliveries
        #   110–114 → PENDING   (5)  — unassigned

        def _bulk_status(i: int) -> str:
            if i < 30:   return "IN_TRANSIT"
            if i < 55:   return "DELIVERED"
            if i < 85:   return "ASSIGNED"
            if i < 105:  return "DELIVERED"
            if i < 110:  return "FAILED"
            return "PENDING"

        # Assign IN_TRANSIT and ASSIGNED orders to the 7 Figma drivers round-robin
        figma_driver_objs = [driver_records[j][0] for j in range(7)]

        bulk_orders = []
        target = 115  # 115 bulk + 3 at-risk = 118
        order_num_start = 1  # external_ref starts at ORD-2026-1
        for i in range(target):
            c = customers[i % len(customers)]
            tw_start = time(9 + (i % 3) * 3, 0)
            tw_end   = time(12 + (i % 3) * 3, 0)
            status   = _bulk_status(i)
            priority = "CRITICAL" if i % 25 == 0 else ("HIGH" if i % 10 == 0 else "NORMAL")
            # Assign a driver to non-PENDING and non-FAILED orders
            assigned_drv_id = None
            if status in ("IN_TRANSIT", "DELIVERED", "ASSIGNED"):
                assigned_drv_id = figma_driver_objs[i % len(figma_driver_objs)].id
            o = Order(
                id=uuid.uuid4(), tenant_id=tid,
                external_ref=f"ORD-2026-{order_num_start + i}",
                customer_id=c.id,
                delivery_address=c.address,
                delivery_latitude=c.latitude,
                delivery_longitude=c.longitude,
                scheduled_date=datetime.combine(TODAY, time(8, 0)),
                time_window_start=tw_start,
                time_window_end=tw_end,
                weight_kg=round(1.0 + (i % 20), 1),
                quantity_units=1 + (i % 5),
                priority=priority,
                status=status,
                assigned_driver_id=assigned_drv_id,
                value=round(800 + (i % 30) * 180, 2),
            )
            db.add(o)
            bulk_orders.append(o)
        db.flush()
        print(f"  ✅ {target + 3} total orders (118 as per Figma)")

        # ── Route Plan + Routes + Stops ───────────────────────────────────────
        plan = RoutePlan(
            id=uuid.uuid4(), tenant_id=tid,
            plan_date=TODAY,
            status="IN_PROGRESS",
            total_orders=118,
            assigned_orders=98,
            total_routes=7,
            planner_version="ortools_v2",
        )
        db.add(plan)
        db.flush()

        # Only first 7 drivers get routes (matching Figma Gantt)
        figma_gantt = [
            # (driver_index, stop_count, start_hour)
            (0, 8,  7),
            (1, 6,  7),
            (2, 1,  8),
            (3, 11, 7),
            (4, 4,  8),
            (5, 1,  8),
            (6, 7,  7),
        ]

        all_bulk_assigned = [o for o in bulk_orders if o.status in ("ASSIGNED", "IN_TRANSIT")]
        order_cursor = 0

        for driver_idx, num_stops, start_h in figma_gantt:
            driver_obj, _, _ = driver_records[driver_idx]
            vehicle, _ = vehicle_records[driver_idx]

            route = Route(
                id=uuid.uuid4(), tenant_id=tid,
                plan_id=plan.id,
                driver_id=driver_obj.id,
                vehicle_id=vehicle.id,
                status="STARTED",
                total_stops=num_stops,
                estimated_duration_minutes=num_stops * 50.0,
                estimated_distance_km=num_stops * 3.5,
            )
            db.add(route)
            db.flush()

            stop_times = _make_stop_times(start_h, num_stops)

            for seq, (st, et) in enumerate(stop_times):
                if order_cursor < len(all_bulk_assigned):
                    order_obj = all_bulk_assigned[order_cursor]
                    order_cursor += 1
                else:
                    break

                stop_status = "DELIVERED" if seq < num_stops // 2 else "IN_TRANSIT" if seq == num_stops // 2 else "ASSIGNED"
                rs = RouteStop(
                    id=uuid.uuid4(), tenant_id=tid,
                    route_id=route.id,
                    order_id=order_obj.id,
                    sequence=seq + 1,
                    status=stop_status,
                    estimated_arrival=st.isoformat(),
                    actual_arrival=st.isoformat() if stop_status == "DELIVERED" else None,
                )
                db.add(rs)
                # Keep order status consistent with stop status
                if stop_status == "DELIVERED":
                    order_obj.status = "DELIVERED"
                elif stop_status == "IN_TRANSIT":
                    order_obj.status = "IN_TRANSIT"
                # ASSIGNED stays as-is

        # Attach at-risk orders to Arjun Mehta's route
        arjun_route_q = db.execute(
            select(Route).where(Route.driver_id == arjun_driver_obj.id, Route.plan_id == plan.id)
        ).scalar_one_or_none()
        for i, ar_order in enumerate(at_risk_order_records):
            if arjun_route_q:
                overdue_time = datetime.combine(TODAY, time(10 + i, 0)) - timedelta(minutes=AT_RISK_ORDERS[i]["delay_minutes"])
                rs = RouteStop(
                    id=uuid.uuid4(), tenant_id=tid,
                    route_id=arjun_route_q.id,
                    order_id=ar_order.id,
                    sequence=20 + i,
                    status="IN_TRANSIT",
                    estimated_arrival=overdue_time.isoformat(),
                    actual_arrival=None,
                )
                db.add(rs)

        db.flush()
        print(f"  ✅ RoutePlan with 7 routes and Gantt-matching stop sequences created")

        db.commit()

        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🎨  Figma demo seed complete!")
        print()
        print("  Login credentials:")
        print("   Dispatcher  →  riya@acme-logistics.com  / demo1234")
        print()
        print("  Tenant slug: acme-logistics-figma")
        print("  To remove:   python scripts/unseed_figma_demo.py")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


def clean():
    db = SessionLocal()
    try:
        tenant = db.execute(
            select(Tenant).where(Tenant.slug == FIGMA_TENANT_SLUG)
        ).scalar_one_or_none()
        if not tenant:
            print("ℹ️  No figma demo tenant found — nothing to remove.")
            return
        db.delete(tenant)
        db.commit()
        print(f"🗑️  Figma demo tenant '{FIGMA_TENANT_SLUG}' and all its data removed.")
    except Exception as e:
        db.rollback()
        print(f"❌ Clean failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Figma demo seed for FleetOpsX dashboard redesign")
    parser.add_argument("--clean", action="store_true", help="Remove figma demo data only")
    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        seed()
