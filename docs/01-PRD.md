# FleetOpsX — Product Requirements Document (PRD)

**Version:** 2.0  
**Status:** Phase 5 planning  
**Owner:** Seenivasan (Platform Admin)

---

## 1. Product Vision

FleetOpsX is a **multi-tenant AI-powered fleet dispatch SaaS** that gives logistics companies a single platform to plan routes, track drivers, manage capacity, and make smarter decisions — all driven by AI that learns from every operation.

**Tagline:** *From chaos to clarity — AI that dispatches, learns, and adapts.*

---

## 2. Target Users

| Role | Description | Access level |
|------|-------------|--------------|
| **Platform Admin** (Seenivasan) | Manages all tenants, AI models, system config | Superadmin — cross-tenant |
| **Tenant Admin** | Manages their company: users, depots, drivers, settings | Admin — own tenant only |
| **Dispatcher** | Day-to-day: plan routes, monitor deliveries, use AI chat | Dispatcher — own tenant |
| **Driver** | Mobile: see stops, mark delivered, auto GPS | Driver — own stops only |
| **Packaging Team** | View orders assigned to their depot, mark packed | Custom — limited |
| **Read-only** | Observers: stakeholders, finance | Readonly — own tenant |

---

## 3. Completed Phases

| Phase | Feature set | Status |
|-------|-------------|--------|
| Phase 1 | MVP: auth, orders, drivers, vehicles, depots, rule-based planner | ✅ Done |
| Phase 2 | OR-Tools VRPTW, LangGraph agent, GPS tracking, SLA alerts | ✅ Done |
| Phase 3 | Multi-agent, analytics ETL, AI suggestions, monitor agent | ✅ Done |
| Phase P | Chat AI, Excel export/import, live map, 3-plan options, UI overhaul | ✅ Done |
| Phase 4 | Multi-region DB, webhooks, capacity marketplace, governance, scenarios | ✅ Done |

---

## 4. Phase 5 — Product Roadmap

### P5-E0: Superadmin Auth + Tenant Management
**Priority: 1 — Blocks everything else**

Platform admin (superadmin role) gets a dedicated post-login tenant selector screen. They can:
- View all tenants in a card grid
- Enter any tenant in "Act as tenant" mode (full access with confirmation prompts)
- Enter any tenant in "Read-only" mode (view only, no mutations)
- See a persistent banner while acting as a tenant with one-click exit
- Every mutating action as superadmin triggers a "Are you sure?" confirmation

---

### P5-E1: AI Provider Management
**Priority: 2**

Platform admin configures a global AI model registry. Tenants can optionally add their own models.

**Global registry (admin only):**
- Add/edit/remove providers: Claude (Anthropic), GPT-4o (OpenAI), Gemini Pro (Google)
- Set one "platform default" for each task type: planning, chat, analysis
- API keys encrypted at rest (Fernet, same key as DB routing)

**Per-task model routing:**
- `planning` → configurable (default: Claude Sonnet)
- `chat` → configurable (default: Claude Haiku — fast)
- `analysis` → configurable (default: Claude Sonnet)

**Tenant override:**
- Tenants can add their own API keys for the same providers
- Tenants can choose: use our default, or use their own key
- Tenants cannot add new providers to the global registry

---

### P5-E2: AI Planning — Multi-Scenario with Memory
**Priority: 3**

Replace single-plan output with an AI-powered multi-scenario planner:

1. **OR-Tools generates baseline** (fast, deterministic)
2. **AI analyzes** the baseline and generates 4 scenario plans:
   - `fastest` — minimize total time, ignore cost
   - `economical` — minimize fuel + driver cost  
   - `balanced` — time/cost balance (current default)
   - `driver_availability` — maximises driver utilisation
3. **Dispatcher picks one** from a card comparison view
4. **Natural language constraints** — dispatcher types "avoid NH-44 today, keep Ravi in North zone" and AI adjusts
5. **Plan confirmed** → stored with metadata, shown in history

**Plan Memory system:**
- Each confirmed plan is stored with: orders, assignments, chosen scenario, dispatcher notes
- Before generating a new plan, AI reads last 5 confirmed plans for the same weekday
- Notes from failed/modified plans become constraints: "Driver 3 was late on northern zone on Mondays"
- Plans evolve — each new plan is smarter than the last

---

### P5-E3: Plan History + Feedback Loop
**Priority: 4**

Dedicated "Plan History" tab in the Planning page:
- List of all confirmed plans (date, scenario chosen, # orders, % on-time)
- Click any plan to see: assignments, AI reasoning, KPIs
- Add notes to past plans: "Driver 5 was overloaded", "North zone traffic on Fridays"
- Mark a plan as "failed" with reason — this becomes memory input
- Compare two plans side-by-side
- Storage: PostgreSQL JSON columns (MongoDB migration path documented in architecture)

---

### P5-E4: Chat UI Redesign (DataGuard-style)
**Priority: 5**

Rebuild the AI chat from a basic panel to a structured, context-aware assistant:

**Position:** Bottom-right corner floating button → slide-over panel (420px) → expandable to full-page

**Design system:** Pure black (#0a0a0a) background, purple accent (#7c3aed), monochrome cards

**Features:**
- **Structured response cards** (not raw markdown) — each response is a typed card: summary, data table, action buttons, follow-up chips
- **Slash commands** with autocomplete: `/plan`, `/reroute`, `/explain`, `/status`, `/forecast`, `/compare`, `/export`
- **Thinking steps** shown as strikethrough progress while AI works
- **Follow-up chips** (↳ suggested next questions) after every response
- **Context footer** on every response: "Based on 47 orders · today · 3 drivers active"
- **AI system prompt** injects fleet context + product rules (no generic responses)

**System prompt rules (always sent):**
- You are FleetOpsX AI — a fleet dispatch assistant. Only answer questions about fleet operations, routes, drivers, orders, and deliveries.
- Always refer to real data from the tenant's fleet context provided below.
- Never suggest tools, platforms, or methods outside FleetOpsX.
- Keep responses concise. Use structured data when showing lists.

---

### P5-E5: Driver Mobile PWA
**Priority: 6**

Convert the driver view to an installable Progressive Web App:
- `manifest.json` + service worker → "Add to Home Screen"
- Photo proof of delivery (camera capture on DELIVERED tap)
- "Open in Maps" navigation deep-link (Google Maps / Waze)
- Offline stop list (IndexedDB cache, syncs when back online)
- Battery-aware GPS (reduce ping frequency when battery < 20%)

---

### P5-E6: Real-time WebSocket Layer
**Priority: 7**

Replace all polling with WebSocket push:
- `ws://api/v1/ws/dispatch/{tenant_id}` — single connection per tenant
- Events pushed: GPS position updates, order status changes, new at-risk alerts
- Redis pub/sub as the event bus between FastAPI instances
- Notification drawer in UI with alert history

---

### P5-E7: Customer Tracking Portal
**Priority: 8**

Public-facing delivery tracking (no login):
- `/track/{short_code}` — shows driver position on map + ETA
- Twilio SMS: "Your delivery is 10 min away"
- Embeddable JS widget for partner websites

---

### P5-E8: User Management (Tenant Admin)
**Priority: 9**

Tenant admins manage their own users:
- Create users: name, email, role, permission level
- Roles: dispatcher, driver, packaging_team, readonly, tenant_admin
- Custom permissions per user (RBAC)
- Invite via email (magic link)
- Deactivate users
- View activity log per user

---

## 5. AI System Prompt (FleetOpsX Chat)

```
You are FleetOpsX AI — the fleet operations assistant for {tenant_name}.

Your role: Help dispatchers plan routes, analyse deliveries, monitor driver performance, and resolve operational issues.

Always use the fleet context provided below. Never invent data.
Only answer questions relevant to fleet operations. If asked about unrelated topics, redirect politely.

Response format:
- Keep answers concise and action-oriented
- Use structured data (tables, lists) when showing driver/order/route information
- End with 2-3 suggested follow-up questions relevant to the data shown
- Always cite what data you used: "Based on X orders today · Y drivers active"

Fleet context:
{fleet_context}
```

---

## 6. Non-functional Requirements

| Requirement | Target |
|-------------|--------|
| API response time (p95) | < 300ms (excluding AI endpoints) |
| AI planning response | < 30s (with notification on completion) |
| Uptime | 99.5% |
| Multi-tenant isolation | Complete — no cross-tenant data leakage |
| GDPR | Data export on request, configurable retention |
| Mobile driver app | Works offline, < 200ms GPS ping |
