# FleetOpsX — Go-Live Checklist

---

## Infrastructure

- [ ] Render Web Service — upgrade API from Free to Starter ($7/mo) for no cold starts
- [ ] Render Static Site — frontend deployed and serving
- [ ] Supabase — production project created, `DATABASE_URL` set in Render env
- [ ] Redis — Render Key Value provisioned, `REDIS_URL` set
- [ ] MongoDB Atlas — M0 free cluster provisioned, `MONGODB_URL` + `MONGODB_DB` set
- [ ] Custom domain configured on Render (API + frontend)
- [ ] SSL certificate active (auto via Render)

## Environment Variables (Render)

- [ ] `JWT_SECRET_KEY` — strong random string (not default)
- [ ] `DATABASE_URL` — Supabase Transaction Pooler URL (port 6543)
- [ ] `REDIS_URL` — Render KV URL
- [ ] `MONGODB_URL` — Atlas connection string
- [ ] `MONGODB_DB` — `fleetopsx`
- [ ] `ANTHROPIC_API_KEY` — set
- [ ] `DEFAULT_PLANNING_MODEL` — `claude-sonnet-4-6`
- [ ] `DEFAULT_CHAT_MODEL` — `claude-haiku-4-5-20251001`
- [ ] `DEFAULT_ANALYSIS_MODEL` — `claude-sonnet-4-6`
- [ ] `RESEND_API_KEY` — email notifications
- [ ] `FRONTEND_URL` — for CORS allowlist
- [ ] `ENVIRONMENT` — `production`

## Database

- [ ] Alembic migrations run on production DB (`alembic upgrade head`)
- [ ] Seed script run for superadmin user (`superadmin@fleetopsx.com`)
- [ ] At least one demo tenant seeded
- [ ] Indexes verified on `tenant_id`, `plan_date`, `status` columns

## Security

- [ ] CORS restricted to production frontend domain only
- [ ] `JWT_SECRET_KEY` is not the default value
- [ ] All AI provider API keys are encrypted in DB (not stored in env except platform default)
- [ ] HTTPS enforced (no HTTP allowed)
- [ ] Superadmin credentials documented and stored in secure password manager
- [ ] Audit log tested: superadmin mutation shows `actor_role = superadmin`

## Frontend

- [ ] `VITE_API_BASE_URL` points to production API URL
- [ ] Production build has no `console.log` leaking sensitive data
- [ ] Error boundaries present for chat and planning pages
- [ ] Demo GPS mode is clearly labelled (not mistakable for real GPS)

## Functional Smoke Test

- [ ] Login as superadmin → tenant selector shown
- [ ] Select tenant → banner shown → dashboard loads
- [ ] Login as dispatcher → dashboard loads, no tenant selector
- [ ] Create order → order appears in list
- [ ] Run AI plan → scenarios generated → select one → plan confirmed
- [ ] Open chat → `/atRisk` → structured response card rendered
- [ ] Live Map → GPS positions shown (real or demo)
- [ ] Export plan to Excel → file downloads

## Phase 5 Epic Status

- [ ] P5-E0: Superadmin Auth + Tenant Management — complete
- [ ] P5-E1: AI Provider Management — complete
- [ ] P5-E2: AI Planning Multi-Scenario — complete
- [ ] P5-E3: Plan History + Feedback — complete
- [ ] P5-E4: Chat UI Redesign — complete
- [ ] P5-E5: Driver Mobile PWA — complete
- [ ] P5-E6: Real-time WebSocket Layer — complete
- [ ] P5-E7: Customer Tracking Portal — complete
- [ ] P5-E8: User Management (Tenant Admin) — complete

## Post-Launch

- [ ] Set up Render health check alert (HTTP 200 on `/health`)
- [ ] Set up Supabase backup schedule
- [ ] Monitor Anthropic API usage dashboard for cost spikes
- [ ] Share demo tenant credentials with first customer
