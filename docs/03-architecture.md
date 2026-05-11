# FleetOpsX — System Architecture

**Version:** 3.0 (Phase 6 — Redesign V2)

---

## 1. Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│  Dispatcher (React SPA)  │  Driver (PWA)  │  Customer (/track)│
└──────────────┬───────────┴────────┬────────┴──────────────────┘
               │ HTTPS              │ HTTPS
┌──────────────▼───────────────────▼──────────────────────────┐
│                   FastAPI (Render Web Service)                │
│  Auth · Orders · Planning · Tracking · Chat · Admin          │
│  WebSocket /ws/dispatch/{tenant_id}                          │
└────┬──────┬────────┬──────────┬───────────┬─────────────────┘
     │      │        │          │           │
  Postgres  Redis  MongoDB   Celery      AI Provider
 (Supabase)(Render  (Atlas)  Worker     (Claude/GPT/Gemini)
            KV)              (Render)
```

---

## 2. Backend (FastAPI)

**Repo:** `FleetOpsX-API/`  
**Runtime:** Python 3.11 · Uvicorn · Gunicorn  
**Deploy:** Render Web Service (Docker)

### Key modules

| Module | Path | Responsibility |
|--------|------|----------------|
| Auth | `app/api/v1/auth.py` | JWT login, register, superadmin tenant list |
| Admin | `app/api/v1/admin.py` | Tenant DB routes, AI provider registry |
| Planning | `app/api/v1/planning.py` | Day plan, multi-scenario AI plan, confirm |
| Chat | `app/api/v1/chat.py` | AI chat with fleet context injection |
| Tracking | `app/api/v1/tracking.py` | GPS ping, live positions |
| Governance | `app/api/v1/governance.py` | Audit log, RBAC, data export |
| Planner | `app/planners/` | OR-Tools baseline + AI scenario engine |
| LLM Factory | `app/core/llm_factory.py` | Provider routing (Claude/GPT/Gemini) |
| AI Provider | `app/core/ai_provider.py` | Global registry + per-tenant override |
| Workers | `app/workers/` | Celery tasks, APScheduler |

---

## 3. Frontend (React + Vite)

**Repo:** `FleetOpsX-UI/`  
**Stack:** React 18 · TypeScript · Tailwind · TanStack Query · Zustand  
**Deploy:** Render Static Site (Docker)

### Key pages

| Route | Page | Role |
|-------|------|------|
| `/login` | Login | All |
| `/select-tenant` | TenantSelector | Superadmin only |
| `/` | Dashboard | Dispatcher, Admin |
| `/planning` | Planning (multi-scenario) | Dispatcher |
| `/plan-history` | Plan History | Dispatcher |
| `/admin` | Admin Console | Superadmin |
| `/admin/ai-providers` | AI Provider Management | Superadmin |
| `/settings/users` | User Management | Tenant Admin |
| `/driver` | Driver View (PWA) | Driver |
| `/track/:code` | Customer Tracking | Public |

---

## 4. Database Architecture

### Primary: PostgreSQL (Supabase)

Shared multi-tenant DB with `tenant_id` on every table.  
Per-tenant dedicated DB routing is implemented (P4-E1) — activate for enterprise tenants.

**Key tables:**

```
tenants → tenant_configs → users
       → orders → route_plans → routes → route_stops
       → drivers → driver_availability
       → vehicles → vehicle_status
       → depots
       → chat_messages
       → audit_log_entries
       → rbac_roles
       → agent_suggestions → agent_logs
       → scenario_runs → scenario_results
       → plan_history (P5-E3 — new)
       → ai_provider_configs (P5-E1 — new)
       → user_invitations (P5-E8 — new)
```

### Secondary: MongoDB Atlas (P5-E3)

Stores plan history, AI reasoning chains, and memory entries.  
Reason: flexible JSON, no schema migrations needed for evolving plan memory structure.

**Collections:**

```
plan_sessions
  _id, tenant_id, plan_date, baseline_plan, scenario_plans[],
  chosen_scenario, dispatcher_notes, status, ai_reasoning_chain,
  created_at, confirmed_at

plan_memories
  _id, tenant_id, weekday, zone, driver_id, pattern,
  source_plan_id, weight, created_at

```

**Connection:** `MONGODB_URL` env var. `app/core/mongo.py` manages the motor async client.

> Until MongoDB Atlas is provisioned, plan history uses the `plan_history` Postgres table with JSONB columns. MongoDB migration documented in `docs/10-decisions-and-open-questions.md`.

### Cache: Redis (Render Key Value)

- GPS position cache: `gps:{driver_id}` → TTL 5 min
- Plan session cache: `plan:{tenant_id}:{date}` → TTL 1 hour
- WebSocket pub/sub channels: `dispatch:{tenant_id}`
- DB route cache: `route_cache` dict in memory (refreshed every 60s from Postgres)

---

## 5. AI Architecture

### Provider Registry

```
AI_PROVIDERS (global, superadmin manages)
  ├── claude-sonnet-4-6  (default for: planning, analysis)
  ├── claude-haiku-4-5   (default for: chat)
  ├── gpt-4o             (optional)
  └── gemini-pro         (optional)

TENANT_AI_CONFIG (per-tenant override)
  ├── use_platform_default: true/false
  ├── planning_model: str
  ├── chat_model: str
  └── api_key_encrypted: str (Fernet)
```

### Planning AI Flow (P5-E2)

```
POST /plan/ai-scenarios
  1. OR-Tools → baseline plan (deterministic, ~2s)
  2. LLM receives: baseline + orders + drivers + natural language constraints
  3. LLM generates 4 scenario adjustments:
     - fastest, economical, balanced, driver_availability
  4. Each scenario returned with: KPIs, reasoning, confidence
  5. Dispatcher selects one → POST /plan/confirm
  6. Confirmed plan stored in plan_sessions (MongoDB/Postgres)
  7. Email/notification sent: "Plan ready"
```

### Chat AI Flow (P5-E4)

```
POST /chat/message
  1. Fleet context builder fetches: today's orders, drivers, GPS, active plan
  2. System prompt injected: product rules + fleet context + last 10 messages
  3. LLM generates structured response (JSON → typed card)
  4. Slash command router: /plan, /reroute, /explain, /status, /forecast
  5. Follow-up suggestions generated
  6. Response stored in chat_messages
```

---

## 6. Superadmin Architecture (P5-E0)

### Auth flow

```
POST /auth/login
  if user.role == 'superadmin':
    response includes: { ...token_data, tenants: [{ id, name, slug, order_count }] }
  else:
    response: standard token

Frontend:
  if isSuperadmin → redirect to /select-tenant
  Tenant selected → store effectiveTenantId in auth store
  All API calls: X-Acting-Tenant-Id: {effectiveTenantId} header added

Backend (deps.py):
  get_effective_tenant_id(user, x_acting_tenant_id):
    if user.role == 'superadmin' and x_acting_tenant_id:
      return x_acting_tenant_id  (validated against tenant table)
    return user.tenant_id
```

### Impersonation safety

- All superadmin-initiated mutations write to audit_log with `actor_role = superadmin`
- Read-only mode: frontend disables all mutating actions (POST/PUT/DELETE)
- Confirmation dialog before any mutating action while in superadmin context
- Exit tenant → back to /select-tenant (effectiveTenantId cleared)

---

## 7. Infrastructure

| Service | Provider | Plan |
|---------|----------|------|
| API | Render Web Service | Free → Starter |
| Celery Worker | Render Web Service (sh workaround) | Free |
| Static Frontend | Render Static Site | Free |
| Database | Supabase PostgreSQL | Free |
| Redis | Render Key Value | Free |
| MongoDB | MongoDB Atlas | Free (512MB) |
| AI (LLM) | Anthropic / OpenAI / Google | Pay-per-use |
| Email | Resend / SendGrid | Free tier |
| SMS (future) | Twilio | Pay-per-use |

---

## 8. Phase 6 Architecture — Redesign V2

### Navigation Structure (Frontend)

```
Sidebar (redesigned)
├── OPERATIONS (section label)
│   ├── Dashboard      /
│   ├── Orders         /orders
│   ├── Planning       /planning
│   ├── Live Map       /map
│   ├── Plan History   /plan-history
│   └── Drivers        /drivers
├── INSIGHTS (section label)
│   ├── Analytics      /analytics
│   └── Settings       /settings
└── Fleet & Platform (collapsible)
    ├── Vehicles       /vehicles
    ├── Depots         /depots
    ├── Integrations   /integrations
    ├── Marketplace    /marketplace
    ├── Governance     /governance
    ├── Scenarios      /scenarios
    ├── AI Providers   /admin/ai-providers
    └── Team           /team
```

### Topbar Architecture

```
[Page Title + Breadcrumb]   [⌘K Global Search]   [Ask AI] [🔔 Bell] [Avatar]
                                    ↓                  ↓
                            CommandPalette        ChatDrawer (420px slide-over)
                            (Modal overlay)       (replaces FAB + /chat page)
```

### Chat Architecture (V2 — MongoDB-backed)

```
TopBar "Ask AI" click
  → ChatDrawer opens (420px right panel)
  → GET /chat/conversations → conversation list
  → Select or create conversation
  → GET /chat/conversations/{id}/messages → message history
  → User sends message
  → POST /chat/conversations/{id}/messages
      Backend:
        1. Fetch last 10 messages from MongoDB
        2. Build [{role, content}] array for LLM messages param
        3. Inject fleet context in system message
        4. LLM generates structured response
        5. Save AI message to MongoDB
        6. Return response
  → ChatDrawer renders message
```

**MongoDB Collections (Motor async):**

```
chat_conversations
  _id: ObjectId
  tenant_id: str
  user_id: str
  title: str (auto-derived from first message)
  created_at: datetime
  updated_at: datetime

chat_messages
  _id: ObjectId
  conversation_id: ObjectId (ref → chat_conversations)
  role: "user" | "assistant"
  content: str
  card_data: dict | null  (structured card for AI responses)
  created_at: datetime
```

### New API Endpoints (Phase 6)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/analytics/kpi-trend?days=7` | Daily KPI time-series for sparklines |
| GET | `/plan/timeline?date=YYYY-MM-DD` | Gantt data: driver schedules + stop times |
| GET | `/chat/conversations` | List user's conversations |
| POST | `/chat/conversations` | Create new conversation |
| GET | `/chat/conversations/{id}/messages` | Fetch all messages in conversation |
| POST | `/chat/conversations/{id}/messages` | Send message + get AI reply |
| DELETE | `/chat/conversations/{id}` | Delete conversation |

### New/Extended Data Models (Phase 6)

**Order (extended):**
```python
priority: str = "NORMAL"          # LOW | NORMAL | HIGH | CRITICAL
value: Decimal | None             # monetary value of delivery
time_window_start: time | None    # earliest delivery time (already exists — confirm)
time_window_end: time | None      # latest delivery time (already exists — confirm)
```

**Driver (computed fields in response):**
```python
utilization_pct: float   # today's assigned hours / available hours * 100
performance_score: float # rolling 30-day on-time delivery % (0–100)
```

**KPI Trend response:**
```json
[
  {
    "date": "2026-05-05",
    "orders_count": 42,
    "on_time_pct": 91.3,
    "active_drivers": 8,
    "fleet_efficiency": 78.5
  }
]
```

**Route Timeline response:**
```json
[
  {
    "driver_id": "uuid",
    "driver_name": "Ravi Kumar",
    "stops": [
      { "order_id": "uuid", "address": "...", "start_time": "09:00", "end_time": "09:30", "status": "DELIVERED" }
    ]
  }
]
```

### Command Palette (⌘K) Architecture

```
KeyboardEvent (⌘K / Ctrl+K)
  → CommandPalette modal opens
  → Input: debounced search
  → Results (no API calls — all from local cache):
      pages[]       — static nav items
      orders[]      — from React Query cache (queryKey: ['orders', ...])
      drivers[]     — from React Query cache (queryKey: ['drivers'])
  → Select item → navigate / open modal
```

### Frontend Component Map (Phase 6 additions)

```
src/
  components/
    layout/
      Sidebar.tsx          (redesigned — 3-section nav + collapsible)
      Topbar.tsx           (search + Ask AI button)
      ChatDrawer.tsx       (NEW — replaces ChatPanel + ChatPage)
      CommandPalette.tsx   (NEW — ⌘K global search)
    dashboard/
      KpiCard.tsx          (NEW — value + sparkline + delta)
      LiveOpsTicker.tsx    (NEW — scrolling alert strip)
      RouteGantt.tsx       (NEW — horizontal timeline)
      AtRiskInbox.tsx      (NEW — at-risk panel with AI chips)
      FleetAvailability.tsx(NEW — 3 availability cards)
  pages/
    Dashboard.tsx          (full redesign)
    Orders.tsx             (tab filters + new columns)
    Drivers.tsx            (avatar + score bars)
    Analytics.tsx          (sparkline KPI cards)
    Settings.tsx           (color mode picker)
    Planning.tsx           (scenario comparison cards)
    LiveMap.tsx            (driver feed panel)
    PlanHistory.tsx        (timeline card list)
  api/
    chat.ts                (NEW — conversations CRUD)
    analytics.ts           (extended — kpi-trend endpoint)
    planning.ts            (extended — timeline endpoint)
```

---

## 9. Security (unchanged)

| Concern | Implementation |
|---------|----------------|
| Auth | JWT (HS256), 24h expiry |
| Tenant isolation | `tenant_id` on every query, enforced in deps |
| API keys at rest | Fernet encryption (JWT_SECRET_KEY derived) |
| CORS | Restricted to UI domain in production |
| Audit | Append-only audit_log_entries for all mutations |
| GDPR | Data export endpoint, configurable retention sweep |
| Webhooks | HMAC-SHA256 signed payloads |
