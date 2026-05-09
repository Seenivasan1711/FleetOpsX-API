# FleetOpsX — Testing Strategy

---

## 1. Backend Testing

### Unit tests (`tests/unit/`)
- Auth service: login, superadmin tenant list, token generation
- `get_effective_tenant_id()` dep: superadmin with header, superadmin without header, regular user
- `llm_factory.py`: provider selection by task_type, fallback chain
- Fernet encrypt/decrypt for API keys

### Integration tests (`tests/integration/`)
- Full login flow for superadmin → verify tenants[] in response
- `GET /admin/tenants` — requires superadmin role
- `GET /admin/ai-providers` — CRUD round-trip
- `POST /plan/ai-scenarios` — queues Celery task, returns task_id
- `POST /chat/message` — returns structured response card
- Tenant isolation: user from tenant A cannot access tenant B's orders

### Running tests
```bash
pytest tests/ -v
pytest tests/unit/ -v        # fast
pytest tests/integration/ -v # requires DB
```

---

## 2. Frontend Testing

### Component tests (Vitest + React Testing Library)
- `TenantSelector.tsx` — renders tenant cards, search filter, action buttons
- `SuperadminBanner.tsx` — shows tenant name, mode toggle, exit button
- `ConfirmActionModal.tsx` — renders, calls onConfirm, calls onCancel
- `Login.tsx` — superadmin redirect to /select-tenant after login

### E2E tests (manual checklist — no Playwright yet)
See Section 4.

---

## 3. Manual Verification Checklist Per Epic

### P5-E0: Superadmin Auth
- [ ] Login as `superadmin@fleetopsx.com` / `admin1234`
- [ ] Redirected to `/select-tenant` (not dashboard)
- [ ] Tenant cards show: name, slug, order count, driver count
- [ ] Search filters tenant cards in real time
- [ ] "Act as tenant" → banner appears with tenant name
- [ ] "Read-only" mode → mutation buttons disabled; toast on attempt
- [ ] Toggle Full Access → confirmation modal → banner updates
- [ ] Perform an order update while acting → audit log entry has `actor_role = superadmin`
- [ ] "Exit Tenant" → back to `/select-tenant`, banner gone

### P5-E1: AI Provider Management
- [ ] `/admin/ai-providers` accessible only to superadmin
- [ ] Add provider with API key → key stored encrypted, key_set shows ✓
- [ ] Set as default for planning → chat requests use old default, planning uses new
- [ ] Tenant settings page shows platform default model name (not key)
- [ ] Tenant adds own key → requests use tenant key for that task

### P5-E2: AI Planning
- [ ] "AI Plan" button opens NL constraint input
- [ ] Submit → loading state with thinking steps animation
- [ ] 4 scenario cards appear with correct KPIs
- [ ] Select scenario → confirmation dialog → plan committed
- [ ] Email notification received on completion

### P5-E3: Plan History
- [ ] Plan history tab shows past confirmed plans
- [ ] Click plan → full assignment detail, AI reasoning visible
- [ ] Add note (issue/improvement/general) → saved and shown
- [ ] New AI plan incorporates memory from past plans (verify in AI reasoning output)

### P5-E4: Chat UI
- [ ] Floating button visible bottom-right on all pages
- [ ] Click → slide-over panel opens (420px)
- [ ] Expand → full-page modal
- [ ] Entry state shows personalized greeting + suggestion chips
- [ ] Type `/` → slash command autocomplete appears
- [ ] `/atRisk` → at_risk_list card rendered correctly
- [ ] `/plan` → triggers scenario generation (polling)
- [ ] Follow-up chips clickable → pre-fill input
- [ ] Context footer shows correct order count and time
- [ ] Thinking steps shown during AI processing

---

## 4. Seed Data for Testing

Run `python scripts/seed_data.py` which creates:
- `superadmin@fleetopsx.com` / `admin1234` (role: superadmin)
- `admin@demo.com` / `demo1234` (tenant: Demo Corp, role: admin)
- `dispatcher@demo.com` / `demo1234` (tenant: Demo Corp, role: dispatcher)
- `driver@demo.com` / `demo1234` (tenant: Demo Corp, role: driver)
- 50 demo orders for today's date
- 5 demo drivers with routes

---

## 5. CI Notes

No CI pipeline configured yet. Pre-push checklist:
1. `pytest tests/unit/ -v` passes
2. `npm run build` (UI) passes with no type errors
3. Manual smoke test: login → dashboard → planning → chat
