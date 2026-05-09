# FleetOpsX — Functional Requirements

---

## P5-E0: Superadmin Auth + Tenant Management

### FR-SA-1: Superadmin login
- User with `role = superadmin` logs in with email + password
- Response includes standard JWT token + list of all active tenants: `[{ id, name, slug, order_count_today, driver_count }]`
- Frontend detects `role = superadmin` → redirects to `/select-tenant` instead of `/`

### FR-SA-2: Tenant selector
- Shows all tenants as cards: name, slug, today's order count, driver count, active status
- Search/filter by tenant name
- Each card has two actions: "Act as tenant" and "Read-only"
- Platform management links: AI Providers, All Tenants, System Health

### FR-SA-3: Acting as tenant
- Superadmin's effective tenant_id stored in auth store
- All API calls include `X-Acting-Tenant-Id: {id}` header
- Backend `get_effective_tenant_id()` dep returns the acting tenant_id for superadmin
- Persistent banner shown at all times: tenant name, mode (read/full), exit button

### FR-SA-4: Read-only mode
- All buttons that trigger mutations (POST/PUT/DELETE) are visually disabled
- Attempting to trigger a mutation shows toast: "Read-only mode — switch to Full Access"
- Toggle in banner switches mode (switching to Full Access shows confirmation)

### FR-SA-5: Superadmin confirmation
- Any mutating action while in superadmin context shows confirmation modal
- Modal text: "You are about to [action] for tenant [name]. This modifies live data."
- Action is only executed after explicit confirmation
- All superadmin mutations logged to audit_log with `actor_role = superadmin`

---

## P5-E1: AI Provider Management

### FR-AI-1: Global provider registry (superadmin)
- `/admin/ai-providers` — CRUD for AI provider configs
- Fields: provider_name (claude/openai/gemini), model_id, api_key (encrypted), task_type (planning/chat/analysis), is_active, is_platform_default
- Only one provider per task_type can be `is_platform_default = true`

### FR-AI-2: Per-task default selection
- Superadmin selects which model is default for: planning, chat, analysis
- All tenants without override use this default
- Default changes take effect on next request (no restart needed)

### FR-AI-3: Tenant AI config
- Tenant can view the platform default (model name shown, no key visible)
- Tenant can add their own API key for the same provider
- Tenant can override per-task model from their own list or platform defaults
- Tenant cannot add new provider types (only superadmin can)

### FR-AI-4: AI provider page (frontend)
- Route: `/admin/ai-providers` (superadmin only)
- Table: provider name, model ID, task type, is_default badge, key status (✓ set / ✗ missing)
- Actions: Add provider, Edit, Delete, Set as default per task
- Tenant settings page: "AI Model" section — choose from platform defaults or add own key

---

## P5-E2: AI Planning Multi-Scenario

### FR-PL-1: AI scenario generation
- `POST /plan/ai-scenarios` — accepts: date, natural_language_constraints (optional)
- Backend runs OR-Tools baseline first
- AI generates 4 scenarios from the baseline
- Returns: `{ baseline, scenarios: [fastest, economical, balanced, driver_availability], ai_reasoning }`
- Streaming support: client polls status while generation runs (Celery task)
- Email notification on completion

### FR-PL-2: Natural language constraints
- Dispatcher types: "keep Ravi in North zone, avoid NH-44 today"
- Constraints parsed by AI and injected as soft constraints into scenario generation
- Constraint acknowledgment shown in response: "Applied: zone lock for Ravi, route restriction NH-44"

### FR-PL-3: Scenario comparison UI
- Cards side-by-side: plan type, # orders, # routes, est time, est cost, AI confidence score
- Expand any card to see full route assignments
- Select one → confirmation dialog → plan committed

### FR-PL-4: Plan memory
- After plan confirmed, store in `plan_sessions`:
  - All 4 scenarios, chosen scenario, dispatcher notes, actual vs planned KPIs
- Before generating new plan, AI reads last 5 confirmed plans for same weekday
- Memory used as context: "On last 3 Mondays, Driver 5 was delayed in North zone"

---

## P5-E3: Plan History + Feedback

### FR-PH-1: Plan history tab
- Tab in Planning page: "Plan History"
- List: date, scenario chosen, # orders, # delivered, % on-time, notes count
- Click to expand: full assignment details, AI reasoning, KPI comparison

### FR-PH-2: Plan notes
- Dispatcher can add notes to any past plan
- Note types: `issue` (something went wrong), `improvement` (what to do next time), `general`
- Notes feed into AI planning memory for future plans

### FR-PH-3: Plan feedback
- After plan day ends, dispatcher can mark outcomes: on_time, delayed, failed
- System auto-populates from delivery completion data where available

---

## P5-E4: Chat UI (DataGuard-style)

### FR-CH-1: Chat panel position and modes
- Floating button: bottom-right, 56px circle, purple
- Click → slide-over panel (420px, right edge)
- Expand button → full-page overlay (centered, 800px max-width)
- Close → returns to floating button
- State persisted across navigation (panel stays open when switching pages)

### FR-CH-2: Entry state
- Shows personalized greeting: "Hi {first_name} — what would you like to know about your fleet today?"
- 3-4 contextual suggestions based on current fleet state (e.g., if 5 unassigned orders: "Why are 5 orders unassigned?")
- Slash command hint: "Type / for commands like /plan, /explain, /status"

### FR-CH-3: Slash commands
| Command | Description | Action |
|---------|-------------|--------|
| `/plan` | Generate today's AI plan | Calls POST /plan/ai-scenarios |
| `/reroute {driver}` | Reroute a specific driver | Calls POST /plan/replan |
| `/explain` | Explain current plan reasoning | Fetches plan reasoning from last plan |
| `/status` | Fleet status summary | Fetches live GPS + orders |
| `/forecast` | Tomorrow's volume forecast | Calls forecast agent |
| `/compare {date1} {date2}` | Compare two plans | Fetches plan history |
| `/export` | Export current plan to Excel | Calls GET /export/plan |
| `/atRisk` | Show at-risk deliveries | Calls GET /sla/at-risk |

### FR-CH-4: Structured response cards
- AI responses returned as structured JSON, rendered as typed React components
- Card types: summary, data_table, plan_scenarios, at_risk_list, draft_document, comparison_table
- Every response ends with 2-3 follow-up suggestion chips (↳ ...)
- Every response has context footer: "Based on {N} orders · {drivers} active · {time}"

### FR-CH-5: Thinking state
- While AI is working, show step-by-step progress:
  - ✓ Reading orders (strikethrough when done)
  - ✓ Checking GPS
  - ○ Analysing... (spinning when current)
- "Streaming · {N}s · Click stop to cancel" at bottom

### FR-CH-6: System prompt rules
Always sent as system context:
- Only answer fleet operations questions
- Always use the provided fleet context data (never invent numbers)
- Structured output format
- Suggest follow-ups relevant to the data shown
- End every response with context citation

---

## P5-E8: User Management

### FR-UM-1: Tenant admin user CRUD
- `/settings/users` — list all users in tenant
- Create user: name, email, role (dispatcher/driver/packaging_team/readonly/tenant_admin), custom permissions
- Deactivate user (soft delete, retains audit history)
- Edit user role and permissions

### FR-UM-2: Roles
| Role | Default permissions |
|------|---------------------|
| tenant_admin | All tenant permissions |
| dispatcher | plan:generate, plan:read, order:write, driver:manage |
| driver | stop:update, order:read |
| packaging_team | order:read (own depot only) |
| readonly | order:read, plan:read |

### FR-UM-3: Custom permissions
- Permission checkboxes shown per user
- Saved to `rbac_roles` table (existing P4-E4 system)
