# FleetOpsX — Decisions & Open Questions

---

## Decided

### D-001: Superadmin role uses existing `users` table
**Decision:** `role = 'superadmin'` on the existing `User` model. No separate admin user table.  
**Reason:** Zero new infrastructure; `require_platform_admin` dep already checks this role.

### D-002: AI provider keys use Fernet encryption
**Decision:** Fernet symmetric encryption, key derived from `JWT_SECRET_KEY`.  
**Reason:** Same pattern as P4-E1 per-tenant DB routing; consistent; no new secrets needed.

### D-003: Postgres JSONB now, MongoDB Atlas later for plan history
**Decision:** Plan history stored in Postgres `plan_history` table with JSONB columns for `ai_reasoning`, `scenarios_json`, `memory_used`. MongoDB Atlas migration happens in P5-E3.  
**Reason:** MongoDB Atlas free tier setup takes time and isn't needed for P5-E0/E1/E2. JSONB handles the data fine for now.  
**Migration path:** P5-E3 provisions Atlas free cluster, creates `plan_sessions` + `plan_memories` collections, new plans write to MongoDB, old Postgres records remain queryable via `plan_history` table.

### D-004: AI scenario generation is async (Celery)
**Decision:** `POST /plan/ai-scenarios` returns `task_id` immediately; client polls `GET /plan/task-status/{id}`.  
**Reason:** LLM generation takes 10–30s; synchronous HTTP would timeout on Render free tier.

### D-005: Different AI models per task type (Option B)
**Decision:** Separate model selection for planning, chat, and analysis.  
**Reason:** Planning benefits from more capable models (sonnet); chat needs lower latency (haiku); analysis may need specific capabilities.

### D-006: Tenant can add own API keys but not new providers
**Decision:** Superadmin defines the provider list (claude/openai/gemini); tenants add their own keys for those providers and choose their active model.  
**Reason:** Keeps platform control over which AI vendors are integrated; tenants can optimise cost.

### D-007: OR-Tools generates baseline, AI generates scenarios
**Decision:** OR-Tools runs first to produce a deterministic optimal baseline; LLM then generates 4 scenario variants from that baseline.  
**Reason:** OR-Tools is reliable and fast (~2s); AI scenarios are meaningful variations on a valid plan rather than hallucinated routes.

### D-008: Chat UI — floating button, slide-over, full-page
**Decision:** Bottom-right 56px purple button → 420px slide-over → full-page modal (DataGuard pattern).  
**Reason:** Non-intrusive default; quick access; expandable for complex queries.

### D-009: Obsidian color theme (pure black + purple)
**Decision:** `--c-bg: #0a0a0a`, `--c-accent: #7c3aed`. Previous midnight blue theme remains as "Midnight Blue" variant.  
**Reason:** Matches DataGuard AI PDF design that user approved.

---

## Open Questions

### OQ-001: WhatsApp notification for plan completion
**Status:** Deferred to P5-E2+  
**Options:** Twilio WhatsApp API (paid), WATI (third-party), Interakt  
**Decision needed:** Which provider to use; will need a WhatsApp Business number.

### OQ-002: MongoDB Atlas provisioning
**Status:** Not started  
**Action:** Sign up at mongodb.com, create free M0 cluster, add `MONGODB_URL` to Render env vars.  
**Who:** Seenivasan (requires manual account creation)

### OQ-003: Email provider for plan notifications
**Status:** Open  
**Options:** Resend (developer-friendly, 3k free/month) vs SendGrid (more established)  
**Recommendation:** Resend — simpler API, no domain verification hassle on free tier.

### OQ-004: Per-tenant Postgres DB routing for enterprise
**Status:** Infrastructure built (P4-E1), not activated  
**Trigger:** When a tenant needs strict data isolation (enterprise contract)  
**Action:** Set `use_dedicated_db = true` in `tenant_configs`, provision Supabase project.

### OQ-005: Driver PWA — push notifications
**Status:** Planned (P5-E5)  
**Question:** Web Push (free, complex) vs FCM via service worker vs SMS fallback  
**Recommendation:** Web Push with service worker for PWA; SMS as fallback.

### OQ-006: Customer tracking portal domain
**Status:** Planned (P5-E7)  
**Question:** `/track/:code` on same domain vs separate `track.fleetopsx.com` subdomain  
**Recommendation:** Same domain for now; subdomain if white-label needed per tenant.

### OQ-007: Plan memory — how many past plans to use as context?
**Status:** Decided tentatively: last 5 same-weekday plans  
**Question:** Is 5 the right number? At ~2KB per plan, that's ~10KB of extra LLM context.  
**Note:** Revisit after P5-E2 is live and we see actual token costs.
