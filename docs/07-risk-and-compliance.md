# FleetOpsX — Risk & Compliance

---

## 1. Security Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JWT token leaked | Low | High | Short expiry (24h), HTTPS only, no token in URL |
| Tenant data cross-contamination | Low | Critical | `tenant_id` filter on every query, enforced in deps |
| AI API key exposure | Medium | High | Fernet encrypted at rest; never returned in API responses |
| Superadmin impersonation abuse | Low | High | All mutations logged to audit_log with actor_role |
| Prompt injection via user chat | Medium | Medium | System prompt prefixed; LLM output validated before rendering |
| SQL injection | Low | Critical | SQLAlchemy ORM (parameterised), no raw SQL |
| XSS in chat responses | Medium | Medium | React renders text as text (no dangerouslySetInnerHTML); markdown sanitised |

---

## 2. Data Privacy

### What we store
- Driver: name, email, home depot, GPS positions (TTL-purged from Redis after 5 min)
- Customer: delivery address, lat/lng, contact details on orders
- Dispatcher: email, activity in audit log
- Chat messages: stored per session; contain fleet context injected by system

### Retention policy
- Orders: retained indefinitely (operational record)
- GPS tracking: Redis cache 5 min; Postgres `tracking` table — configurable sweep (default 90 days)
- Chat messages: 30 days default; configurable per tenant via `tenant_configs`
- Audit log: append-only, never deleted
- Plan history: indefinite (used as AI memory)

### GDPR compliance
- `GET /api/v1/governance/export` — exports all data for a tenant
- Soft-delete on users (`is_active = false`) — email retained for audit log integrity
- No PII sent to AI providers except what's in the fleet context (driver names, addresses)

---

## 3. Operational Risks

| Risk | Mitigation |
|------|-----------|
| AI provider outage (Anthropic/OpenAI) | Fallback chain in `llm_factory.py`; manual override via admin |
| Render free tier cold start (>30s) | Upgrade to Starter on production launch |
| Supabase free tier row limits | Monitor; current usage well within 500MB free |
| MongoDB Atlas write failure | Plan history falls back to Postgres JSONB until Atlas recovered |
| Celery worker crash during plan generation | Task status tracked; UI shows error; user can retry |
| Email delivery failure (Resend) | Non-blocking; plan still confirmed; log error |

---

## 4. Multi-tenant Isolation Checklist

- [x] Every Postgres table has `tenant_id` column
- [x] `get_current_tenant_id()` dep enforced on all routes except `/auth` and `/admin`
- [x] `get_effective_tenant_id()` (P5-E0) validates acting tenant against tenant table
- [x] Superadmin mutations logged separately in audit_log
- [ ] Per-tenant Postgres DB routing (P4-E1 — activate for enterprise) — infrastructure ready, not enabled for demo

---

## 5. AI Safety Rules (System Prompt)

The following rules are injected as a system prompt prefix for every chat request:

```
You are FleetOpsX AI — a fleet operations assistant.
RULES:
1. Only answer questions about fleet operations: orders, drivers, vehicles, routes, planning, SLA.
2. Never answer general-knowledge, coding, or off-topic questions.
3. Always use provided fleet context data. Never invent numbers.
4. Format responses as structured JSON (response card format).
5. Every response must include follow-up suggestion chips.
6. Every response must end with a context footer citing data sources used.
7. If you cannot answer from the provided data, say so clearly.
```

---

## 6. Audit Log

All mutations write to `audit_log_entries`:
```
actor_email, actor_role, action, resource_type, resource_id,
tenant_id, acting_tenant_id (for superadmin), changes_json, created_at
```

Superadmin mutations include `actor_role = superadmin` and `acting_tenant_id` set.

---

## 7. API Key Management

- AI provider API keys are encrypted using Fernet symmetric encryption
- Encryption key derived from `JWT_SECRET_KEY` (PBKDF2 / first 32 bytes)
- Keys are decrypted in memory only at request time
- Keys are never returned in API responses (only `key_set: true/false`)
- Tenant-owned keys are stored in `ai_provider_configs` with `tenant_id` set
- Platform keys (superadmin-managed) have `tenant_id = NULL`
