# Synthetic Data Generator (Bangalore) – Technical Specification

> **For AI Coding Assistants:** This is a standalone script, not part of the FastAPI app. It seeds realistic fleet data for Bangalore into the database for demos and testing. Run it after all domain tables are created.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Synthetic Data Generator |
| **Epic** | P1-E7 |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Author** | Antigravity |
| **Depends On** | P1-E3 (all domain tables must exist) |
| **Implementation Branch** | feat/p1-e7-synthetic-data |

---

## Executive Summary

**Purpose:** Generate realistic synthetic fleet data for Bangalore — 2 depots, 20 drivers, 20 vehicles, 50 customers, and 100 orders across 3 days. Used for demo, investor presentation, and local testing when no real data is available.

### Key Deliverables

| Component | File | Status |
|-----------|------|--------|
| Data generator script | `scripts/seed_data.py` | ⬜ |
| Bangalore coordinates | embedded in script | ⬜ |
| CLI with options | argparse | ⬜ |

---

## 2. Data to Generate

### Tenant
- 1 demo tenant: name = "FleetOpsX Demo", slug = "fleetopsx-demo"

### Depots (2)
| Name | Area | Lat | Lng |
|------|------|-----|-----|
| Koramangala Depot | South Bangalore | 12.9352 | 77.6245 |
| Whitefield Depot | East Bangalore | 12.9698 | 77.7499 |

### Drivers (20)
- 10 per depot
- Random Indian names
- Shift: 08:00–18:00 default
- License class: alternating LMV / TRANS
- All active

### Vehicles (20)
- 10 per depot (mix of VAN and BIKE)
- VAN: capacity_kg=500, capacity_units=100
- BIKE: capacity_kg=30, capacity_units=10
- All active

### Customers (50)
- Random addresses spread across Bangalore bounding box:
  - Lat range: 12.85 – 13.05
  - Lng range: 77.45 – 77.75
- Zones: NORTH, SOUTH, EAST, WEST (random)

### Orders (100)
- ~33 per day for 3 consecutive days starting from `--start-date`
- Mix of priorities: 60% NORMAL, 25% HIGH, 10% LOW, 5% CRITICAL
- Random time windows: morning (09:00–12:00), afternoon (12:00–15:00), evening (15:00–18:00)
- All status = PENDING
- delivery lat/lng = customer lat/lng

---

## 3. Script Specification

### File: `scripts/seed_data.py`

```python
#!/usr/bin/env python3
"""
FleetOpsX Synthetic Data Generator – Bangalore Demo
Usage:
  python scripts/seed_data.py
  python scripts/seed_data.py --start-date 2026-01-15 --days 3
  python scripts/seed_data.py --clean  (drops and re-seeds)
"""
import argparse
import random
import uuid
import sys
import os
from datetime import date, time, timedelta, datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.models import (
    Tenant, TenantConfig, Depot, Driver, Vehicle, Customer, Order, DriverShift
)

# ── Constants ──────────────────────────────────────────────────────────────────

BENGALURU_BBOX = {
    "lat_min": 12.85, "lat_max": 13.05,
    "lng_min": 77.45, "lng_max": 77.75,
}

DEPOT_DATA = [
    {"name": "Koramangala Depot", "city": "Bangalore", "latitude": 12.9352, "longitude": 77.6245, "pincode": "560034"},
    {"name": "Whitefield Depot",  "city": "Bangalore", "latitude": 12.9698, "longitude": 77.7499, "pincode": "560066"},
]

DRIVER_NAMES = [
    "Ravi Kumar", "Suresh Babu", "Arjun Sharma", "Kiran Reddy", "Mahesh Nair",
    "Pradeep Singh", "Rajesh Patel", "Vikram Rao", "Anand Pillai", "Santosh Joshi",
    "Deepak Verma", "Mohan Das", "Ramesh Iyer", "Sunil Hegde", "Vinod Shetty",
    "Arun Kumar", "Ganesh Murugan", "Harish Bhat", "Sanjay Gowda", "Naresh Tiwari",
]

CUSTOMER_AREAS = [
    "Indiranagar", "Koramangala", "HSR Layout", "Whitefield", "Jayanagar",
    "JP Nagar", "Marathahalli", "Electronic City", "Bellandur", "Sarjapur",
    "BTM Layout", "Hebbal", "Yelahanka", "Banashankari", "Malleshwaram",
]

PRIORITIES = (
    ["NORMAL"] * 60 + ["HIGH"] * 25 + ["LOW"] * 10 + ["CRITICAL"] * 5
)

VEHICLE_TYPES = ["VAN", "VAN", "VAN", "BIKE", "BIKE"]

TIME_WINDOWS = [
    (time(9, 0), time(12, 0)),
    (time(12, 0), time(15, 0)),
    (time(15, 0), time(18, 0)),
]


def rand_lat(): return round(random.uniform(BENGALURU_BBOX["lat_min"], BENGALURU_BBOX["lat_max"]), 6)
def rand_lng(): return round(random.uniform(BENGALURU_BBOX["lng_min"], BENGALURU_BBOX["lng_max"]), 6)


def seed(start_date: date, num_days: int = 3):
    db = SessionLocal()
    try:
        print("🌱 Seeding FleetOpsX demo data for Bangalore...")

        # ── Tenant ────────────────────────────────────────────────────────────
        tenant = Tenant(
            id=uuid.uuid4(),
            name="FleetOpsX Demo",
            slug="fleetopsx-demo",
            is_active=True,
        )
        db.add(tenant)
        db.flush()
        print(f"  ✅ Tenant created: {tenant.id}")

        # Config
        for key, value in [
            ("business_vertical", "LAST_MILE_PARCEL"),
            ("capacity_unit", "WEIGHT_KG"),
            ("time_window_style", "SLOTS"),
        ]:
            db.add(TenantConfig(
                id=uuid.uuid4(), tenant_id=tenant.id,
                config_key=key, config_value=value,
            ))

        # ── Depots ────────────────────────────────────────────────────────────
        depots = []
        for d in DEPOT_DATA:
            depot = Depot(id=uuid.uuid4(), tenant_id=tenant.id, **d)
            db.add(depot)
            depots.append(depot)
        db.flush()
        print(f"  ✅ {len(depots)} depots created")

        # ── Drivers ───────────────────────────────────────────────────────────
        drivers = []
        for i, name in enumerate(DRIVER_NAMES):
            depot = depots[i // 10]
            driver = Driver(
                id=uuid.uuid4(), tenant_id=tenant.id,
                full_name=name,
                phone=f"98{random.randint(10000000, 99999999)}",
                license_class="LMV" if i % 2 == 0 else "TRANS",
                default_shift_start=time(8, 0),
                default_shift_end=time(18, 0),
                home_depot_id=depot.id,
                is_active=True,
            )
            db.add(driver)
            drivers.append(driver)

            # Add working shift for each day
            for day_offset in range(num_days):
                shift_date = start_date + timedelta(days=day_offset)
                db.add(DriverShift(
                    id=uuid.uuid4(), tenant_id=tenant.id,
                    driver_id=driver.id, shift_date=shift_date,
                    shift_start=time(8, 0), shift_end=time(18, 0),
                    status="WORKING", is_available=True,
                ))
        db.flush()
        print(f"  ✅ {len(drivers)} drivers created with shifts")

        # ── Vehicles ──────────────────────────────────────────────────────────
        vehicles = []
        for i in range(20):
            depot = depots[i // 10]
            vtype = random.choice(VEHICLE_TYPES)
            vehicle = Vehicle(
                id=uuid.uuid4(), tenant_id=tenant.id,
                registration_number=f"KA-0{i+1:02d}-AB-{random.randint(1000,9999)}",
                vehicle_type=vtype,
                capacity_kg=500.0 if vtype == "VAN" else 30.0,
                capacity_units=100 if vtype == "VAN" else 10,
                home_depot_id=depot.id,
                is_active=True,
            )
            db.add(vehicle)
            vehicles.append(vehicle)
        db.flush()
        print(f"  ✅ {len(vehicles)} vehicles created")

        # ── Customers ─────────────────────────────────────────────────────────
        customers = []
        for i in range(50):
            area = random.choice(CUSTOMER_AREAS)
            zone = random.choice(["NORTH", "SOUTH", "EAST", "WEST"])
            customer = Customer(
                id=uuid.uuid4(), tenant_id=tenant.id,
                name=f"Customer {i+1} ({area})",
                phone=f"80{random.randint(10000000, 99999999)}",
                address=f"{random.randint(1,200)}, {area}, Bangalore",
                city="Bangalore",
                pincode=str(random.randint(560001, 560099)),
                latitude=rand_lat(), longitude=rand_lng(),
                zone=zone,
            )
            db.add(customer)
            customers.append(customer)
        db.flush()
        print(f"  ✅ {len(customers)} customers created")

        # ── Orders ────────────────────────────────────────────────────────────
        order_count = 0
        for day_offset in range(num_days):
            order_date = start_date + timedelta(days=day_offset)
            for _ in range(33):
                customer = random.choice(customers)
                tw = random.choice(TIME_WINDOWS)
                order = Order(
                    id=uuid.uuid4(), tenant_id=tenant.id,
                    customer_id=customer.id,
                    delivery_address=customer.address,
                    delivery_latitude=customer.latitude,
                    delivery_longitude=customer.longitude,
                    scheduled_date=datetime.combine(order_date, time(9, 0)),
                    time_window_start=tw[0],
                    time_window_end=tw[1],
                    weight_kg=round(random.uniform(0.5, 20.0), 2),
                    quantity_units=random.randint(1, 10),
                    priority=random.choice(PRIORITIES),
                    status="PENDING",
                )
                db.add(order)
                order_count += 1
        db.commit()
        print(f"  ✅ {order_count} orders created across {num_days} days")

        print(f"\n🎉 Done! Tenant ID: {tenant.id}")
        print(f"   Use this as X-Tenant-ID header in all API calls.")
        return str(tenant.id)

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


def clean():
    db = SessionLocal()
    try:
        print("🗑️  Cleaning demo data...")
        tenant = db.execute(
            __import__("sqlalchemy").select(Tenant).where(Tenant.slug == "fleetopsx-demo")
        ).scalar_one_or_none()
        if tenant:
            db.delete(tenant)
            db.commit()
            print("  ✅ Demo tenant and all related data deleted")
        else:
            print("  ℹ️  No demo tenant found")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FleetOpsX Demo Data Seeder")
    parser.add_argument("--start-date", default=str(date.today()), help="Start date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=3, help="Number of days to generate orders for")
    parser.add_argument("--clean", action="store_true", help="Delete demo data and exit")
    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        start = date.fromisoformat(args.start_date)
        seed(start_date=start, num_days=args.days)
```

---

## 4. File Checklist

| Action | File | Status |
|--------|------|--------|
| CREATE | `scripts/seed_data.py` | ⬜ |
| CREATE | `scripts/__init__.py` (empty) | ⬜ |

---

## 5. Verification

```bash
# Seed demo data
python scripts/seed_data.py --start-date 2026-01-15 --days 3

# Expected output:
# 🌱 Seeding FleetOpsX demo data for Bangalore...
#   ✅ Tenant created: <uuid>
#   ✅ 2 depots created
#   ✅ 20 drivers created with shifts
#   ✅ 20 vehicles created
#   ✅ 50 customers created
#   ✅ 99 orders created across 3 days
# 🎉 Done! Tenant ID: <uuid>

# Verify via API
TENANT_ID="<uuid-from-above>"
curl -s http://localhost:8000/api/v1/drivers/ -H "X-Tenant-ID: $TENANT_ID" | jq length
# Expected: 20

curl -s "http://localhost:8000/api/v1/orders/?plan_date=2026-01-15" \
  -H "X-Tenant-ID: $TENANT_ID" | jq length
# Expected: ~33

# Now run the planner
curl -s -X POST "http://localhost:8000/api/v1/plan/day?plan_date=2026-01-15" \
  -H "X-Tenant-ID: $TENANT_ID" | jq .

# Clean up when done
python scripts/seed_data.py --clean
```

---

**Document Status:** Not Started  
**Last Updated:** 2026-03-29  
**Implementation Status:** ⬜ Not Started
