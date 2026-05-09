# FleetOpsX — Phase 5 Progress Tracker

> **This file tracks Phase 5 only.**  
> For Phase 1–4 history, see `../PROGRESS_TRACKER.md`.

---

## Quick Status

```
Last Updated  : 2026-05-09
Current Phase : Phase 5 — Platform Intelligence & UX
Current Epic  : P5-E0 — Superadmin Auth + Tenant Management (code complete, pending manual verification)
Next Action   : Verify P5-E0 manually then start P5-E1 AI Provider Management
Blocker       : None
```

---

## Phase 5 Epic Overview

| Epic | Name | Priority | Status | Est. Effort |
|------|------|----------|--------|-------------|
| P5-E0 | Superadmin Auth + Tenant Management | 1 | 🟡 In Progress | 1 day |
| P5-E1 | AI Provider Management Page | 2 | ⬜ Not Started | 1 day |
| P5-E2 | AI Planning — Multi-Scenario + Memory | 3 | ⬜ Not Started | 3 days |
| P5-E3 | Plan History + Feedback Loop | 4 | ⬜ Not Started | 2 days |
| P5-E4 | Chat UI Redesign (DataGuard-style) | 5 | ⬜ Not Started | 2 days |
| P5-E5 | Driver Mobile PWA | 6 | ⬜ Not Started | 2 days |
| P5-E6 | Real-time WebSocket Layer | 7 | ⬜ Not Started | 2 days |
| P5-E7 | Customer Tracking Portal | 8 | ⬜ Not Started | 1 day |
| P5-E8 | User Management (Tenant Admin) | 9 | ⬜ Not Started | 2 days |

---

## P5-E0: Superadmin Auth + Tenant Management

### Backend

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E0-BE-1 | `GET /admin/tenants` — list all tenants with today's order count | ✅ | `app/api/v1/admin.py` |
| P5-E0-BE-2 | Update `POST /auth/login` — if superadmin, include tenants[] in response | ✅ | `app/api/v1/auth.py` |
| P5-E0-BE-3 | `get_effective_tenant_id()` dep — reads X-Acting-Tenant-Id header for superadmin | ✅ | `app/api/deps.py` |
| P5-E0-BE-4 | Seed superadmin user (`superadmin@fleetopsx.com` / `admin1234`) in seed script | ✅ | `scripts/seed_data.py` |
| P5-E0-BE-VER | Login as superadmin → tenants list returned; impersonation header accepted | ⬜ | Manual test |

### Frontend

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E0-FE-1 | Update `User` type — add `role: 'superadmin'` + `tenants?` field | ✅ | `src/types/index.ts` |
| P5-E0-FE-2 | Update `auth.store.ts` — add `effectiveTenantId`, `isReadOnly`, `isSuperadmin` | ✅ | `src/store/auth.store.ts` |
| P5-E0-FE-3 | Update `client.ts` interceptor — add `X-Acting-Tenant-Id` header when set | ✅ | `src/api/client.ts` |
| P5-E0-FE-4 | `TenantSelector.tsx` — full-page tenant picker (cards, search, act/read buttons) | ✅ | `src/pages/TenantSelector.tsx` |
| P5-E0-FE-5 | `SuperadminBanner.tsx` — amber banner: tenant name, mode toggle, exit | ✅ | `src/components/layout/SuperadminBanner.tsx` |
| P5-E0-FE-6 | `ConfirmActionModal.tsx` — "Are you sure?" for superadmin mutations | ✅ | `src/components/shared/ConfirmActionModal.tsx` |
| P5-E0-FE-7 | Update `AppRoutes.tsx` — add `/select-tenant` route | ✅ | `src/routes/AppRoutes.tsx` |
| P5-E0-FE-8 | Update `Login.tsx` — redirect superadmin to `/select-tenant` after login | ✅ | `src/pages/Login.tsx` |
| P5-E0-FE-9 | Update `AppShell.tsx` — show SuperadminBanner if isSuperadmin + effectiveTenantId | ✅ | `src/components/layout/AppShell.tsx` |
| P5-E0-FE-VER | Login as superadmin → see tenant list → select → banner shown → exit works | ⬜ | Manual test |

---

## P5-E1: AI Provider Management

### Backend

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E1-BE-1 | `AiProviderConfig` model | ⬜ | `app/models/ai_provider.py` |
| P5-E1-BE-2 | Alembic migration for `ai_provider_configs` | ⬜ | `alembic/versions/...` |
| P5-E1-BE-3 | Schemas: `AiProviderIn`, `AiProviderOut`, `AiProviderUpdate` | ⬜ | `app/schemas/ai_provider.py` |
| P5-E1-BE-4 | `GET/POST/PUT/DELETE /admin/ai-providers` (superadmin) | ⬜ | `app/api/v1/admin.py` |
| P5-E1-BE-5 | `GET/PATCH /settings/ai-config` (tenant — view platform default + set own) | ⬜ | `app/api/v1/tenants.py` |
| P5-E1-BE-6 | Update `llm_factory.py` — read from `ai_provider_configs` table instead of env | ⬜ | `app/core/llm_factory.py` |

### Frontend

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E1-FE-1 | `src/api/aiProviders.ts` — CRUD API client | ⬜ | `src/api/aiProviders.ts` |
| P5-E1-FE-2 | `/admin/ai-providers` page — provider table + add/edit/delete + set default | ⬜ | `src/pages/AiProviders.tsx` |
| P5-E1-FE-3 | Settings page "AI Model" section — tenant config panel | ⬜ | `src/pages/Settings.tsx` |

---

## P5-E2: AI Planning Multi-Scenario

### Backend

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E2-BE-1 | `POST /plan/ai-scenarios` endpoint — Celery task, returns task_id | ⬜ | `app/api/v1/planning.py` |
| P5-E2-BE-2 | `AIPlannerService` — runs OR-Tools baseline + LLM scenario generation | ⬜ | `app/services/ai_planner_service.py` |
| P5-E2-BE-3 | `ai_scenario_task` Celery task | ⬜ | `app/workers/tasks.py` |
| P5-E2-BE-4 | NL constraint parser — inject into scenario generation | ⬜ | `app/planners/constraint_parser.py` |
| P5-E2-BE-5 | `POST /plan/confirm-scenario` — commits chosen scenario to route_plans | ⬜ | `app/api/v1/planning.py` |
| P5-E2-BE-6 | Plan memory reader — fetch last 5 same-weekday plans as LLM context | ⬜ | `app/services/plan_memory_service.py` |
| P5-E2-BE-7 | Email notification on plan completion (Resend/SendGrid) | ⬜ | `app/core/notifications.py` |

### Frontend

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E2-FE-1 | Planning page — "AI Plan" button → NL constraint input → loading state | ⬜ | `src/pages/Planning.tsx` |
| P5-E2-FE-2 | Scenario card comparison component (4 cards, KPIs, select) | ⬜ | `src/components/planning/ScenarioCards.tsx` |
| P5-E2-FE-3 | Plan polling hook — polls task status every 3s until done | ⬜ | `src/hooks/usePlanPolling.ts` |

---

## P5-E3: Plan History + Feedback

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E3-BE-1 | `plan_history` Postgres table + model | ⬜ | `app/models/plan_history.py` |
| P5-E3-BE-2 | `plan_notes` table + model | ⬜ | `app/models/plan_notes.py` |
| P5-E3-BE-3 | `GET /plan/history` + `GET /plan/history/{id}` + `POST /plan/history/{id}/notes` | ⬜ | `app/api/v1/planning.py` |
| P5-E3-FE-1 | "Plan History" tab in Planning page | ⬜ | `src/pages/Planning.tsx` |
| P5-E3-FE-2 | History list + detail view + notes panel | ⬜ | `src/components/planning/PlanHistory.tsx` |
| P5-E3-MON-1 | MongoDB Atlas free cluster provisioned | ⬜ | Atlas dashboard |
| P5-E3-MON-2 | `app/core/mongo.py` — Motor async client | ⬜ | `app/core/mongo.py` |
| P5-E3-MON-3 | Migrate plan_history to MongoDB collections | ⬜ | `app/services/plan_session_service.py` |

---

## P5-E4: Chat UI Redesign

| ID | Story | Status | File |
|----|-------|--------|------|
| P5-E4-FE-1 | Floating chat button (bottom-right, purple, 56px) | ⬜ | `src/components/chat/ChatButton.tsx` |
| P5-E4-FE-2 | Chat slide-over panel (420px, full-height, dark) | ⬜ | `src/components/chat/ChatPanel.tsx` |
| P5-E4-FE-3 | Full-page chat modal (expand button) | ⬜ | `src/components/chat/ChatFullPage.tsx` |
| P5-E4-FE-4 | Entry state: greeting + contextual suggestions | ⬜ | `src/components/chat/ChatEntryState.tsx` |
| P5-E4-FE-5 | Slash command autocomplete dropdown | ⬜ | `src/components/chat/SlashMenu.tsx` |
| P5-E4-FE-6 | Thinking state component (steps + streaming indicator) | ⬜ | `src/components/chat/ThinkingState.tsx` |
| P5-E4-FE-7 | Response card renderer (typed cards: summary, table, plan, at_risk) | ⬜ | `src/components/chat/ResponseCard.tsx` |
| P5-E4-FE-8 | Follow-up chips component | ⬜ | `src/components/chat/FollowUpChips.tsx` |
| P5-E4-FE-9 | Context footer component | ⬜ | `src/components/chat/ContextFooter.tsx` |
| P5-E4-BE-1 | Update chat endpoint — return structured JSON response cards | ⬜ | `app/api/v1/chat.py` |
| P5-E4-BE-2 | Slash command router (backend intent detection) | ⬜ | `app/services/chat_service.py` |
| P5-E4-BE-3 | Updated system prompt with product rules | ⬜ | `app/services/chat_context_service.py` |
| P5-E4-GCS-1 | Update globals.css — Obsidian theme (#0a0a0a bg, #7c3aed accent) | ⬜ | `src/styles/globals.css` |

---

## P5-E5 through P5-E8 (Planned, not started)

These epics are planned in the PRD (`docs/01-PRD.md`) and architecture (`docs/03-architecture.md`).  
Story-level tracker will be added here when each epic starts.
