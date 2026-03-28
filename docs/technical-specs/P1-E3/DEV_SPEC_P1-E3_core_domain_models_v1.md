# Core Domain Models & APIs – Technical Specification

> **For AI Coding Assistants:** Implement checkpoints in order. Do not skip verification steps. Every model MUST use `TenantMixin` and `TimestampMixin`. Every router MUST use `Depends(require_tenant_id)`. Business logic MUST live in `app/services/`, not in routers.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Core Domain Models & APIs |
| **Epic** | P1-E3 |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Author** | Antigravity |
| **Reference** | Blueprint Section 7 – Canonical Data Model |
| **Depends On** | P1-E2 (Multi-Tenancy) – must be complete first |
| **Implementation Branch** | feat/p1-e3-domain-models |

---

## Executive Summary

**Purpose:** Build all core domain models (DB tables), Pydantic schemas (DTOs), service layer (business logic), and API routers for the 5 primary fleet entities: Depots, Drivers, Vehicles, Customers, and Orders. Also includes DriverShift, RoutePlan, Route, RouteStop, DeliveryEvent, and User. This is the data backbone that the Planner (P1-E4) and Dashboard (P1-E5) will operate on.

### Key Deliverables

| Component | Files | Priority | Status |
|-----------|-------|----------|--------|
| Domain models (9 files) | `app/models/*.py` | P0 | ⬜ |
| Pydantic schemas (7 files) | `app/schemas/*.py` | P0 | ⬜ |
| Service layer (5 files) | `app/services/*.py` | P0 | ⬜ |
| API routers (5 files) | `app/api/v1/*.py` | P0 | ⬜ |
| Alembic migration | `alembic/versions/` | P0 | ⬜ |
| Auth module | `app/api/v1/auth.py` | P1 | ⬜ |

### Success Criteria

- [ ] `alembic upgrade head` creates all 13 domain tables
- [ ] CRUD endpoints for all 5 core entities return correct responses
- [ ] All endpoints return HTTP 400 without `X-Tenant-ID` header
- [ ] Data from one tenant is never returned to another tenant
- [ ] Swagger docs at `/docs` show all routes grouped by tag

### Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| P1-E2 fully implemented | ⬜ Required | `require_tenant_id` dep must exist |
| Alembic migration from P1-E2 applied | ⬜ Required | `tenants` table must exist |

---

## 1. Goals & Objectives

### Primary Goals

1. **Complete canonical data model:** All tables match blueprint Section 7 exactly
2. **Tenant-scoped queries:** Every service function filters by `tenant_id` — no cross-tenant leaks
3. **Layered architecture:** Router → Service → Model. No DB logic in routers.

### Non-Goals

- Auth/JWT (P1-E3-S6, separate ticket — User model created, endpoints not yet)
- Planner logic (P1-E4)
- Real-time tracking (P2-E3)
- Notifications (P2-E4)

---

## 2. Domain Models

All models follow this pattern:

```python
class MyModel(Base, TimestampMixin, TenantMixin):
    __tablename__ = "my_models"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ... fields
```

---

### Model 1: `app/models/user.py`

```python
import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class User(Base, TimestampMixin, TenantMixin):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="dispatcher")
    # Roles: superadmin | admin | dispatcher | driver | readonly
    is_active = Column(Boolean, default=True)
```

---

### Model 2: `app/models/depot.py`

```python
import uuid
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class Depot(Base, TimestampMixin, TenantMixin):
    __tablename__ = "depots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="India")
    pincode = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    drivers = relationship("Driver", back_populates="home_depot")
    vehicles = relationship("Vehicle", back_populates="home_depot")
```

---

### Model 3: `app/models/driver.py`

```python
import uuid
from sqlalchemy import Column, String, Float, Boolean, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class Driver(Base, TimestampMixin, TenantMixin):
    __tablename__ = "drivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    license_number = Column(String(100), nullable=True)
    license_class = Column(String(50), nullable=True)
    # LMV | HMV | TRANS
    default_shift_start = Column(Time, nullable=True)
    default_shift_end = Column(Time, nullable=True)
    home_depot_id = Column(
        UUID(as_uuid=True), ForeignKey("depots.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    is_active = Column(Boolean, default=True)

    home_depot = relationship("Depot", back_populates="drivers")
    shifts = relationship("DriverShift", back_populates="driver", cascade="all, delete-orphan")
```

---

### Model 4: `app/models/driver_shift.py`

```python
import uuid
from sqlalchemy import Column, Date, Time, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class DriverShift(Base, TimestampMixin, TenantMixin):
    __tablename__ = "driver_shifts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_id = Column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    shift_date = Column(Date, nullable=False, index=True)
    shift_start = Column(Time, nullable=False)
    shift_end = Column(Time, nullable=False)
    status = Column(String(50), nullable=False, default="WORKING")
    # WORKING | LEAVE | SICK | HOLIDAY
    is_available = Column(Boolean, default=True)

    driver = relationship("Driver", back_populates="shifts")
```

---

### Model 5: `app/models/vehicle.py`

```python
import uuid
from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class Vehicle(Base, TimestampMixin, TenantMixin):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_number = Column(String(50), nullable=False, index=True)
    vehicle_type = Column(String(50), nullable=False, default="VAN")
    # BIKE | AUTO | VAN | TRUCK_SMALL | TRUCK_LARGE
    capacity_kg = Column(Float, nullable=True)
    capacity_volume_liters = Column(Float, nullable=True)
    capacity_units = Column(Integer, nullable=True)
    is_refrigerated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    home_depot_id = Column(
        UUID(as_uuid=True), ForeignKey("depots.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    home_depot = relationship("Depot", back_populates="vehicles")
```

---

### Model 6: `app/models/customer.py`

```python
import uuid
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class Customer(Base, TimestampMixin, TenantMixin):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    pincode = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    zone = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="customer")
```

---

### Model 7: `app/models/order.py`

```python
import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, Time, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class Order(Base, TimestampMixin, TenantMixin):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_ref = Column(String(255), nullable=True, index=True)
    customer_id = Column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    pickup_address = Column(String(500), nullable=True)
    pickup_latitude = Column(Float, nullable=True)
    pickup_longitude = Column(Float, nullable=True)
    delivery_address = Column(String(500), nullable=False)
    delivery_latitude = Column(Float, nullable=True)
    delivery_longitude = Column(Float, nullable=True)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    time_window_start = Column(Time, nullable=True)
    time_window_end = Column(Time, nullable=True)
    weight_kg = Column(Float, nullable=True)
    volume_liters = Column(Float, nullable=True)
    quantity_units = Column(Integer, nullable=True)
    requires_refrigeration = Column(Boolean, default=False)
    priority = Column(String(20), nullable=False, default="NORMAL")
    # LOW | NORMAL | HIGH | CRITICAL
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    # PENDING | ASSIGNED | IN_TRANSIT | DELIVERED | FAILED | CANCELLED
    notes = Column(Text, nullable=True)
    assigned_driver_id = Column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    assigned_vehicle_id = Column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    customer = relationship("Customer", back_populates="orders")
    assigned_driver = relationship("Driver", foreign_keys=[assigned_driver_id])
    assigned_vehicle = relationship("Vehicle", foreign_keys=[assigned_vehicle_id])
    route_stop = relationship("RouteStop", back_populates="order", uselist=False)
```

---

### Model 8: `app/models/route_plan.py`

Three classes in one file: `RoutePlan`, `Route`, `RouteStop`, `DeliveryEvent`

```python
import uuid
from sqlalchemy import Column, Date, String, Integer, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, TenantMixin

class RoutePlan(Base, TimestampMixin, TenantMixin):
    __tablename__ = "route_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="DRAFT")
    # DRAFT | PUBLISHED | IN_PROGRESS | COMPLETED
    total_orders = Column(Integer, default=0)
    assigned_orders = Column(Integer, default=0)
    total_routes = Column(Integer, default=0)
    planner_version = Column(String(50), nullable=True, default="rule_based_v1")

    routes = relationship("Route", back_populates="plan", cascade="all, delete-orphan")


class Route(Base, TimestampMixin, TenantMixin):
    __tablename__ = "routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("route_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="PLANNED")
    # PLANNED | STARTED | COMPLETED | CANCELLED
    total_stops = Column(Integer, default=0)
    estimated_duration_minutes = Column(Float, nullable=True)
    estimated_distance_km = Column(Float, nullable=True)

    plan = relationship("RoutePlan", back_populates="routes")
    driver = relationship("Driver")
    vehicle = relationship("Vehicle")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence")


class RouteStop(Base, TimestampMixin, TenantMixin):
    __tablename__ = "route_stops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    # PENDING | ARRIVED | DELIVERED | FAILED | SKIPPED
    estimated_arrival = Column(String(50), nullable=True)
    actual_arrival = Column(String(50), nullable=True)

    route = relationship("Route", back_populates="stops")
    order = relationship("Order", back_populates="route_stop")


class DeliveryEvent(Base, TimestampMixin, TenantMixin):
    __tablename__ = "delivery_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_stop_id = Column(UUID(as_uuid=True), ForeignKey("route_stops.id", ondelete="CASCADE"), nullable=True, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # ASSIGNED | STARTED | ARRIVED | DELIVERED | FAILED | DELAYED | CANCELLED | NOTE
    description = Column(String(500), nullable=True)
    recorded_by = Column(String(100), nullable=True)
    # "driver" | "system" | "dispatcher" | user_id
```

---

### Update `app/models/__init__.py`

```python
from app.models.base import Base, TimestampMixin, TenantMixin
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User
from app.models.depot import Depot
from app.models.driver import Driver
from app.models.driver_shift import DriverShift
from app.models.vehicle import Vehicle
from app.models.customer import Customer
from app.models.order import Order
from app.models.route_plan import RoutePlan, Route, RouteStop, DeliveryEvent

__all__ = [
    "Base", "TimestampMixin", "TenantMixin",
    "Tenant", "TenantConfig",
    "User",
    "Depot",
    "Driver", "DriverShift",
    "Vehicle",
    "Customer",
    "Order",
    "RoutePlan", "Route", "RouteStop", "DeliveryEvent",
]
```

---

## 3. Pydantic Schemas

Create `app/schemas/` folder. Pattern for every entity:

```python
class EntityBase(BaseModel):         # shared fields
class EntityCreate(EntityBase):      # POST body
class EntityUpdate(BaseModel):       # PATCH body – all Optional
class EntityResponse(EntityBase):    # GET response – includes id, tenant_id, timestamps
    class Config:
        from_attributes = True
```

### `app/schemas/__init__.py`
```python
# schemas package
```

### `app/schemas/common.py`
```python
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

### `app/schemas/depot.py`
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class DepotBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool = True

class DepotCreate(DepotBase):
    pass

class DepotUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[bool] = None

class DepotResponse(DepotBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

### `app/schemas/driver.py`
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime, time

class DriverBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    license_class: Optional[str] = None
    default_shift_start: Optional[time] = None
    default_shift_end: Optional[time] = None
    home_depot_id: Optional[UUID] = None
    is_active: bool = True

class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    home_depot_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    default_shift_start: Optional[time] = None
    default_shift_end: Optional[time] = None

class DriverResponse(DriverBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

### `app/schemas/vehicle.py`
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class VehicleBase(BaseModel):
    registration_number: str
    vehicle_type: str = "VAN"
    capacity_kg: Optional[float] = None
    capacity_volume_liters: Optional[float] = None
    capacity_units: Optional[int] = None
    is_refrigerated: bool = False
    home_depot_id: Optional[UUID] = None
    is_active: bool = True

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    registration_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    capacity_kg: Optional[float] = None
    is_refrigerated: Optional[bool] = None
    home_depot_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class VehicleResponse(VehicleBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

### `app/schemas/customer.py`
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone: Optional[str] = None
    is_active: bool = True

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

### `app/schemas/order.py`
```python
from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime, time

class OrderBase(BaseModel):
    external_ref: Optional[str] = None
    customer_id: Optional[UUID] = None
    pickup_address: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    delivery_address: str
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    scheduled_date: datetime
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None
    weight_kg: Optional[float] = None
    volume_liters: Optional[float] = None
    quantity_units: Optional[int] = None
    requires_refrigeration: bool = False
    priority: str = "NORMAL"
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    delivery_address: Optional[str] = None
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    scheduled_date: Optional[datetime] = None
    time_window_start: Optional[time] = None
    time_window_end: Optional[time] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None

class OrderResponse(OrderBase):
    id: UUID
    tenant_id: UUID
    status: str
    assigned_driver_id: Optional[UUID] = None
    assigned_vehicle_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

---

## 4. Service Layer

All services follow this pattern:

```python
def create_X(db: Session, tenant_id: str, data: XCreate) -> X:
    obj = X(**data.model_dump(), tenant_id=UUID(tenant_id))
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def get_X(db: Session, tenant_id: str, x_id: UUID) -> Optional[X]:
    return db.execute(
        select(X).where(X.id == x_id, X.tenant_id == UUID(tenant_id))
    ).scalar_one_or_none()

def list_Xs(db: Session, tenant_id: str, ...) -> list[X]:
    q = select(X).where(X.tenant_id == UUID(tenant_id))
    # add filters...
    return list(db.execute(q).scalars().all())

def update_X(db: Session, tenant_id: str, x_id: UUID, data: XUpdate) -> Optional[X]:
    obj = get_X(db, tenant_id, x_id)
    if not obj: return None
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    db.commit(); db.refresh(obj)
    return obj

def delete_X(db: Session, tenant_id: str, x_id: UUID) -> bool:
    obj = get_X(db, tenant_id, x_id)
    if not obj: return False
    db.delete(obj); db.commit()
    return True
```

**Create these 5 service files following the pattern above:**

| File | Model | List filters |
|------|-------|-------------|
| `app/services/depot_service.py` | Depot | `active_only: bool` |
| `app/services/driver_service.py` | Driver | `active_only: bool`, `depot_id: Optional[UUID]` |
| `app/services/vehicle_service.py` | Vehicle | `active_only: bool`, `depot_id: Optional[UUID]` |
| `app/services/customer_service.py` | Customer | `active_only: bool`, `zone: Optional[str]` |
| `app/services/order_service.py` | Order | `plan_date: Optional[date]`, `status: Optional[str]`, `unassigned_only: bool` |

Also create `app/services/__init__.py` (empty).

---

## 5. API Routers

All routers follow this pattern:

```python
router = APIRouter(prefix="/entity", tags=["Entity"])

@router.post("/", response_model=EntityResponse, status_code=201)
def create(data: EntityCreate, db=Depends(get_db), tenant_id=Depends(require_tenant_id)):
    return entity_service.create_entity(db, tenant_id, data)

@router.get("/", response_model=List[EntityResponse])
def list_all(db=Depends(get_db), tenant_id=Depends(require_tenant_id)):
    return entity_service.list_entities(db, tenant_id)

@router.get("/{id}", response_model=EntityResponse)
def get_one(id: UUID, db=Depends(get_db), tenant_id=Depends(require_tenant_id)):
    obj = entity_service.get_entity(db, tenant_id, id)
    if not obj: raise HTTPException(404, "Not found")
    return obj

@router.patch("/{id}", response_model=EntityResponse)
def update(id: UUID, data: EntityUpdate, db=Depends(get_db), tenant_id=Depends(require_tenant_id)):
    obj = entity_service.update_entity(db, tenant_id, id, data)
    if not obj: raise HTTPException(404, "Not found")
    return obj

@router.delete("/{id}", status_code=204)
def delete(id: UUID, db=Depends(get_db), tenant_id=Depends(require_tenant_id)):
    if not entity_service.delete_entity(db, tenant_id, id):
        raise HTTPException(404, "Not found")
```

**Create these 5 router files:**

| File | Prefix | Tag |
|------|--------|-----|
| `app/api/v1/depots.py` | `/depots` | Depots |
| `app/api/v1/drivers.py` | `/drivers` | Drivers |
| `app/api/v1/vehicles.py` | `/vehicles` | Vehicles |
| `app/api/v1/customers.py` | `/customers` | Customers |
| `app/api/v1/orders.py` | `/orders` | Orders |

Also create `app/api/v1/__init__.py` (empty).

### Update `app/api/router.py` to include all routers:

```python
from fastapi import APIRouter
from app.api import health
from app.api.v1 import depots, drivers, vehicles, customers, orders

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(depots.router, prefix="/api/v1")
api_router.include_router(drivers.router, prefix="/api/v1")
api_router.include_router(vehicles.router, prefix="/api/v1")
api_router.include_router(customers.router, prefix="/api/v1")
api_router.include_router(orders.router, prefix="/api/v1")
```

---

## 6. Alembic Migration

After creating all models and updating `__init__.py`, run:

```bash
alembic revision --autogenerate -m "P1_E3_core_domain_models"
alembic upgrade head
```

### Expected tables after migration:
`tenants`, `tenant_configs`, `users`, `depots`, `drivers`, `driver_shifts`, `vehicles`, `customers`, `orders`, `route_plans`, `routes`, `route_stops`, `delivery_events`

---

## 7. File Checklist

| Action | File | Status |
|--------|------|--------|
| CREATE | `app/models/user.py` | ⬜ |
| CREATE | `app/models/depot.py` | ⬜ |
| CREATE | `app/models/driver.py` | ⬜ |
| CREATE | `app/models/driver_shift.py` | ⬜ |
| CREATE | `app/models/vehicle.py` | ⬜ |
| CREATE | `app/models/customer.py` | ⬜ |
| CREATE | `app/models/order.py` | ⬜ |
| CREATE | `app/models/route_plan.py` | ⬜ |
| MODIFY | `app/models/__init__.py` | ⬜ |
| CREATE | `app/schemas/__init__.py` | ⬜ |
| CREATE | `app/schemas/common.py` | ⬜ |
| CREATE | `app/schemas/depot.py` | ⬜ |
| CREATE | `app/schemas/driver.py` | ⬜ |
| CREATE | `app/schemas/vehicle.py` | ⬜ |
| CREATE | `app/schemas/customer.py` | ⬜ |
| CREATE | `app/schemas/order.py` | ⬜ |
| CREATE | `app/services/__init__.py` | ⬜ |
| CREATE | `app/services/depot_service.py` | ⬜ |
| CREATE | `app/services/driver_service.py` | ⬜ |
| CREATE | `app/services/vehicle_service.py` | ⬜ |
| CREATE | `app/services/customer_service.py` | ⬜ |
| CREATE | `app/services/order_service.py` | ⬜ |
| CREATE | `app/api/v1/__init__.py` | ⬜ |
| CREATE | `app/api/v1/depots.py` | ⬜ |
| CREATE | `app/api/v1/drivers.py` | ⬜ |
| CREATE | `app/api/v1/vehicles.py` | ⬜ |
| CREATE | `app/api/v1/customers.py` | ⬜ |
| CREATE | `app/api/v1/orders.py` | ⬜ |
| MODIFY | `app/api/router.py` | ⬜ |
| RUN | `alembic revision --autogenerate -m "P1_E3_core_domain_models"` | ⬜ |
| RUN | `alembic upgrade head` | ⬜ |

---

## 8. Verification

```bash
# All 13 tables exist
docker exec fleetopsx-db psql -U fleetuser -d fleetopsx -c "\dt"

# Swagger shows all routes
open http://localhost:8000/docs

# Create a test tenant first (direct DB insert for now)
docker exec fleetopsx-db psql -U fleetuser -d fleetopsx \
  -c "INSERT INTO tenants (id, name, slug) VALUES (gen_random_uuid(), 'Test Tenant', 'test-tenant') RETURNING id;"
# Save the returned UUID as TENANT_ID

# Test depot CRUD
TENANT_ID="<uuid-from-above>"

curl -s -X POST http://localhost:8000/api/v1/depots/ \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"name": "Bangalore Central Depot", "city": "Bangalore", "latitude": 12.9716, "longitude": 77.5946}' | jq .

curl -s http://localhost:8000/api/v1/depots/ \
  -H "X-Tenant-ID: $TENANT_ID" | jq .
```

---

**Document Status:** Not Started  
**Last Updated:** 2026-03-29  
**Implementation Status:** ⬜ Not Started
