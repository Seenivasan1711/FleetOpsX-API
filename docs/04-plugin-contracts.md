# FleetOpsX — Plugin & API Contracts

---

## 1. REST API Conventions

- Base URL: `/api/v1/`
- Auth: `Authorization: Bearer <jwt>` on all protected routes
- Superadmin impersonation: `X-Acting-Tenant-Id: <tenant_uuid>` header
- All responses: `{ data, error, message }` envelope (errors) or flat object (success)
- Pagination: `?page=1&per_page=50` → `{ items[], total, page, per_page }`
- Dates: ISO 8601 strings throughout (`2026-05-10`)

---

## 2. Auth Contracts

### POST /api/v1/auth/login
```json
Request:  { "email": "str", "password": "str" }

Response (regular user):
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": { "id", "email", "full_name", "role", "tenant_id" }
}

Response (superadmin):
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": { "id", "email", "full_name", "role": "superadmin", "tenant_id": null },
  "tenants": [
    { "id": "uuid", "name": "Demo Corp", "slug": "demo-corp",
      "order_count_today": 47, "driver_count": 19, "is_active": true }
  ]
}
```

---

## 3. Superadmin Admin Contracts

### GET /api/v1/admin/tenants
```json
Headers: Authorization: Bearer <superadmin_jwt>
Response: [{ "id", "name", "slug", "is_active", "order_count_today", "driver_count" }]
```

### GET/POST/PUT/DELETE /api/v1/admin/ai-providers
```json
POST body:
{
  "provider_name": "claude | openai | gemini",
  "model_id": "claude-sonnet-4-6",
  "api_key": "sk-ant-...",        // stored encrypted
  "task_type": "planning | chat | analysis | all",
  "is_active": true,
  "is_platform_default": false
}

Response: AiProviderOut (api_key omitted, key_set: bool)
```

---

## 4. Planning Contracts

### POST /api/v1/plan/ai-scenarios
```json
Request:  { "plan_date": "2026-05-10", "natural_language_constraints": "avoid NH-44" }
Response: { "task_id": "celery-uuid", "status": "queued" }

Poll: GET /api/v1/plan/task-status/{task_id}
  → { "status": "pending|running|done|failed", "result": { ... } }

Result when done:
{
  "baseline": { "routes": [...], "total_distance_km": 342 },
  "scenarios": [
    {
      "type": "fastest",
      "routes": [...],
      "kpis": { "total_time_min": 252, "est_fuel_cost": 1820, "coverage": 47 },
      "ai_confidence": 0.87,
      "reasoning": "Optimised for minimum total route time..."
    }
  ],
  "constraints_applied": ["avoid NH-44", "zone lock: Ravi → North"]
}
```

### POST /api/v1/plan/confirm-scenario
```json
Request:  { "plan_date": "2026-05-10", "scenario_type": "balanced", "session_id": "uuid" }
Response: { "route_plan_id": "uuid", "status": "confirmed" }
```

---

## 5. Chat Contracts

### POST /api/v1/chat/message
```json
Request:
{
  "session_id": "uuid",
  "message": "Which drivers are at risk today?",
  "slash_command": "/atRisk"    // optional
}

Response:
{
  "session_id": "uuid",
  "response_card": {
    "type": "at_risk_list | summary | data_table | plan_scenarios | comparison_table | draft_document",
    "title": "At-Risk Deliveries",
    "content": { ... },           // typed by card type
    "follow_up_chips": ["Show Ravi's full route", "Which stops can be reassigned?"],
    "context_footer": "Based on 47 orders · 3 drivers active · 10:23 AM"
  }
}
```

---

## 6. Tenant Settings Contracts

### GET /api/v1/settings/ai-config
```json
Response:
{
  "platform_defaults": { "planning": "claude-sonnet-4-6", "chat": "claude-haiku-4-5-20251001", "analysis": "claude-sonnet-4-6" },
  "tenant_overrides": { "planning": null, "chat": "gpt-4o", "analysis": null },
  "own_keys_configured": ["openai"]
}
```

### PATCH /api/v1/settings/ai-config
```json
Request: { "task_type": "chat", "model_id": "gpt-4o", "api_key": "sk-..." }
```

---

## 7. WebSocket Contract (P5-E6)

```
ws://<host>/ws/dispatch/{tenant_id}?token=<jwt>

Server → Client events:
  { "event": "gps_update",    "driver_id": "uuid", "lat": 12.97, "lng": 77.59, "speed_kmh": 28 }
  { "event": "order_status",  "order_id": "uuid", "status": "delivered" }
  { "event": "plan_ready",    "task_id": "uuid", "plan_date": "2026-05-10" }
  { "event": "driver_alert",  "driver_id": "uuid", "message": "Ravi is 45 min behind" }

Client → Server:
  { "type": "ping" }
  { "type": "subscribe_driver", "driver_id": "uuid" }
```

---

## 8. External Integrations

| Integration | Purpose | Contract |
|-------------|---------|----------|
| Anthropic API | Planning + Chat (primary) | `POST /v1/messages` — see Anthropic SDK |
| OpenAI API | Optional AI provider | `POST /v1/chat/completions` |
| Google AI (Gemini) | Optional AI provider | `POST /v1beta/models/{model}:generateContent` |
| Resend / SendGrid | Email notifications | `POST /emails` — plan ready, invite |
| MongoDB Atlas | Plan sessions + memories | Motor async driver, MONGODB_URL env |
| Supabase | Postgres primary DB | SQLAlchemy + psycopg2 |
| Render | Hosting (API + frontend) | Deploy on git push |
