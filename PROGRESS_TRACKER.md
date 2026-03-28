# FleetOpsX – Master Progress Tracker

> **How to use this file:**
> Read this FIRST at the start of every work session.
> It tells you exactly where you are, what to do next, and links to the right spec.
> Update the "Quick Status" box and tick off items as you complete them.

---

## Quick Status ← UPDATE THIS EVERY SESSION

```
Last Updated  : 2026-03-29
Last Worked On: P1-E5 Web UI – Ops Dashboard ✅
Current Phase : Phase 1 – MVP
Current Epic  : P1-E6 Driver View
Next Action   : Build DriverView page + backend driver stops endpoint
Blocker       : None
Demo Target   : Phase 1 complete — working end-to-end demo
Timeline      : 4 weeks
```

---

## Phase Overview

| Phase | Name | Status | Milestone |
|-------|------|--------|-----------|
| **Phase 1** | MVP – Assisted Dispatch | 🔄 In Progress (6/7 epics done) | Investor + pilot demo ready |
| **Phase 2** | Autonomous Dispatch & Optimization | ⬜ Not Started | Pilot customer live |
| **Phase 3** | Adaptive Multi-Agent & Learning | ⬜ Not Started | AI moat for Series A |
| **Phase 4** | Fleet Intelligence Platform | ⬜ Not Started | Enterprise contracts |

---

## DEMO COMPLETION CHECKLIST

This is what "Phase 1 working demo" means. Every item below must be ✅ before you call the demo ready:

```
[ ] docker compose up starts all services without errors
[ ] Seed script runs: python scripts/seed_data.py --start-date <date>
[ ] Dispatcher can log in at http://localhost:5173/login
[ ] Dashboard shows today's unassigned orders
[ ] "Generate Plan" button assigns orders to drivers
[ ] Assignments table shows driver names + stop sequences
[ ] Driver can log in (driver@demo.com) and see their stops
[ ] Driver can tap "Arrived" and "Delivered" on each stop
[ ] Dispatcher dashboard reflects updated delivery counts
[ ] API docs available at http://localhost:8000/docs
```

---

## Phase 1 – Epic Status

| Epic | Name | Status | GENSPEC | Blocker |
|------|------|--------|---------|---------|
| P1-E1 | Infrastructure Setup | ✅ Done | `GENSPEC_P1-E1_infrastructure_setup_v2.md` | — |
| P1-E2 | Multi-Tenant Foundations | ✅ Done | `GENSPEC_P1-E2_multi_tenancy_v2.md` | — |
| P1-E3 | Core Domain Models & APIs | ✅ Done | `GENSPEC_P1-E3_core_domain_models_v1.md` | — |
| P1-E3-S6 | Auth – JWT Login | ✅ Done | `GENSPEC_P1-E3-S6_auth_v1.md` | — |
| P1-E4 | Planner v1 (Rule-Based) | ✅ Done | `GENSPEC_P1-E4_planner_v1_v1.md` | — |
| P1-E5 | Web UI – Ops Dashboard | ✅ Done | `GENSPEC_P1-E5_ops_dashboard_v1.md` | — |
| P1-E6 | Driver View | ⬜ Not Started | `GENSPEC_P1-E6_driver_view_v1.md` | P1-E4 + P1-E5 Login |
| P1-E7 | Synthetic Data & Demo | ✅ Done | `GENSPEC_P1-E7_synthetic_data_v1.md` | — |

---

## Phase 1 – Story-Level Tracker

### P1-E1: Infrastructure Setup ✅ (with bugs)

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E1-S1 | Monorepo structure | ✅ | `FleetOpsX-API/`, `FleetOpsX-UI/` |
| P1-E1-S2 | FastAPI skeleton + health endpoint | ✅ | `app/main.py`, `app/api/health.py` |
| P1-E1-S3 | Postgres + Redis via Docker Compose | ✅ | `docker-compose.yml` |
| P1-E1-S4 | Alembic migrations pipeline | ✅ | `alembic/env.py` |
| P1-E1-S5 | CI/CD GitHub Actions | ✅ | `.github/workflows/` |
| **BUG-001** | Fix `db.py` wrong attribute name | ✅ Fixed | `app/core/db.py` — `settings.DATABASE_URL` |
| **BUG-002** | Fix `main.py` wrong import | ✅ Fixed | `app/main.py` — `config.settings.SENTRY_DSN` |
| **BUG-003** | Fix `planners/interface.py` bare stub | ✅ Fixed | `app/planners/interface.py` — ABC + @abstractmethod |

### P1-E2: Multi-Tenant Foundations ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E2-PRE1 | Fix BUG-001 | ✅ | `app/core/db.py` |
| P1-E2-PRE2 | Fix BUG-002 | ✅ | `app/main.py` |
| P1-E2-PRE3 | Fix BUG-003 | ✅ | `app/planners/interface.py` |
| P1-E2-S1 | Tenant model already exists | ✅ | `app/models/tenant.py` |
| P1-E2-S2 | Tenant ContextVar | ✅ | `app/core/context.py` |
| P1-E2-S3 | TenantMiddleware | ✅ | `app/core/middleware.py` |
| P1-E2-S4 | FastAPI deps (`require_tenant_id`) | ✅ | `app/api/deps.py` |
| P1-E2-S5 | Central API router | ✅ | `app/api/router.py` |
| P1-E2-S6 | Register middleware in main.py | ✅ | `app/main.py` |
| P1-E2-S7 | Alembic migration — tenant tables | ✅ | `alembic/versions/69965e83503f_p1_e2_add_tenant_models.py` |
| P1-E2-VER | Verify: tenants + tenant_configs in DB at (head) | ✅ | docker exec confirmed |

### P1-E3: Core Domain Models & APIs ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E3-M1 | User model | ✅ | `app/models/user.py` |
| P1-E3-M2 | Depot model | ✅ | `app/models/depot.py` |
| P1-E3-M3 | Driver model | ✅ | `app/models/driver.py` |
| P1-E3-M4 | DriverShift model | ✅ | `app/models/driver_shift.py` |
| P1-E3-M5 | Vehicle model | ✅ | `app/models/vehicle.py` |
| P1-E3-M6 | Customer model | ✅ | `app/models/customer.py` |
| P1-E3-M7 | Order model | ✅ | `app/models/order.py` |
| P1-E3-M8 | RoutePlan/Route/RouteStop/Event | ✅ | `app/models/route_plan.py` |
| P1-E3-M9 | Update `__init__.py` | ✅ | `app/models/__init__.py` |
| P1-E3-SCH | All 7 Pydantic schema files | ✅ | `app/schemas/` |
| P1-E3-SVC | All 5 service files | ✅ | `app/services/` |
| P1-E3-API | All 5 CRUD routers | ✅ | `app/api/v1/` |
| P1-E3-MIG | Alembic migration — all 13 tables | ✅ | `alembic/versions/9cfd8384148b_p1_e3_core_domain_models.py` |
| P1-E3-VER | Verify: 13 tables in DB | ✅ | docker exec confirmed |

### P1-E3-S6: Auth – JWT Login ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-AUTH-1 | Add deps: python-jose, passlib | ✅ | `requirements.txt` |
| P1-AUTH-2 | JWT config in settings | ✅ | `app/core/config.py`, `.env` |
| P1-AUTH-3 | `app/core/security.py` | ✅ | hash_password, create_token, decode_token |
| P1-AUTH-4 | `app/schemas/auth.py` | ✅ | RegisterRequest, LoginRequest, TokenResponse |
| P1-AUTH-5 | `app/services/auth_service.py` | ✅ | register_user, login_user |
| P1-AUTH-6 | `app/api/v1/auth.py` | ✅ | POST /auth/register, POST /auth/login |
| P1-AUTH-7 | Update `app/api/deps.py` | ✅ | get_current_user, require_dispatcher, require_driver |
| P1-AUTH-8 | Register auth router | ✅ | `app/api/router.py` |
| P1-AUTH-9 | Add demo users to seed script | ✅ | `scripts/seed_data.py` |
| P1-AUTH-VER | App imports clean | ✅ | python import check passed |

### P1-E4: Planner v1 ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E4-S1 | RuleBasedPlanner implementation | ✅ | `app/planners/rule_based.py` |
| P1-E4-S2 | PlanningService wrapper | ✅ | `app/services/planning_service.py` |
| P1-E4-S3 | `/plan/day` endpoint | ✅ | `app/api/v1/planning.py` |
| P1-E4-S4 | Maps API client (optional) | ✅ | `app/core/maps.py` (stub, activates when MAPS_API_KEY set) |
| P1-E4-S5 | Register planning router | ✅ | `app/api/router.py` |
| P1-E4-VER | App imports clean | ✅ | python import check passed |

### P1-E5: Ops Dashboard UI ⬜

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E5-T | TypeScript types | ⬜ | `src/types/index.ts` |
| P1-E5-API | API client modules (6 files) | ⬜ | `src/api/` |
| P1-E5-STORE | Update zustand store | ⬜ | `src/store/useAppStore.ts` |
| P1-E5-ROUTE | ProtectedRoute + AppRoutes update | ⬜ | `src/routes/` |
| P1-E5-LOGIN | Login page (full implementation) | ⬜ | `src/pages/Login.tsx` |
| P1-E5-LAYOUT | AppLayout with sidebar | ⬜ | `src/components/layout/AppLayout.tsx` |
| P1-E5-DASH | Dashboard page (stats + quick action) | ⬜ | `src/pages/Dashboard.tsx` |
| P1-E5-PLAN | Planning page (key demo screen) | ⬜ | `src/pages/Planning.tsx` |
| P1-E5-SHARED | Shared components: FormModal, DataTable, StatusBadge, FormField, ToggleSwitch | ⬜ | `src/components/shared/` |
| P1-E5-ORD | Orders — full CRUD (table + create/edit modal + filters) | ⬜ | `src/pages/Orders.tsx` |
| P1-E5-DRV | Drivers — full CRUD (table + create/edit modal + depot dropdown) | ⬜ | `src/pages/Drivers.tsx` |
| P1-E5-VEH | Vehicles — full CRUD (table + create/edit modal + refrigerated toggle) | ⬜ | `src/pages/Vehicles.tsx` |
| P1-E5-DEP | Depots — full CRUD (table + create/edit modal + lat/lng fields) | ⬜ | `src/pages/Depots.tsx` |
| P1-E5-COMP | Shared components (StatusBadge, Spinner, EmptyState) | ⬜ | `src/components/shared/` |
| P1-E5-VER | UI loads, login works, planning screen generates plan | ⬜ | Manual test |

### P1-E6: Driver View ⬜

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E6-API | Backend driver endpoints | ⬜ | `app/api/v1/driver.py` |
| P1-E6-REG | Register driver router | ⬜ | `app/api/router.py` |
| P1-E6-FE | Frontend API client | ⬜ | `src/api/driver.ts` |
| P1-E6-PAGE | DriverView page | ⬜ | `src/pages/DriverView.tsx` |
| P1-E6-SEED | Link driver email in seed script | ⬜ | `scripts/seed_data.py` |
| P1-E6-VER | Driver sees stops + marks delivered | ⬜ | Manual test |

### P1-E7: Synthetic Data & Demo ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E7-S1 | Bangalore data generator | ✅ | `scripts/seed_data.py` |
| P1-E7-S2 | CLI options (--start-date, --days, --clean) | ✅ | `scripts/seed_data.py` |
| P1-E7-S3 | Demo users created in seed | ✅ | `scripts/seed_data.py` |
| P1-E7-VER | Seed ran: 2 depots, 20 drivers, 20 vehicles, 50 customers, 99 orders | ✅ | Verified live |

---

## Phase 2 – Epic Status

| Epic | Name | Status | GENSPEC |
|------|------|--------|---------|
| P2-E1 | OR-Tools VRPTW Optimization | ⬜ Spec ready | `GENSPEC_P2_autonomous_dispatch_v1.md` |
| P2-E2 | LangGraph Planner Agent | ⬜ Spec ready | `GENSPEC_P2_autonomous_dispatch_v1.md` |
| P2-E3 | Real-Time Tracking & Re-planning | ⬜ Spec ready | `GENSPEC_P2_autonomous_dispatch_v1.md` |
| P2-E4 | SLA Risk Alerts | ⬜ Spec ready | `GENSPEC_P2_autonomous_dispatch_v1.md` |

## Phase 3 – Epic Status

| Epic | Name | Status | GENSPEC |
|------|------|--------|---------|
| P3-E1 | Historical Analytics & Feature Store | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |
| P3-E2 | Multi-Agent System (Planner, Monitor, Forecast, Explainer) | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |
| P3-E3 | Proactive Planning | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |

## Phase 4 – Epic Status

| Epic | Name | Status | GENSPEC |
|------|------|--------|---------|
| P4-E1 | Multi-Region & Per-Tenant DB | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |
| P4-E2 | Partner APIs (ERP/WMS/TMS) | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |
| P4-E3 | Capacity Marketplace | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |
| P4-E4 | Governance, Compliance & Audit | ⬜ Planning | `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` |

---

## GENSPEC Document Index

### Phase 1 — All Available

| File | Epic | Ready? | Notes |
|------|------|--------|-------|
| `GENSPEC_P1-E1_infrastructure_setup_v2.md` | P1-E1 | ✅ Reference | Implemented — shows what exists + bug list |
| `GENSPEC_P1-E2_multi_tenancy_v2.md` | P1-E2 | ✅ Implement | Full code + file paths + verification |
| `GENSPEC_P1-E3_core_domain_models_v1.md` | P1-E3 | ✅ Implement | All models, schemas, services, routers |
| `GENSPEC_P1-E3-S6_auth_v1.md` | P1-E3-S6 | ✅ Implement | JWT login, register, dispatcher/driver roles |
| `GENSPEC_P1-E4_planner_v1_v1.md` | P1-E4 | ✅ Implement | RuleBasedPlanner + planning endpoint |
| `GENSPEC_P1-E5_ops_dashboard_v1.md` | P1-E5 | ✅ Implement | Base spec: Login, AppLayout, Dashboard, Planning page |
| `GENSPEC_P1-E5_crud_screens_addendum_v1.md` | P1-E5 | ✅ Implement | Addendum: full CRUD for Orders, Drivers, Vehicles, Depots — complete working code |
| `GENSPEC_P1-E6_driver_view_v1.md` | P1-E6 | ✅ Implement | Driver mobile web view + status updates |
| `GENSPEC_P1-E7_synthetic_data_v1.md` | P1-E7 | ✅ Implement | Bangalore seed script |

### Phase 2-4 — High Level (detail added when Phase 1 ships)

| File | Phases | Ready? |
|------|--------|--------|
| `GENSPEC_P2_autonomous_dispatch_v1.md` | Phase 2 | ✅ Spec (not implement yet) |
| `GENSPEC_P3_P4_multi_agent_enterprise_v1.md` | Phase 3 & 4 | ✅ Planning |

---

## Implementation Order (4-week plan to demo)

### Week 1 — Backend Foundation
```
Day 1-2: Fix bugs → P1-E2 (multi-tenancy + middleware)
Day 3-4: P1-E3 (domain models + migration)
Day 5:   P1-E3-S6 (auth JWT)
```

### Week 2 — Backend Features + Seed Data
```
Day 1-2: P1-E4 (rule-based planner)
Day 3:   P1-E7 (seed data script — need data for UI testing)
Day 4-5: Backend integration test (all APIs working end-to-end)
```

### Week 3 — Frontend
```
Day 1:   P1-E5 setup: types, API clients, store, routing, login
Day 2-3: P1-E5 core: Dashboard + Planning screen (key demo screens first)
Day 4:   P1-E5 management: Orders + Drivers + Vehicles + Depots
Day 5:   P1-E6 driver view
```

### Week 4 — Integration, Polish, Demo Prep
```
Day 1-2: Full end-to-end test with seed data
Day 3:   Bug fixes and polish
Day 4:   Demo script rehearsal
Day 5:   Demo ready ✅
```

---

## Architecture Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| FastAPI over Django | Async-first, less boilerplate, better for AI agent integration | 2025-12 |
| UUID PKs everywhere | Multi-tenant safe, no sequential ID leakage | 2025-12 |
| Shared DB with tenant_id | Simplest start; per-tenant DB routing in Phase 4 | 2025-12 |
| Header-based tenant in dev, JWT in prod | JWT covers tenant_id — no separate header needed | 2025-12 |
| PlannerInterface abstraction | Phase 2 swaps in LangGraph behind same API endpoint | 2025-12 |
| Modular monolith now, microservices later | Extract only when scale forces it (Phase 3+) | 2025-12 |
| PostGIS from day one | Geospatial distance queries needed for planner | 2025-12 |
| Driver linked by email to User | Simple Phase 1 approach — driver creates account with same email as Driver record | 2026-03 |
| Maps API optional in Phase 1 | Haversine works for demo; real Maps API plugged in for Phase 2 | 2026-03 |

---

## Known Issues / Tech Debt

| ID | Severity | Description | File | Resolution |
|----|----------|-------------|------|------------|
| BUG-001 | 🔴 High | `settings.database_url` wrong case — app won't start | `app/core/db.py` | Fix in P1-E2 pre-work |
| BUG-002 | 🔴 High | `config.SENTRY_DSN` wrong import | `app/main.py` | Fix in P1-E2 pre-work |
| BUG-003 | 🟡 Medium | `PlannerInterface` is bare stub | `app/planners/interface.py` | Fix in P1-E2 pre-work |
| TD-001 | 🟢 Low | CORS `allow_origins=["*"]` | `app/main.py` | Restrict before prod |
| TD-002 | 🟢 Low | `order_service.list_orders` date filter fragile at month-end | `app/services/order_service.py` | Fix with `timedelta(days=1)` |
| TD-003 | 🟢 Low | No pagination on list endpoints | All routers | Add `skip/limit` params before prod |
| TD-004 | 🟢 Low | Driver linked by email — breaks if emails differ | `app/api/v1/driver.py` | Add explicit `driver_id` FK to User model in Phase 2 |

---

## Environment Setup Reference

### First-Time Setup

```bash
# 1. Create .env in FleetOpsX-API/
cat > FleetOpsX-API/.env << 'EOF'
APP_ENV=local
DATABASE_URL=postgresql+psycopg2://fleetuser:fleetpass@localhost:5432/fleetopsx
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=
MAPS_API_KEY=
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
PLANNER_TYPE=rule_based
EOF

# 2. Start infra
cd FleetOpsX-API
docker compose up db redis -d

# 3. Install Python deps
pip install -r requirements.txt

# 4. Run migrations
alembic upgrade head

# 5. Seed demo data
python scripts/seed_data.py --start-date $(date +%Y-%m-%d)

# 6. Start API
uvicorn app.main:app --reload

# 7. Start UI (separate terminal)
cd ../FleetOpsX-UI
npm install && npm run dev
```

### Useful Commands

```bash
# API dev
uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
alembic history

# Docker
docker compose up -d                              # all services
docker compose up db redis -d                     # infra only
docker compose logs api -f                        # API logs
docker exec fleetopsx-db psql -U fleetuser -d fleetopsx -c "\dt"  # list tables

# Seed data
python scripts/seed_data.py --start-date 2026-01-15 --days 3
python scripts/seed_data.py --clean

# API tests
curl http://localhost:8000/health
open http://localhost:8000/docs

# Login test
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"dispatcher@demo.com","password":"demo1234","tenant_id":"<uuid>"}' | jq .
```

---

## How to Resume After a Break (3-step process)

1. **Read Quick Status box** at top of this file — tells you current epic
2. **Open the GENSPEC** for that epic (listed in GENSPEC Index above)
3. **Find the first ⬜ row** in the File Checklist inside that GENSPEC — start there

---

*Last updated: 2026-03-29*
