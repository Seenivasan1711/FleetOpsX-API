#!/usr/bin/env python3
"""
FleetOpsX Synthetic Data Generator – Bangalore Demo

Usage:
  python scripts/seed_data.py
  python scripts/seed_data.py --start-date 2026-01-15 --days 3
  python scripts/seed_data.py --clean   (drops and re-seeds)
"""
import argparse
import random
import uuid
import sys
import os
from datetime import date, time, timedelta, datetime
from sqlalchemy import select

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    Tenant, TenantConfig, Depot, Driver, DriverShift,
    Vehicle, Customer, Order, User,
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

PRIORITIES = ["NORMAL"] * 60 + ["HIGH"] * 25 + ["LOW"] * 10 + ["CRITICAL"] * 5

VEHICLE_TYPES = ["VAN", "VAN", "VAN", "BIKE", "BIKE"]

TIME_WINDOWS = [
    (time(9, 0),  time(12, 0)),
    (time(12, 0), time(15, 0)),
    (time(15, 0), time(18, 0)),
]


def rand_lat():
    return round(random.uniform(BENGALURU_BBOX["lat_min"], BENGALURU_BBOX["lat_max"]), 6)

def rand_lng():
    return round(random.uniform(BENGALURU_BBOX["lng_min"], BENGALURU_BBOX["lng_max"]), 6)


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
                email=f"driver{i+1}@demo.com",
                license_class="LMV" if i % 2 == 0 else "TRANS",
                default_shift_start=time(8, 0),
                default_shift_end=time(18, 0),
                home_depot_id=depot.id,
                is_active=True,
            )
            db.add(driver)
            drivers.append(driver)

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
                registration_number=f"KA-0{i+1:02d}-AB-{random.randint(1000, 9999)}",
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
                address=f"{random.randint(1, 200)}, {area}, Bangalore",
                city="Bangalore",
                pincode=str(random.randint(560001, 560099)),
                latitude=rand_lat(),
                longitude=rand_lng(),
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

        # ── Demo Users (P1-AUTH-9) ─────────────────────────────────────────────
        dispatcher_user = User(
            id=uuid.uuid4(), tenant_id=tenant.id,
            email="dispatcher@demo.com",
            hashed_password=hash_password("demo1234"),
            full_name="Demo Dispatcher",
            role="dispatcher",
            is_active=True,
        )
        driver_user = User(
            id=uuid.uuid4(), tenant_id=tenant.id,
            email="driver@demo.com",
            hashed_password=hash_password("demo1234"),
            full_name="Demo Driver",
            role="driver",
            is_active=True,
        )
        db.add(dispatcher_user)
        db.add(driver_user)

        # ── Superadmin user (P5-E0) ────────────────────────────────────────────
        existing_superadmin = db.execute(
            select(User).where(User.email == "superadmin@fleetopsx.com")
        ).scalar_one_or_none()
        if not existing_superadmin:
            superadmin_user = User(
                id=uuid.uuid4(),
                tenant_id=None,
                email="superadmin@fleetopsx.com",
                hashed_password=hash_password("admin1234"),
                full_name="Platform Admin",
                role="superadmin",
                is_active=True,
            )
            db.add(superadmin_user)

        # Link the first driver record to driver@demo.com so /driver/my-stops works
        if drivers:
            drivers[0].email = "driver@demo.com"
            print(f"  ✅ Driver '{drivers[0].full_name}' linked to driver@demo.com")

        db.commit()
        print(f"  ✅ {order_count} orders created across {num_days} days")
        print(f"  ✅ Demo users created")
        print(f"     Superadmin:  superadmin@fleetopsx.com / admin1234")
        print(f"     Dispatcher:  dispatcher@demo.com / demo1234")
        print(f"     Driver:      driver@demo.com / demo1234")

        print(f"\n🎉 Done! Tenant ID: {tenant.id}")
        print(f"   Start date: {start_date}  |  Days: {num_days}")
        print(f"\n   Login at http://localhost:5173/login")
        print(f"   API docs at http://localhost:8000/docs")
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
            select(Tenant).where(Tenant.slug == "fleetopsx-demo")
        ).scalar_one_or_none()
        if tenant:
            db.delete(tenant)
            db.commit()
            print("  ✅ Demo tenant and all related data deleted (CASCADE)")
        else:
            print("  ℹ️  No demo tenant found — nothing to clean")
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
