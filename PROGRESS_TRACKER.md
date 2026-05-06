# FleetOpsX – Master Progress Tracker

> **How to use this file:**
> Read this FIRST at the start of every work session.
> It tells you exactly where you are, what to do next, and links to the right spec.
> Update the "Quick Status" box and tick off items as you complete them.

---

## Quick Status ← UPDATE THIS EVERY SESSION

```
Last Updated  : 2026-05-05
Last Worked On: Phase P — PP-E2 BE complete (plan options: fastest/economical/balanced + confirm)
Current Phase : Phase P – Priority Features — ALL BE EPICS COMPLETE
Current Epic  : Phase P fully done (BE + FE)
Next Action   : Run migrations (alembic upgrade head) + smoke-test all new endpoints
Blocker       : None
```

---

## Phase Overview

| Phase | Name | Status | Milestone |
|-------|------|--------|-----------|
| **Phase 1** | MVP – Assisted Dispatch | ✅ Done (7/7 epics done) | Investor + pilot demo ready |
| **Phase 2** | Autonomous Dispatch & Optimization | ✅ Done (7/7 epics done) | Pilot customer live |
| **Phase 3** | Adaptive Multi-Agent & Learning | ✅ Done (3/3 epics done) | AI moat for Series A |
| **Phase P** | Priority Features (NEW) | ⬜ Not Started (7 epics) | Demo-ready polish + power features |
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
| P1-E6 | Driver View | ✅ Done | `GENSPEC_P1-E6_driver_view_v1.md` | — |
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

### P1-E5: Ops Dashboard UI ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E5-T | TypeScript types | ✅ | `src/types/index.ts` |
| P1-E5-API | API client modules (6 files) | ✅ | `src/api/` |
| P1-E5-STORE | Update zustand store | ✅ | `src/store/useAppStore.ts` |
| P1-E5-ROUTE | ProtectedRoute + AppRoutes update | ✅ | `src/routes/` |
| P1-E5-LOGIN | Login page (full implementation) | ✅ | `src/pages/Login.tsx` |
| P1-E5-LAYOUT | AppLayout with sidebar | ✅ | `src/components/layout/AppLayout.tsx` |
| P1-E5-DASH | Dashboard page (stats + quick action) | ✅ | `src/pages/Dashboard.tsx` |
| P1-E5-PLAN | Planning page (key demo screen) | ✅ | `src/pages/Planning.tsx` |
| P1-E5-SHARED | Shared components: FormModal, DataTable, StatusBadge, FormField, ToggleSwitch | ✅ | `src/components/shared/` |
| P1-E5-ORD | Orders — full CRUD (table + create/edit modal + filters) | ✅ | `src/pages/Orders.tsx` |
| P1-E5-DRV | Drivers — full CRUD (table + create/edit modal + depot dropdown) | ✅ | `src/pages/Drivers.tsx` |
| P1-E5-VEH | Vehicles — full CRUD (table + create/edit modal + refrigerated toggle) | ✅ | `src/pages/Vehicles.tsx` |
| P1-E5-DEP | Depots — full CRUD (table + create/edit modal + lat/lng fields) | ✅ | `src/pages/Depots.tsx` |
| P1-E5-COMP | Shared components (StatusBadge, Spinner, EmptyState) | ✅ | `src/components/shared/` |
| P1-E5-VER | UI loads, login works, planning screen generates plan | ✅ | Manual test |

### P1-E6: Driver View ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P1-E6-API | Backend driver endpoints | ✅ | `app/api/v1/driver.py` |
| P1-E6-REG | Register driver router | ✅ | `app/api/router.py` |
| P1-E6-FE | Frontend API client | ✅ | `src/api/driver.ts` |
| P1-E6-PAGE | DriverView page | ✅ | `src/pages/DriverView.tsx` |
| P1-E6-SEED | Link driver email in seed script | ✅ | `scripts/seed_data.py` |
| P1-E6-VER | Driver sees stops + marks delivered | ✅ | Manual test |

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
| P2-E1 | OR-Tools VRPTW Optimization | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |
| P2-E2 | Multi-LLM Provider (Claude/OpenAI/Gemini) | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |
| P2-E3 | LangGraph Dispatch Agent | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |
| P2-E4 | Real-Time GPS Tracking | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |
| P2-E5 | Live Map Dashboard (Leaflet + OSM) | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |
| P2-E6 | Agent Activity Feed (UI) | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |
| P2-E7 | SLA Risk Alerts | ✅ Done | `DEV_SPEC_P2_autonomous_dispatch_v2.md` |

## Phase 2 – Story-Level Tracker

### P2-E1: OR-Tools VRPTW ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E1-S1 | Add `ortools>=9.8` to requirements.txt | ✅ | `requirements.txt` |
| P2-E1-S2 | Add `PLANNER_TYPE` to config | ✅ | `app/core/config.py` (already existed) |
| P2-E1-S3 | Implement ORToolsPlanner | ✅ | `app/planners/ortools_planner.py` |
| P2-E1-S4 | Update PlanningService with feature flag | ✅ | `app/services/planning_service.py` |
| P2-E1-VER | Set PLANNER_TYPE=ortools → plan returns optimized routes | ✅ | 33/33 assigned, 3 routes, planner=ortools confirmed |

### P2-E2: Multi-LLM Provider ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E2-S1 | Add LangChain deps (langchain-core, langchain-google-genai, langchain-openai, langchain-anthropic, langgraph) | ✅ | `requirements.txt` |
| P2-E2-S2 | LLM config stored as TenantConfig KV rows (no migration needed) | ✅ | existing `tenant_configs` table |
| P2-E2-S3 | No migration needed — uses existing KV store | ✅ | — |
| P2-E2-S4 | Implement LLMProviderFactory | ✅ | `app/core/llm_factory.py` |
| P2-E2-S5 | GET + PATCH /tenants/config/llm endpoints | ✅ | `app/api/v1/tenants.py` |
| P2-E2-S6 | Add LLM env vars to .env + docker-compose | ✅ | `.env`, `docker-compose.yml` |
| P2-E2-VER | GET returns system default, PATCH persists to KV store, provider switch works | ✅ | Live API test confirmed |

### P2-E3: LangGraph Agent ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E3-S1 | AgentLog model | ✅ | `app/models/agent_log.py` |
| P2-E3-S2 | Alembic migration for agent_logs | ✅ | `alembic/versions/486e6906d442_p2_e3_agent_logs.py` |
| P2-E3-S3 | LangGraph agent (fetch → optimize → explain) | ✅ | `app/planners/langgraph_agent.py` |
| P2-E3-S4 | Agent logs API endpoint | ✅ | `app/api/v1/agent_logs.py` |
| P2-E3-S5 | Register agent_logs router | ✅ | `app/api/router.py` |
| P2-E3-S6 | planner + explanation fields in response (dict fields, no schema change needed) | ✅ | `langgraph_agent.py` adds them |
| P2-E3-VER | PLANNER_TYPE=langgraph → fetch+optimize+explain logged, explanation returned | ✅ | 3 agent log steps confirmed, 33/33 assigned |

### P2-E4: Real-Time GPS Tracking ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E4-S1 | DriverLocationPing model | ✅ | `app/models/tracking.py` |
| P2-E4-S2 | Alembic migration for tracking table | ✅ | `alembic/versions/3abca364f966_p2_e4_driver_location_pings.py` |
| P2-E4-S3 | TrackingService (record ping + Redis cache) | ✅ | `app/services/tracking_service.py` |
| P2-E4-S4 | Add get_redis() to db.py | ✅ | `app/core/db.py` |
| P2-E4-S5 | Tracking endpoints (ping / live / history) | ✅ | `app/api/v1/tracking.py` |
| P2-E4-S6 | Register tracking router | ✅ | `app/api/router.py` |
| P2-E4-S7 | Driver app geo-ping useEffect (every 30s) | ✅ | `src/pages/DriverView.tsx` |
| P2-E4-S8 | Frontend tracking API client | ✅ | `src/api/tracking.ts` |
| P2-E4-S9 | `POST /plan/replan` endpoint (single driver or full fleet) | ✅ | `app/api/v1/planning.py` |
| P2-E4-VER | Driver ping → Redis updated → live endpoint returns position | ✅ | 2 pings stored, Redis cache confirmed, live returns 1 driver |
| P2-E4-VER2 | Replan returns updated assignments with `"replan": true` | ✅ | 33/33 assigned, replan=True confirmed |

### P2-E5: Live Map Dashboard ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E5-S1 | Install leaflet@1.9.4 + react-leaflet@5.0 + @types/leaflet | ✅ | `package.json` |
| P2-E5-S2 | FleetMap component (OSM tiles, AutoFit, Vite icon fix) | ✅ | `src/components/map/FleetMap.tsx` |
| P2-E5-S3 | DriverMarker with DivIcon + popup (name, time, speed, accuracy) | ✅ | `src/components/map/DriverMarker.tsx` |
| P2-E5-S4 | RoutePolyline — deferred (no route coords in Phase 2) | — | skipped |
| P2-E5-S5 | LiveMap page — polls every 10s, driver list cards below map | ✅ | `src/pages/LiveMap.tsx` |
| P2-E5-S6 | Add /map route + "Live Map" sidebar nav item | ✅ | `AppRoutes.tsx`, `AppLayout.tsx` |
| P2-E5-VER | Vite HMR picked up leaflet/react-leaflet cleanly, UI 200 OK | ✅ | `vite ✨ new dependencies optimized` confirmed |

### P2-E6: Agent Activity Feed ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E6-S1 | AgentFeed component (collapsible, role icons, LLM summary prominent) | ✅ | `src/components/shared/AgentFeed.tsx` |
| P2-E6-S2 | Agent logs API client | ✅ | `src/api/agentLogs.ts` |
| P2-E6-S3 | Planning page: AgentFeed + planner badge below plan result | ✅ | `src/pages/Planning.tsx` |
| P2-E6-VER | 3 log entries (fetch/optimize/explain) returned for langgraph plan_id | ✅ | API confirmed |

### P2-E7: SLA Risk Alerts ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P2-E7-S1 | SLA service (at-risk stop detection) | ✅ | `app/services/sla_service.py` |
| P2-E7-S2 | GET /sla/at-risk endpoint | ✅ | `app/api/v1/sla.py` |
| P2-E7-S3 | Register SLA router | ✅ | `app/api/router.py` |
| P2-E7-S4 | Frontend SLA API client | ✅ | `src/api/sla.ts` |
| P2-E7-S5 | Dashboard at-risk panel (collapsible, red badge, 60s poll) | ✅ | `src/pages/Dashboard.tsx` |
| P2-E7-VER | Driver far away → 70 stops flagged at-risk; clear ping → 0 | ✅ | API + Redis test confirmed |

## Phase 3 – Epic Status

| Epic | Name | Status | GENSPEC |
|------|------|--------|---------|
| P3-E1 | Historical Analytics & Feature Store | ✅ Done | `DEV_SPEC_P3_adaptive_multi_agent_v1.md` |
| P3-E2 | Multi-Agent Orchestration (Forecast, Planner, Explainer, Monitor) | ✅ Done | `DEV_SPEC_P3_adaptive_multi_agent_v1.md` |
| P3-E3 | Proactive Planning & Suggested Actions UI | ✅ Done | `DEV_SPEC_P3_adaptive_multi_agent_v1.md` |

---

### P3-E1: Historical Analytics & Feature Store ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P3-E1-S1 | `DeliveryAnalytics` + `DriverPerformanceScore` models | ✅ | `app/models/analytics.py` |
| P3-E1-S2 | Alembic migration for analytics tables | ✅ | `alembic/versions/a1b2c3d4e5f6_p3_e1_analytics_tables.py` |
| P3-E1-S3 | `AnalyticsService` — ETL function (idempotent upsert) | ✅ | `app/services/analytics_service.py` |
| P3-E1-S4 | APScheduler setup + register daily ETL job @ 01:00 | ✅ | `app/workers/scheduler.py`, `app/main.py` |
| P3-E1-S5 | Analytics API endpoints (kpis, driver-performance, run-etl) | ✅ | `app/api/v1/analytics.py` |
| P3-E1-S6 | Register analytics router | ✅ | `app/api/router.py` |
| P3-E1-S7 | `recharts` added to package.json + frontend API client | ✅ | `src/api/analytics.ts` |
| P3-E1-S8 | Analytics page (KPI cards + charts + driver leaderboard) | ✅ | `src/pages/Analytics.tsx` |
| P3-E1-S9 | Add `/analytics` route + nav item | ✅ | `AppRoutes.tsx`, `AppLayout.tsx` |
| P3-E1-VER | Run ETL → GET /analytics/kpis returns data → charts render | ✅ | Manual test |

### P3-E2: Multi-Agent Orchestration ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P3-E2-S1 | `AgentSuggestion` model | ✅ | `app/models/agent_suggestion.py` |
| P3-E2-S2 | Alembic migration for `agent_suggestions` | ✅ | `alembic/versions/b2c3d4e5f6a7_p3_e2_agent_suggestions.py` |
| P3-E2-S3 | Forecast Agent node (day-of-week baseline from DeliveryAnalytics) | ✅ | `app/planners/agents/forecast_agent.py` |
| P3-E2-S4 | Monitor Agent (standalone scan function, creates AgentSuggestion rows) | ✅ | `app/planners/agents/monitor_agent.py` |
| P3-E2-S5 | Multi-agent LangGraph orchestrator (fetch_context → forecast → call_optimizer → explain) | ✅ | `app/planners/orchestrator.py` |
| P3-E2-S6 | `MultiAgentPlanner` implementing `PlannerInterface` | ✅ | `app/planners/multi_agent_planner.py` |
| P3-E2-S7 | Add `multi_agent` case to `get_planner()` factory | ✅ | `app/services/planning_service.py` |
| P3-E2-S8 | `AgentSuggestionOut` + `AgentSuggestionUpdate` schemas | ✅ | `app/schemas/agent_suggestion.py` |
| P3-E2-S9 | `GET /agent/suggestions` + `PATCH /agent/suggestions/{id}` endpoints | ✅ | `app/api/v1/agent_suggestions.py` |
| P3-E2-S10 | Register agent_suggestions router | ✅ | `app/api/router.py` |
| P3-E2-VER | PLANNER_TYPE=multi_agent → forecast step in response, agent logs show 4 steps | ✅ | Manual test |

### P3-E3: Proactive Planning & Suggested Actions UI ✅

| ID | Story | Status | File |
|----|-------|--------|------|
| P3-E3-S1 | Register Monitor scan job in APScheduler (every 5 min, 07–20h) | ✅ | `app/workers/scheduler.py` |
| P3-E3-S2 | Accept REPLAN_DRIVER → triggers scoped replan, marks ACCEPTED | ✅ | `app/api/v1/agent_suggestions.py` (done in P3-E2) |
| P3-E3-S3 | Frontend API client for suggestions (fetch + respond) | ✅ | `src/api/agentSuggestions.ts` |
| P3-E3-S4 | `SuggestedActions` component (Accept/Dismiss, polls 60s) | ✅ | `src/components/shared/SuggestedActions.tsx` |
| P3-E3-S5 | Add `SuggestedActions` to Dashboard below SLA panel | ✅ | `src/pages/Dashboard.tsx` |
| P3-E3-S6 | Planning page PENDING suggestions badge | ✅ | `src/pages/Planning.tsx` |
| P3-E3-S7 | Add `AgentSuggestion` type to frontend types | ✅ | `src/types/index.ts` |
| P3-E3-VER | Monitor scan creates suggestion → appears in UI → Accept triggers replan | ✅ | Manual test |

## Phase P – Priority Features (NEW — implement before Phase 4)

> These 7 epics were added 2026-04-30 as high-priority product features for demo readiness and product quality.
> Complete ALL Phase P epics before starting Phase 4.

| Epic | Name | Area | Status |
|------|------|------|--------|
| PP-E1 | Planning AI Enhancement | Backend + FE | 🟡 BE done · FE done |
| PP-E2 | Multiple Plan Options (Fastest / Economical / Balanced) | Backend + FE | 🟡 BE done · FE done |
| PP-E3 | Dynamic Conditions (Driver & Vehicle Availability) | Backend + FE | 🟡 BE done · FE done |
| PP-E4 | Chat AI Interface | Backend + FE | 🟡 BE done · FE done |
| PP-E5 | Excel Export / Import | Backend + FE | 🟡 BE done · FE done (pending router rename) |
| PP-E6 | Map with Route Plans Overlay | Frontend | ✅ Done |
| PP-E7 | UI Polish & Design Overhaul | Frontend | ✅ Done |

---

### PP-E1: Planning AI Enhancement
> Smarter AI-driven planning with reasoning transparency, confidence scores, and natural-language plan summaries shown to the dispatcher.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E1-S1 | Add `confidence_score` + `reasoning_steps` fields to plan response schema | ✅ | all planners return these fields |
| PP-E1-S2 | LangGraph agent emits step-by-step reasoning (chain-of-thought) per route | ✅ | `app/planners/langgraph_agent.py` — `_node_explain` |
| PP-E1-S3 | AI pre-planning analysis: flag risky orders before generating plan | ✅ | `app/planners/langgraph_agent.py` — `_node_analyze` |
| PP-E1-S4 | Backend: POST /plan/day returns `ai_summary`, `confidence`, `warnings[]` | ✅ | `app/api/v1/planning.py` (passes through planner dict) |
| PP-E1-S5 | Frontend: Planning page shows AI reasoning panel + confidence badge | ⬜ | `src/pages/Planning.tsx` |
| PP-E1-S6 | Frontend: Pre-plan warnings shown before dispatcher confirms | ⬜ | `src/pages/Planning.tsx` |
| PP-E1-VER | Planning returns reasoning + confidence; warnings surface in UI | ⬜ | Manual test |

---

### PP-E2: Multiple Plan Options (Fastest / Economical / Balanced)
> Generate 3 distinct route plans and let the dispatcher pick the best one.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E2-S1 | Cost model: fuel cost + time cost + distance weighting per plan type | ✅ | `app/planners/cost_model.py` |
| PP-E2-S2 | ORToolsPlanner accepts `plan_mode` param: `fastest` / `economical` / `balanced` | ✅ | `app/planners/ortools_planner.py` — `plan_mode` + `commit_assignments` params |
| PP-E2-S3 | POST /plan/options — runs all 3 modes, returns array of 3 plan summaries | ✅ | `app/api/v1/planning.py` + `app/services/plan_options_service.py` |
| PP-E2-S4 | Plan summary schema: `mode`, `total_distance_km`, `est_duration_min`, `est_fuel_cost`, `orders_covered` | ✅ | `app/schemas/plan_options.py` |
| PP-E2-S5 | POST /plan/confirm — confirm selected plan_id as active plan | ✅ | `app/api/v1/planning.py` |
| PP-E2-S6 | Frontend: Plan options card layout (3 cards, side-by-side, metrics highlighted) | ⬜ | `src/components/planning/PlanOptionsCard.tsx` (new) |
| PP-E2-S7 | Frontend: Planning page — "Generate Options" button → select → confirm flow | ⬜ | `src/pages/Planning.tsx` |
| PP-E2-VER | 3 plan variants returned; dispatcher selects one; assignments applied | ⬜ | Manual test |

---

### PP-E3: Dynamic Conditions (Driver & Vehicle Availability)
> Real-time availability of drivers and vehicles fed into the planner — unavailable resources excluded automatically.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E3-S1 | `DriverAvailability` model: shift_start, shift_end, status (available/on_break/off_duty), hours_worked_today | ✅ | `app/models/driver_availability.py` |
| PP-E3-S2 | `VehicleStatus` model: current_mileage, fuel_level_pct, status (available/in_use/maintenance) | ✅ | `app/models/vehicle_status.py` |
| PP-E3-S3 | Alembic migration for new tables | ✅ | `alembic/versions/c3d4e5f6a7b8_pp_e3_...py` |
| PP-E3-S4 | PATCH /drivers/{id}/availability — dispatcher marks driver available/off_duty | ✅ | `app/api/v1/drivers.py` |
| PP-E3-S5 | PATCH /vehicles/{id}/status — dispatcher updates vehicle fuel/status | ✅ | `app/api/v1/vehicles.py` |
| PP-E3-S6 | Planner reads availability before assigning — skips unavailable drivers/vehicles | ✅ | `app/planners/rule_based.py`, `app/planners/ortools_planner.py` |
| PP-E3-S7 | GET /fleet/availability — summary of all driver + vehicle statuses | ✅ | `app/api/v1/fleet.py` |
| PP-E3-S8 | Frontend: Drivers page — availability toggle (available / off duty / on break) | ⬜ | `src/pages/Drivers.tsx` |
| PP-E3-S9 | Frontend: Vehicles page — fuel level + status badges | ⬜ | `src/pages/Vehicles.tsx` |
| PP-E3-S10 | Frontend: Dashboard — fleet availability summary widget | ⬜ | `src/pages/Dashboard.tsx` |
| PP-E3-VER | Off-duty driver excluded from plan; low-fuel vehicle excluded automatically | ⬜ | Manual test |

---

### PP-E4: Chat AI Interface
> Conversational AI assistant embedded in the app — dispatchers ask questions in natural language and get instant answers.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E4-S1 | Chat context builder: aggregates today's orders, drivers, vehicles, plan status | ✅ | `app/services/chat_context_service.py` |
| PP-E4-S2 | POST /chat/message — LangChain-powered response with fleet context injected | ✅ | `app/api/v1/chat.py` |
| PP-E4-S3 | Chat history model: `ChatMessage` (session_id, role, content, tenant_id) | ✅ | `app/models/chat_message.py` |
| PP-E4-S4 | Alembic migration for chat_messages | ✅ | `alembic/versions/d4e5f6a7b8c9_pp_e4_chat_messages.py` |
| PP-E4-S5 | GET /chat/history?session_id= — last 50 messages | ✅ | `app/api/v1/chat.py` |
| PP-E4-S6 | Register chat router | ✅ | `app/api/router.py` |
| PP-E4-S7 | Frontend: Chat sidebar panel (slide-in, message bubbles, input box) | ⬜ | `src/components/chat/ChatPanel.tsx` (new) |
| PP-E4-S8 | Frontend: Chat API client | ⬜ | `src/api/chat.ts` (new) |
| PP-E4-S9 | Frontend: Chat icon in header/nav → toggles panel on all pages | ⬜ | `src/components/layout/AppLayout.tsx` |
| PP-E4-S10 | Seed chat suggestions: "How many orders unassigned?", "Which driver has most stops?" | ⬜ | `src/components/chat/ChatPanel.tsx` |
| PP-E4-VER | Ask "what's the plan summary?" → AI responds with today's fleet context | ⬜ | Manual test |

---

### PP-E5: Excel Export / Import
> Dispatchers can export orders and route plans to Excel, and import bulk orders via Excel template.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E5-S1 | Add `openpyxl` to requirements.txt | ✅ | `requirements.txt` |
| PP-E5-S2 | ExportService: orders → Excel | ✅ | `app/services/export_service.py` |
| PP-E5-S3 | ExportService: route plan → Excel (route per sheet) | ✅ | `app/services/export_service.py` |
| PP-E5-S4 | GET /export/orders | ✅ | `app/api/v1/export.py` |
| PP-E5-S5 | GET /export/plan/{plan_id} | ✅ | `app/api/v1/export.py` |
| PP-E5-S6 | ImportService: validate + parse Excel rows | ✅ | `app/services/import_service.py` |
| PP-E5-S7 | POST /import/orders | ✅ | `app/api/v1/import_orders.py` |
| PP-E5-S8 | GET /export/template | ✅ | `app/api/v1/export.py` |
| PP-E5-S9 | Register export + import routers | ✅ | `app/api/router.py` (via router_new.py rename) |
| PP-E5-S10 | Frontend: Orders page — "Export Orders" button + "Import Orders" file upload | ⬜ | `src/pages/Orders.tsx` |
| PP-E5-S11 | Frontend: Planning page — "Export Plan" button after plan generated | ⬜ | `src/pages/Planning.tsx` |
| PP-E5-S12 | Frontend: export/import API clients | ⬜ | `src/api/exportImport.ts` (new) |
| PP-E5-VER | Export orders → valid .xlsx opens in Excel; import file creates orders in DB | ⬜ | Manual test |

---

### PP-E6: Map with Route Plans Overlay
> Show planned routes as colored polylines on the live map, with stop markers and driver assignment visible.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E6-S1 | GET /plan/{plan_id}/geodata — returns routes with ordered lat/lng arrays per route | ⬜ | `app/api/v1/planning.py` |
| PP-E6-S2 | Enrich RouteStop with geocoded lat/lng at plan time (use customer coords) | ⬜ | `app/services/planning_service.py` |
| PP-E6-S3 | Frontend: `RoutePolyline` component — Leaflet Polyline per route, color-coded by driver | ⬜ | `src/components/map/RoutePolyline.tsx` (new) |
| PP-E6-S4 | Frontend: `StopMarker` component — numbered CircleMarker for each stop | ⬜ | `src/components/map/StopMarker.tsx` (new) |
| PP-E6-S5 | Frontend: LiveMap page — toggle: "Live Tracking" vs "Route Plan" view | ⬜ | `src/pages/LiveMap.tsx` |
| PP-E6-S6 | Frontend: Route plan view polls GET /plan/geodata and renders polylines + stops | ⬜ | `src/pages/LiveMap.tsx` |
| PP-E6-S7 | Frontend: Map legend (driver name → color) | ⬜ | `src/components/map/MapLegend.tsx` (new) |
| PP-E6-S8 | Frontend: Clicking a stop marker shows popup with order details | ⬜ | `src/components/map/StopMarker.tsx` |
| PP-E6-VER | After plan generated: Live Map shows colored routes + numbered stops per driver | ⬜ | Manual test |

---

### PP-E7: UI Polish & Design Overhaul
> Elevate the UI from functional to visually impressive — better typography, layout, color system, and micro-interactions.

| ID | Story | Status | File |
|----|-------|--------|------|
| PP-E7-S1 | Color system: establish brand palette (primary, accent, semantic colors) in Tailwind config | ⬜ | `tailwind.config.ts`, `src/index.css` |
| PP-E7-S2 | Typography: consistent heading scale, font weight, line-height across all pages | ⬜ | `src/index.css`, global styles |
| PP-E7-S3 | Sidebar redesign: icons + labels, active state, hover animations, collapse support | ⬜ | `src/components/layout/AppLayout.tsx` |
| PP-E7-S4 | Dashboard redesign: KPI cards with trend indicators, better grid layout | ⬜ | `src/pages/Dashboard.tsx` |
| PP-E7-S5 | Data tables: alternating rows, better hover states, column alignment | ⬜ | `src/components/shared/DataTable.tsx` |
| PP-E7-S6 | Loading skeletons: replace spinners with shimmer skeleton cards | ⬜ | `src/components/shared/Skeleton.tsx` (new) |
| PP-E7-S7 | Empty states: illustrated empty state with CTA for Orders, Drivers, Vehicles, Depots | ⬜ | `src/components/shared/EmptyState.tsx` |
| PP-E7-S8 | Toast notifications: success/error toasts for all CRUD + plan actions | ⬜ | `src/components/shared/Toast.tsx` (new) |
| PP-E7-S9 | Status badges: unified, color-coded system (green/amber/red/blue) across all entities | ⬜ | `src/components/shared/StatusBadge.tsx` |
| PP-E7-S10 | Button variants: primary, secondary, danger — consistent across all pages | ⬜ | `src/components/shared/Button.tsx` (new) |
| PP-E7-S11 | Planning page redesign: cleaner plan result display with route cards | ⬜ | `src/pages/Planning.tsx` |
| PP-E7-S12 | Mobile responsiveness: all pages usable on tablet/mobile | ⬜ | all page files |
| PP-E7-VER | All pages reviewed in browser; no layout breaks; visually consistent | ⬜ | Manual review |

---

## Phase 4 – Epic Status

| Epic | Name | Status | GENSPEC |
|------|------|--------|---------|
| P4-E1 | Multi-Region & Per-Tenant DB Routing | ⬜ Not Started | `DEV_SPEC_P4_fleet_intelligence_platform_v1.md` |
| P4-E2 | Partner APIs & Webhook Integration (ERP/WMS/TMS) | ⬜ Not Started | `DEV_SPEC_P4_fleet_intelligence_platform_v1.md` |
| P4-E3 | Capacity Marketplace | ⬜ Not Started | `DEV_SPEC_P4_fleet_intelligence_platform_v1.md` |
| P4-E4 | Governance, Compliance & Audit | ⬜ Not Started | `DEV_SPEC_P4_fleet_intelligence_platform_v1.md` |
| P4-E5 | Multi-Day Strategic Planning & Scenario Simulator | ⬜ Not Started | `DEV_SPEC_P4_fleet_intelligence_platform_v1.md` |

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

### Phase 2-4 — Detailed Specs

| File | Phases | Ready? |
|------|--------|--------|
| `DEV_SPEC_P2_autonomous_dispatch_v2.md` | Phase 2 | ✅ Implemented |
| `DEV_SPEC_P3_adaptive_multi_agent_v1.md` | Phase 3 | ✅ Implemented |
| `DEV_SPEC_P4_fleet_intelligence_platform_v1.md` | Phase 4 | ✅ Spec (5 epics, ready to implement) |
| `DEV_SPEC_P3_P4_multi_agent_enterprise_v1.md` | Phase 3 & 4 | ⚠️ Superseded — use P3/P4 individual specs above |

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

*Last updated: 2026-04-30*
