# FleetOpsX – Project Blueprint & Execution Plan

_Autonomy for every fleet_

This document is the **single source of truth** for starting FleetOpsX.
It is written so it can be used:

- As a **Cursor / AI coding tool context file**
- As a **PM → Engineering handoff doc**
- As a **backlog seed** (epics, stories, phases)

---

## 1. Vision & Product Overview

### 1.1 Vision

FleetOpsX is a **multi-tenant Agentic AI platform** that:

- Centralizes fleet operations (orders, drivers, vehicles, routes)
- Uses AI and optimization to plan & re-plan routes and driver allocation
- Evolves from **rule-based planning → autonomous, learning, multi-agent system**
- Serves multiple industries (parcel logistics, dairy distribution, grocery, etc.) using one canonical model and tenant-specific configuration.

**Tagline:** _Autonomy for every fleet_

---

## 2. High-Level Strategy

### 2.1 Build Strategy

1. Start with a **modular monolith** (FastAPI + Postgres + Redis) that is:
   - Cleanly separated into domain modules (orders, fleet, planning, tracking, notifications)
   - Easy to later split into microservices by extracting modules
2. Use a **single shared database** with `tenant_id` on all core tables for **multi-tenancy**.
   - Later, support optional per-tenant DBs (for large enterprise/on-prem) via a connection routing layer.
3. Implement planning logic in phases:
   - **Phase 1:** Simple rule-based planning in plain Python
   - **Phase 2:** Upgrade to LangGraph/agentic workflows internally
   - **Phase 3:** Add multi-agent behavior using e.g. CrewAI/AutoGen or extended LangGraph
   - **Phase 4:** Scale to full fleet intelligence platform (multi-region, marketplace, etc.)
4. Use **adapters** for customer-specific onboarding/data models, but keep **internal canonical data model** stable.

---

## 3. Target Users & Tenants

### 3.1 Personas

- **Ops Manager / Fleet Coordinator**
- **Driver**
- **Business Owner / CXO**
- **Integrator / IT Admin**

### 3.2 Example Tenant Types

- **Parcel Logistics Tenant** (e.g., “Amazon-style” last-mile)
- **Dairy Logistics Tenant** (milk routes, recurring drops)
- **Other verticals** (grocery, pharma, etc.)

Each tenant is represented by a `Tenant` entity with config for:

- Vertical type (`business_vertical`)
- Capacity metrics (weight, volume, crates)
- Time window styles
- Constraints enabled (chilled, fragile, etc.)

---

## 4. Architecture Overview

### 4.1 System Style

- **Modular Monolith (Phase 1–2)**
  - Single FastAPI app
  - Monorepo style
  - Internal modules for each domain
- **Microservice-ready Design (Phase 3–4)**
  - Clear module boundaries
  - Planner and Tracking can be extracted as separate services
  - DB-level multi-tenancy remains consistent

### 4.2 Core Components (Conceptual)

- **API & Gateway**
  - FastAPI application with routers per domain
  - Auth & tenant resolution middleware
- **Domain Modules (inside monolith)**
  - `orders` – orders/delivery jobs
  - `fleet` – drivers & vehicles
  - `calendar` – shifts, availability, depot info
  - `planning` – planning/orchestration/agents
  - `tracking` – location & status updates
  - `notifications` – emails/SMS/WhatsApp
  - `auth` – users, roles, tenant mapping
  - `common` – shared utilities, DB session management
- **Data & Infra**
  - Postgres + PostGIS
  - Redis (cache, queues)
  - Message Queue (can start with Redis or simple DB polling; Kafka/RabbitMQ later)
  - External APIs: Maps/routing (Google Maps / OpenRouteService), SMS/email
- **Agent & Optimization Layer**
  - Rule-based planner (Phase 1)
  - LangGraph-based planner (Phase 2)
  - Multi-agent layer (CrewAI/AutoGen or extended LangGraph) (Phase 3)
  - Strategic planning & marketplace logic (Phase 4)

---

## 5. Tech Stack

### 5.1 Backend

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy + Alembic for migrations
- **Workers / Async Tasks:** Celery or RQ (backed by Redis)

### 5.2 Agentic / AI

- **Phase 1:** Plain Python planner, optional LLM for explanations
- **Phase 2:** LangGraph (on top of LangChain) for tool-calling, workflow graphs
- **Phase 3:** Add CrewAI/AutoGen (or keep LangGraph multi-agent patterns)
- **LLM Provider:** OpenAI (configurable via env)

### 5.3 Database & Caching

- **DB:** PostgreSQL + PostGIS
- **Cache / Queue:** Redis

### 5.4 Frontend

- **Ops Dashboard:** React + TypeScript
- **Driver App:** React Native or responsive mobile web (Phase 1–2 can start with web only)

### 5.5 Deployment

- **Phase 1:** Docker + Docker Compose
- **Phase 2+:** Ready for Kubernetes
- Use `.env`/configuration files for DB/Redis/API keys

---

## 6. Multi-Tenancy Design

### 6.1 Model

- Single shared DB:
  - Every core table has `tenant_id`
  - All queries filter by `tenant_id`
- Tenants:
  - `tenants` table
  - `tenant_config` table for vertical/behavior options
- Tenant resolution:
  - From auth token (user → tenant)
  - Optionally from subdomain later

### 6.2 Tenant Config

Fields (example, not exhaustive):

- `business_vertical` – `LAST_MILE_PARCEL`, `DAIRY_MILK`, etc.
- `time_window_style` – strict, slots, recurring schedule
- `capacity_unit` – `WEIGHT_KG`, `VOLUME_L`, `CRATES`
- `features_enabled` – flags for advanced capabilities
- `labels_overrides` – optional UI label customizations

### 6.3 Future Hybrid Strategy

In future, some tenants may be migrated to:

- Dedicated DB
- On-prem or VPC deployment

Code should support a simple interface like:

```python
def get_db_for_tenant(tenant_id) -> Session:
    # for MVP: always return shared DB session
    # future: route some tenants to dedicated DBs
```

---

## 7. Canonical Data Model (High Level)

Core tables (all with `id` & `tenant_id`):

- `tenants`
- `tenant_configs`
- `depots`
- `drivers`
- `vehicles`
- `customers` (delivery recipients, shops, etc.)
- `orders` / `delivery_jobs`
- `routes` (per driver+vehicle per day)
- `route_stops` (points on a route tied to orders)
- `route_plans` (daily plan summary)
- `events` (delivery events, delays, breakdowns, status)
- `users` (platform users)
- `user_roles`

**Key concept:**
External customer’s “weird data model” is normalized into these canonical tables through ingestion adapters.

---

## 8. Phases (Product & Technical)

### Phase 1 – Assisted Dispatch (MVP)

**Goal:** Centralize operations, rule-based planning, human in the loop.

- Single-tenant-ish but technically multi-tenant ready
- Basic CRUD for tenants, drivers, vehicles, depots, orders
- **Simple rule-based planner:**
  - Assign closest available driver/vehicle within shift/time window
  - Simple route & ETA via Maps API
- **Dashboard UI:** unassigned vs assigned orders, per-driver view
- **Driver:** simple web view for assigned jobs + status updates
- No LangGraph yet. No multi-agent yet.

### Phase 2 – Autonomous Dispatch & Optimization

**Goal:** Automated route optimization & re-planning.

- Real-time (or batch) tracking integration
- Planner uses OR-Tools VRPTW for route optimization
- Planner wrapped as LangGraph agent calling:
  - DB tools
  - Routing service
  - OR-Tools optimization
- Auto-assignment with configuration-driven guardrails
- SLA risk detection & alerts
- Mongo/warehouse still optional; metrics via Postgres OK.

### Phase 3 – Adaptive Multi-Agent System

**Goal:** Learning & proactive planning.

- **Multi-agent roles:**
  - **Planner Agent**
  - **Monitor Agent** (anomaly detection)
  - **Forecast Agent** (volume & delay predictions)
  - **Explainer Agent** (decision transparency)
- Historical data → train models for:
  - travel-time adjustment
  - delay risk
- Multi-day planning support
- Enhanced dashboards and analytics

### Phase 4 – Fleet Intelligence Platform & Marketplace

**Goal:** Enterprise scale, multi-region, capacity marketplace.

- Multi-region, multi-depot optimizations
- Dedicated tenants (DB, on-prem, etc.)
- APIs for partners (ERP, WMS, TMS, etc.)
- Marketplace logic: share excess capacity across tenants
- Strong SLAs, governance, compliance, auditing

---

## 9. Epics & Stories (Backlog Structure)

This section can be used directly as tasks in Jira/Linear/etc.

### 9.1 Phase 1 – MVP (Suggested Duration: 6–8 weeks)

#### Epic P1-E1: Project Setup & Infrastructure

- **Story P1-E1-S1:** Initialize monorepo structure
  - Create `backend/`, `frontend/`, `infra/`, `docs/`
- **Story P1-E1-S2:** Setup FastAPI app skeleton
  - Health check endpoint
  - Basic logging & config
- **Story P1-E1-S3:** Setup Postgres + Redis via Docker Compose
- **Story P1-E1-S4:** Add Alembic migrations pipeline
- **Story P1-E1-S5:** Setup base CI (formatting, tests, build)

#### Epic P1-E2: Multi-Tenant Foundations

- **Story P1-E2-S1:** Define `Tenant` and `TenantConfig` models and migrations
- **Story P1-E2-S2:** Implement middleware to resolve `tenant_id` from auth (for now, simple user → tenant mapping)
- **Story P1-E2-S3:** Ensure all core tables include `tenant_id`
- **Story P1-E2-S4:** Implement tenant-aware DB session dependency (FastAPI dependency that injects tenant-aware session)

#### Epic P1-E3: Core Domain Models & APIs (Monolith)

- **Story P1-E3-S1:** Implement drivers module (CRUD + list/filter)
- **Story P1-E3-S2:** Implement vehicles module
- **Story P1-E3-S3:** Implement depots module
- **Story P1-E3-S4:** Implement orders (delivery jobs) module
- **Story P1-E3-S5:** Implement calendar (driver shifts) module
- **Story P1-E3-S6:** Implement users + auth (simple JWT-based)

#### Epic P1-E4: Planner v1 (Rule-Based)

- **Story P1-E4-S1:** Define `PlannerInterface` with method e.g. `plan_day(tenant_id, date)`
- **Story P1-E4-S2:** Implement `RuleBasedPlanner`:
  - For each unassigned order, pick nearest available driver within shift
- **Story P1-E4-S3:** Implement `/plan/day` endpoint that:
  - Validates input
  - Calls `PlannerInterface`
  - Writes assignments & routes (simple one-stop-per-route initially)
- **Story P1-E4-S4:** Integrate Maps API client for distance/ETA estimation (used inside planner)

#### Epic P1-E5: Web UI – Operations Dashboard

- **Story P1-E5-S1:** Setup React + TypeScript project
- **Story P1-E5-S2:** Implement login + tenant switching (simple implementation)
- **Story P1-E5-S3:** Implement Orders screen (list, filters, create/edit)
- **Story P1-E5-S4:** Implement Drivers/Vehicles/Depots management screens
- **Story P1-E5-S5:** Implement Planning view:
  - Show unassigned vs assigned orders
  - Button “Generate Plan”
  - Show suggested assignments per driver

#### Epic P1-E6: Driver View (Basic)

- **Story P1-E6-S1:** Implement simple driver web/mobile view:
  - Show today’s assigned stops in order
- **Story P1-E6-S2:** Implement status updates: accepted, en_route, completed, issue
- **Story P1-E6-S3:** Wire driver updates back to backend (update route stop status)

#### Epic P1-E7: Synthetic Data & Demo

- **Story P1-E7-S1:** Create synthetic data generator for Bangalore:
  - 1–3 depots, 50 drivers, 200 orders
- **Story P1-E7-S2:** Add CLI script to load sample data into DB
- **Story P1-E7-S3:** Create demo scenario & script for investors

### 9.2 Phase 2 – Autonomous Dispatch & Optimization

#### Epic P2-E1: OR-Tools Optimization Service

- **Story P2-E1-S1:** Create planning/optimizer module wrapping OR-Tools VRPTW
- **Story P2-E1-S2:** Implement `optimize_routes(orders, vehicles, constraints)` function
- **Story P2-E1-S3:** Add unit tests with small VRP instances

#### Epic P2-E2: LangGraph Agent Integration

- **Story P2-E2-S1:** Setup LangGraph dependency and base agent runtime
- **Story P2-E2-S2:** Define tools for agent:
  - `fetch_unassigned_orders`
  - `fetch_available_drivers_vehicles`
  - `call_optimizer`
  - `write_assignments`
- **Story P2-E2-S3:** Implement Planner Agent with LangGraph flow
- **Story P2-E2-S4:** Wire `/plan/day` endpoint to use Agent instead of direct rule-based logic (keep old logic behind feature flag)

#### Epic P2-E3: Tracking & Re-planning

- **Story P2-E3-S1:** Implement Tracking API to receive periodic GPS pings
- **Story P2-E3-S2:** Store tracking data & derive current driver/vehicle location
- **Story P2-E3-S3:** Implement “replan” endpoint `/plan/replan` for single driver or full fleet
- **Story P2-E3-S4:** Agent watches events (new orders, delays) and triggers re-planning suggestions

#### Epic P2-E4: SLA Risk Alerts

- **Story P2-E4-S1:** Compute SLA risk (based on current ETA vs time window)
- **Story P2-E4-S2:** Notification service sends alerts to Ops UI and via email/SMS
- **Story P2-E4-S3:** UI shows “At-risk deliveries” panel

### 9.3 Phase 3 – Multi-Agent & Learning

#### Epic P3-E1: Historical Data & Analytics

- **Story P3-E1-S1:** Define analytic schema (or separate schema) for historical runs
- **Story P3-E1-S2:** Schedule ETL jobs to move operational data → analytics tables
- **Story P3-E1-S3:** Build basic dashboards (via BI or custom UI)

#### Epic P3-E2: Multi-Agent Roles

- **Story P3-E2-S1:** Implement Forecast Agent:
  - Uses historical data to estimate demand per region/time
- **Story P3-E2-S2:** Implement Monitor Agent:
  - Listens to events/metrics; identifies anomalies
- **Story P3-E2-S3:** Implement Explainer Agent:
  - Given a plan + logs, explains decisions in human language

#### Epic P3-E3: Proactive Planning

- **Story P3-E3-S1:** Use Forecast Agent outputs as input to Planner Agent (pre-day planning)
- **Story P3-E3-S2:** Implement proactive re-planning suggestions before SLA breaches
- **Story P3-E3-S3:** UI: “Suggested actions” feed for Ops Manager

### 9.4 Phase 4 – Enterprise & Marketplace

(High-level only; details to refine later)

- Multi-region support
- Per-tenant DB & on-prem deployment mode
- Marketplace logic for cross-tenant capacity sharing
- Advanced compliance/audit features

---

## 10. Coding & Design Guidelines (Team Alignment)

- **Keep business logic inside service modules**, not in routers.
- **No customer-specific logic in core domain models:**
  - All tenant-specific differences via `TenantConfig` + adapters
- **`PlannerInterface` is the main abstraction:**
  - Improvement of logic must not break API endpoints.
  - Use feature flags when replacing rule-based planner with LangGraph agent.
- **Monolith first, but modular:**
  - Each domain in its own folder with routers, schemas, services, models.
  - Easy to later extract planning, tracking, notifications into separate services.

---

## 11. Immediate Next Steps (for Engineering Team)

1. **Create repo** with this file as `/docs/project_blueprint.md`.
2. **Implement Phase 1 – Epics P1-E1 to P1-E3 first:**
   - Project setup
   - Multi-tenant foundation
   - Core domain models & APIs
3. **Parallel track:**
   - Frontend skeleton (P1-E5)
   - Synthetic data & demo (P1-E7)
4. **Once Phase 1 backend + minimal UI is working:**
   - Connect planner (P1-E4)
   - Validate end-to-end MVP flow
5. **From this point,** the team can simply follow the epic/story list as backlog tickets.

---

**End of FleetOpsX Project Blueprint – v1**
