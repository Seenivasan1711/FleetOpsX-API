# FleetOpsX — Progress Tracker

> **This file tracks Phase 6 (Redesign V2) actively.**  
> For Phase 1–5 history, see `../PROGRESS_TRACKER.md`.

---

## Quick Status

```
Last Updated  : 2026-05-11
Current Phase : Phase 6 — UI/UX Redesign V2
Branch        : redesign/v2-ux (local only — push to GitHub before PR)
Reference     : claude.ai/design/p/019e0e94
Status        : Implementation complete — polish + push pending
Next Action   : push redesign/v2-ux to origin (both repos), then open PR
Blocker       : None
```

---

## Phase 5 Summary (All Complete ✅)

| Epic | Name | Status |
|------|------|--------|
| P5-E0 | Superadmin Auth + Tenant Management | ✅ Done |
| P5-E1 | AI Provider Management | ✅ Done |
| P5-E2 | AI Planning — Multi-Scenario + Memory | ✅ Done |
| P5-E3 | Plan History + Feedback Loop | ✅ Done |
| P5-E4 | Chat UI Redesign (FAB + slash commands) | ✅ Done |
| P5-E5 | Driver Mobile PWA | ✅ Done |
| P5-E6 | Real-time WebSocket Layer | ✅ Done |
| P5-E7 | Customer Tracking Portal | ✅ Done |
| P5-E8 | User Management (Tenant Admin) | ✅ Done |

---

## Phase 6 — UI/UX Redesign V2

### Task Overview

| # | Task | Category | Status | Commit |
|---|------|----------|--------|--------|
| #5  | Design tokens, color palette, typography | Foundation | ✅ Done | `cf793c9` (UI) |
| #6  | Sidebar — OPERATIONS/INSIGHTS + Fleet & Platform collapsible | Shell | ✅ Done | `cf793c9` (UI) |
| #7  | Topbar — global search + Ask AI CTA | Shell | ✅ Done | `cf793c9` (UI) |
| #8  | Dashboard — KPI cards with sparklines | Dashboard | ✅ Done | `29b9dc9` (UI) |
| #9  | Dashboard — Live Ops ticker banner | Dashboard | ✅ Done | `29b9dc9` (UI) |
| #10 | Dashboard — Route Timeline Gantt | Dashboard | ✅ Done | `29b9dc9` (UI) |
| #11 | Dashboard — At-Risk Inbox + AI action chips | Dashboard | ✅ Done | `6a68d7b` (UI) |
| #12 | Dashboard — Fleet availability 3 cards | Dashboard | ✅ Done | `29b9dc9` (UI) |
| #13 | Dashboard — Quick Actions redesign (icon+title+subtitle) | Dashboard | ✅ Done | `29b9dc9` (UI) |
| #14 | Orders — tab filters + VALUE/PRIORITY/WINDOW columns | Pages | ✅ Done | `cf793c9` (UI) |
| #15 | AI Planning — scenario comparison + plan detail | Pages | ✅ Done | `cf793c9` (UI) |
| #16 | Live Map — driver feed panel + optimize button | Pages | ✅ Done | `1b2902e` (UI) |
| #17 | Plan History — clean card list with inline stats | Pages | ✅ Done | pre-existing |
| #18 | Drivers — avatars, score bars, status pills, utilization | Pages | ✅ Done | `cf793c9` (UI) |
| #19 | Analytics — sparkline KPI cards + utilization bars | Pages | ✅ Done | `72b1538` (UI) |
| #20 | Settings — color mode picker + alert toggles | Pages | ✅ Done | pre-existing |
| #21 | Ask AI drawer — wired to conversations API (MongoDB-aware) | Chat/AI | ✅ Done | `29b9dc9` (UI) |
| #22 | ⌘K global command palette | Shell | ✅ Done | `cf793c9` (UI) |
| #23 | BE audit — document existing Order/Driver fields | Backend | ✅ Done | `bdcde15` (API) |
| #24 | Animations & micro-interactions | Polish | 🟡 Partial | CSS done; number counters exist |
| #25 | Light mode audit | Polish | 🟡 Pending visual review | no code gaps |
| #26 | Git — push branches + PR | Close | ⬜ Manual step | push to origin |
| #27 | BE — Order: add value field + migration | Backend | ✅ Done | `bdcde15` (API) |
| #28 | BE — Driver: utilization_pct, performance_score | Backend | ✅ Done | `bdcde15` (API) |
| #29 | BE — Daily KPI trend endpoint | Backend | ✅ Done | `bdcde15` (API) |
| #30 | BE — Route timeline endpoint for Gantt | Backend | ✅ Done | `bdcde15` (API) |
| #31 | BE — MongoDB chat history CRUD | Backend | ✅ Done | `bdcde15` + `359c6b3` (API) |
| #32 | BE — Multi-turn AI context (history sent to LLM) | Backend | ✅ Done | `359c6b3` (API) |
| #33 | FE — Wire chat to MongoDB conversations API | Chat/AI | ✅ Done | `29b9dc9` (UI) |

---

### #5 — Foundation: Design Tokens & Typography

**Goal:** Establish the new visual system as CSS variables in `globals.css`.

| Story | Status | Notes |
|-------|--------|-------|
| New semantic color tokens (--c-bg, --c-surface, --c-elevated, --c-accent, --c-muted) | ⬜ | Already partially done — audit and extend |
| Typography scale (--text-xs through --text-2xl + --font-mono) | ⬜ | |
| Spacing scale and border-radius tokens | ⬜ | |
| Dark + light theme variants for all tokens | ⬜ | |
| page-slide-in animation + hover-lift keyframes | ⬜ | |

---

### #6 — Sidebar Redesign

**Goal:** Restructure nav into OPERATIONS / INSIGHTS / "Fleet & Platform" collapsible sections.

**OPERATIONS items:** Dashboard, Orders, Planning, Live Map, Plan History, Drivers  
**INSIGHTS items:** Analytics, Settings  
**Fleet & Platform (collapsible):** Vehicles, Depots, Integrations, Marketplace, Governance, Scenarios, AI Providers, Team

| Story | Status | Notes |
|-------|--------|-------|
| Section labels with uppercase tracking | ⬜ | |
| "Fleet & Platform" collapsible with ChevronDown/Up | ⬜ | |
| User profile footer (avatar initials, name, email, role pill) | ⬜ | |
| Active state highlight: left 2px accent bar | ⬜ | |
| Collapsed sidebar (icon-only mode) support | ⬜ | |

---

### #7 — Topbar Redesign

**Goal:** Add global search to topbar; "Ask AI" becomes the sole AI entry point.

| Story | Status | Notes |
|-------|--------|-------|
| Global search input (⌘K trigger) in center topbar | ⬜ | |
| "Ask AI" button — opens slide-over drawer (replaces FAB) | ⬜ | |
| Notification bell with badge count | ⬜ | |
| Page title + breadcrumb left side | ⬜ | |

---

### #8 — Dashboard: KPI Cards with Sparklines

**Goal:** Replace static stat boxes with animated KPI cards showing 7-day trend lines.

| Story | Status | Notes |
|-------|--------|-------|
| KPI card component: value, label, delta %, sparkline | ⬜ | Needs #29 BE endpoint |
| 4 cards: Orders Today, On-Time %, Active Drivers, Fleet Efficiency | ⬜ | |
| Recharts LineChart (thin, no axes, just the curve) | ⬜ | |
| Delta badge: green ↑ / red ↓ | ⬜ | |

---

### #9 — Dashboard: Live Ops Ticker

**Goal:** Scrolling horizontal alert strip below the KPI cards.

| Story | Status | Notes |
|-------|--------|-------|
| CSS marquee / JS scroll ticker | ⬜ | |
| Events: delayed orders, driver alerts, at-risk stops | ⬜ | |
| Click-to-dismiss per event | ⬜ | |

---

### #10 — Dashboard: Route Timeline Gantt

**Goal:** Horizontal Gantt showing each driver's stop schedule for today.

| Story | Status | Notes |
|-------|--------|-------|
| Recharts Gantt or custom SVG rows | ⬜ | Needs #30 BE endpoint |
| Driver row: colored blocks per stop, hover = stop detail | ⬜ | |
| Current time indicator line | ⬜ | |
| Click stop → Opens order detail | ⬜ | |

---

### #11 — Dashboard: At-Risk Inbox

**Goal:** Right-panel list of orders at risk of missing SLA with AI action chips.

| Story | Status | Notes |
|-------|--------|-------|
| At-Risk card: order ref, driver, ETA, risk reason | ⬜ | |
| AI action chips: "Reassign", "Notify customer", "Extend window" | ⬜ | |
| Click action → fires AI chat with pre-filled prompt | ⬜ | |

---

### #12 — Dashboard: Fleet Availability Cards

**Goal:** Replace single "Fleet Overview" table with 3 stat cards.

| Story | Status | Notes |
|-------|--------|-------|
| Drivers: Active / Total with donut ring | ⬜ | |
| Vehicles: Available / Total | ⬜ | |
| Efficiency: composite score with bar | ⬜ | |

---

### #13 — Dashboard: Quick Actions Redesign

**Goal:** Grid of 4-6 large action cards (icon + title + subtitle).

| Story | Status | Notes |
|-------|--------|-------|
| Card grid layout (2 or 3 cols) | ⬜ | |
| Actions: New Order, Plan Today, Assign Driver, View Map, Run Scenarios | ⬜ | |
| Hover lift animation | ⬜ | |

---

### #14 — Orders Page Redesign

**Goal:** Tab-based filter bar + new VALUE, PRIORITY, WINDOW columns.

| Story | Status | Notes |
|-------|--------|-------|
| Tab strip: All / Pending / In-Transit / Delivered / Failed | ⬜ | |
| VALUE column (currency display) | ⬜ | Needs #27 |
| PRIORITY column with colored badges | ⬜ | Needs #27 |
| TIME WINDOW column | ⬜ | Needs #27 |
| Bulk select + bulk actions (assign, cancel) | ⬜ | |

---

### #15 — AI Planning Redesign

**Goal:** Cleaner scenario selection UX with comparison cards and plan detail table.

| Story | Status | Notes |
|-------|--------|-------|
| 4 scenario cards with: name, icon, KPI grid, select button | ⬜ | |
| Selected card: accent border + shadow | ⬜ | |
| Plan detail table: driver, stops, distance, ETA | ⬜ | |
| AI confidence badge per scenario | ⬜ | |

---

### #16 — Live Map Redesign

**Goal:** Driver feed side panel + one-click live route optimization.

| Story | Status | Notes |
|-------|--------|-------|
| Right panel: driver list with live GPS ping time | ⬜ | |
| Driver status pills: Active / Idle / Off-route | ⬜ | |
| "Optimize Live" button → triggers immediate re-plan | ⬜ | |
| Map clustering for dense stop areas | ⬜ | |

---

### #17 — Plan History Redesign

**Goal:** Clean timeline of past plans with inline KPI stats.

| Story | Status | Notes |
|-------|--------|-------|
| Card list: date, scenario used, # orders, on-time %, star rating | ⬜ | |
| Click card → detail view with route table | ⬜ | |
| Notes indicator badge | ⬜ | |

---

### #18 — Drivers Page Redesign

**Goal:** Rich driver cards with avatars, performance scores, utilization bars.

| Story | Status | Notes |
|-------|--------|-------|
| Avatar circle: initials with color derived from name | ⬜ | |
| Performance score bar (0–100) | ⬜ | Needs #28 |
| Utilization bar: today's hours vs capacity | ⬜ | Needs #28 |
| Status pill: Active / Off-duty / On-leave | ⬜ | |

---

### #19 — Analytics Redesign

**Goal:** Replace plain charts with sparkline KPI cards and horizontal utilization bars.

| Story | Status | Notes |
|-------|--------|-------|
| 4 top KPI cards with 7-day sparklines | ⬜ | |
| Driver utilization horizontal bar chart | ⬜ | |
| On-time % trend line | ⬜ | |
| Route efficiency heatmap by day of week | ⬜ | |

---

### #20 — Settings Redesign

**Goal:** Visual color mode picker + structured alert preference toggles.

| Story | Status | Notes |
|-------|--------|-------|
| Color mode: System / Light / Dark picker with preview swatches | ⬜ | |
| Alert toggles: SLA breach, driver offline, plan complete | ⬜ | |
| Save confirmation toast | ⬜ | |

---

### #21 — Ask AI Drawer Panel

**Goal:** Remove floating FAB + /chat page. "Ask AI" topbar button opens slide-over drawer.

| Story | Status | Notes |
|-------|--------|-------|
| Slide-over drawer (right side, 420px) with conversation list | ⬜ | |
| New Conversation button | ⬜ | |
| Conversation history from MongoDB (grouped: Today / Yesterday / Past 7 days) | ⬜ | |
| Message bubbles: user right, AI left with card renderer | ⬜ | |
| Slash command autocomplete | ⬜ | |
| Remove FAB from AppShell | ⬜ | |
| Remove /chat route from AppRoutes | ⬜ | |
| Remove "Chat AI" from sidebar nav | ⬜ | |

---

### #22 — ⌘K Command Palette

**Goal:** Global search across orders, drivers, and pages — no extra API calls.

| Story | Status | Notes |
|-------|--------|-------|
| ⌘K / Ctrl+K keyboard listener | ⬜ | |
| Modal overlay with search input | ⬜ | |
| Results: pages (static), orders (React Query cache), drivers (React Query cache) | ⬜ | |
| Keyboard navigation (↑↓ + Enter) | ⬜ | |
| Recent items section when input is empty | ⬜ | |

---

### #23 — Backend Audit: Order/Driver Fields

**Goal:** Document all existing Order and Driver API response fields before extending.

| Story | Status | Notes |
|-------|--------|-------|
| List all Order model fields (Postgres + schema) | ⬜ | |
| List all Driver model fields (Postgres + schema) | ⬜ | |
| Identify gaps vs redesign requirements | ⬜ | |
| Document findings — unblock #27 and #28 | ⬜ | |

---

### #24 — Animations & Micro-interactions

| Story | Status | Notes |
|-------|--------|-------|
| page-slide-in on all pages (already present — audit) | ⬜ | |
| Hover lift on cards | ⬜ | |
| Number counter animation on KPI cards | ⬜ | |
| Skeleton loaders on all async sections | ⬜ | |
| Toast enter/exit transitions | ⬜ | |

---

### #25 — Light Mode Audit

| Story | Status | Notes |
|-------|--------|-------|
| All new components render correctly in light theme | ⬜ | |
| ChatPanel hardcoded dark values replaced with CSS vars | ⬜ | |
| Contrast ratios pass WCAG AA | ⬜ | |

---

### #26 — Git Commits + PR

| Story | Status | Notes |
|-------|--------|-------|
| Structured commits: one per module/task | ⬜ | |
| PR on redesign/v2-ux → main with full description | ⬜ | |

---

### #27 — BE: Order Fields

**Goal:** Add `priority`, `value`, `time_window_start`, `time_window_end` to Order model.

| Story | Status | Notes |
|-------|--------|-------|
| Alembic migration — new columns | ⬜ | Blocked by #23 |
| Update OrderIn / OrderOut schemas | ⬜ | |
| Update `GET /orders` response | ⬜ | |
| Update `POST /orders` + `PUT /orders/{id}` | ⬜ | |

---

### #28 — BE: Driver Fields

**Goal:** Add `utilization_pct` and `performance_score` to Driver response.

| Story | Status | Notes |
|-------|--------|-------|
| Compute utilization_pct from today's route assignments | ⬜ | Blocked by #23 |
| Compute performance_score from historical on-time % | ⬜ | |
| Return in DriverOut schema | ⬜ | |

---

### #29 — BE: KPI Trend Endpoint

**Goal:** `GET /analytics/kpi-trend?days=7` — returns time-series for dashboard sparklines.

| Story | Status | Notes |
|-------|--------|-------|
| Endpoint returning daily: orders_count, on_time_pct, active_drivers, fleet_efficiency | ⬜ | |
| Cached (Redis, TTL 1h) | ⬜ | |

---

### #30 — BE: Route Timeline Endpoint

**Goal:** `GET /plan/timeline?date=YYYY-MM-DD` — Gantt data per driver.

| Story | Status | Notes |
|-------|--------|-------|
| Returns: [{driver_id, driver_name, stops: [{order_id, address, start_time, end_time, status}]}] | ⬜ | |
| Derived from existing route_plans + route_stops | ⬜ | |

---

### #31 — BE: MongoDB Chat History

**Goal:** Motor async client + ChatConversation / ChatMessage collections + CRUD API.

| Story | Status | Notes |
|-------|--------|-------|
| `app/core/mongo.py` — Motor client setup | ⬜ | |
| ChatConversation collection: {_id, tenant_id, user_id, title, created_at, updated_at} | ⬜ | |
| ChatMessage collection: {_id, conversation_id, role, content, card_data, created_at} | ⬜ | |
| `GET /chat/conversations` — list user's conversations | ⬜ | |
| `POST /chat/conversations` — create new conversation | ⬜ | |
| `GET /chat/conversations/{id}/messages` — fetch messages | ⬜ | |
| `POST /chat/conversations/{id}/messages` — send message + AI reply | ⬜ | |
| `DELETE /chat/conversations/{id}` — delete conversation | ⬜ | |

---

### #32 — BE: Multi-turn AI Context

**Goal:** Send last N conversation messages to LLM for context-aware replies.

| Story | Status | Notes |
|-------|--------|-------|
| Fetch last 10 messages from MongoDB on each request | ⬜ | Blocked by #31 |
| Format as [{role, content}] array for LLM messages param | ⬜ | |
| Inject fleet context in system message | ⬜ | |

---

### #33 — FE: Wire Chat to MongoDB API

**Goal:** Replace localStorage chat persistence with MongoDB-backed API.

| Story | Status | Notes |
|-------|--------|-------|
| `src/api/chat.ts` — conversations CRUD API client | ⬜ | Blocked by #31, #32, #21 |
| Ask AI drawer loads conversation list from API | ⬜ | |
| New conversation: POST to API, use returned ID | ⬜ | |
| Messages: stream from API, auto-save | ⬜ | |
| Delete conversation from API | ⬜ | |
| Remove localStorage fallback | ⬜ | |
