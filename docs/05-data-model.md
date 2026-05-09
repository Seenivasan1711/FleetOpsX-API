# FleetOpsX — Data Model

---

## Postgres Tables (Supabase)

### Phase 5 — New Tables

#### `ai_provider_configs` (P5-E1)
```sql
id            UUID PK
tenant_id     UUID NULLABLE (NULL = global/platform config)
provider_name VARCHAR(50)   -- claude | openai | gemini
model_id      VARCHAR(100)  -- claude-sonnet-4-6 | gpt-4o | gemini-pro
api_key_enc   TEXT          -- Fernet encrypted
task_type     VARCHAR(30)   -- planning | chat | analysis | all
is_active     BOOLEAN DEFAULT true
is_platform_default BOOLEAN DEFAULT false
created_at    TIMESTAMPTZ
updated_at    TIMESTAMPTZ
UNIQUE (tenant_id, provider_name, task_type)
```

#### `plan_history` (P5-E3 — Postgres fallback before MongoDB)
```sql
id             UUID PK
tenant_id      UUID FK→tenants
plan_date      DATE
plan_mode      VARCHAR(30)   -- fastest | economical | balanced | driver_availability
route_plan_id  UUID NULLABLE FK→route_plans
total_orders   INT
assigned_orders INT
confirmed_at   TIMESTAMPTZ
dispatcher_notes TEXT
outcome_notes  TEXT
outcome_status VARCHAR(20)   -- pending | success | partial | failed
ai_reasoning   JSONB         -- full AI chain from generation
scenarios_json JSONB         -- all 4 scenarios generated
memory_used    JSONB         -- memory entries that influenced this plan
created_at     TIMESTAMPTZ
```

#### `plan_notes` (P5-E3)
```sql
id           UUID PK
tenant_id    UUID
plan_id      UUID FK→plan_history
note_type    VARCHAR(20)  -- issue | improvement | general
content      TEXT
created_by   VARCHAR(255) -- email
created_at   TIMESTAMPTZ
```

#### `user_invitations` (P5-E8)
```sql
id          UUID PK
tenant_id   UUID FK→tenants
email       VARCHAR(255)
role        VARCHAR(50)
permissions JSONB
token       VARCHAR(64) UNIQUE
expires_at  TIMESTAMPTZ
accepted_at TIMESTAMPTZ NULLABLE
invited_by  UUID FK→users
created_at  TIMESTAMPTZ
```

---

## MongoDB Collections (P5-E3)

### `plan_sessions`
```json
{
  "_id": "ObjectId",
  "tenant_id": "uuid-string",
  "plan_date": "2026-05-10",
  "weekday": 1,
  "baseline_plan": { "routes": [...], "total_distance_km": 342.5 },
  "scenarios": [
    {
      "type": "fastest",
      "routes": [...],
      "kpis": { "total_time_min": 252, "est_fuel_cost": 1820, "coverage": 47 },
      "ai_confidence": 0.87,
      "reasoning": "Optimised for minimum total route time..."
    }
  ],
  "chosen_scenario": "balanced",
  "natural_language_constraints": "avoid NH-44, keep Ravi in North zone",
  "dispatcher_notes": "",
  "outcome": { "status": "success", "on_time_pct": 0.91 },
  "created_at": "ISO8601",
  "confirmed_at": "ISO8601"
}
```

### `plan_memories`
```json
{
  "_id": "ObjectId",
  "tenant_id": "uuid-string",
  "weekday": 1,
  "zone": "North",
  "driver_id": "uuid-string",
  "pattern": "Driver tends to run 30-40 min late on North zone Mondays due to school zone traffic",
  "source_plan_ids": ["plan-uuid-1", "plan-uuid-2"],
  "weight": 0.85,
  "occurrence_count": 3,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

## Existing Key Tables (reference)

```
tenants(id, name, slug, is_active, plan)
tenant_configs(tenant_id, key, value)  -- KV store for all config
users(id, tenant_id, email, hashed_password, full_name, role, is_active)
  role: superadmin | admin | dispatcher | driver | readonly | packaging_team

orders(id, tenant_id, plan_date, status, delivery_address, lat, lng, priority, ...)
drivers(id, tenant_id, full_name, email, home_depot_id, is_active, ...)
vehicles(id, tenant_id, registration_number, capacity_kg, is_active, ...)
depots(id, tenant_id, name, latitude, longitude, is_active)
route_plans(id, tenant_id, plan_date, status, planner, assigned_orders, ...)
routes(id, route_plan_id, driver_id, vehicle_id, ...)
route_stops(id, route_id, order_id, sequence, status, ...)

tracking(id, tenant_id, driver_id, latitude, longitude, recorded_at)
chat_messages(id, tenant_id, session_id, role, content, created_at)
audit_log_entries(id, tenant_id, actor_email, action, resource_type, ...)
rbac_roles(id, tenant_id, name, permissions[], is_system)
agent_suggestions(id, tenant_id, suggestion_type, status, ...)
scenario_runs(id, tenant_id, scenario_type, status, ...)
scenario_results(id, scenario_run_id, plan_date, kpis, kpi_delta, ...)
```

---

## AI Provider Config — Env Variables

```bash
# Required — at least one must be set
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Default model per task (overridable via DB)
DEFAULT_PLANNING_MODEL=claude-sonnet-4-6
DEFAULT_CHAT_MODEL=claude-haiku-4-5-20251001
DEFAULT_ANALYSIS_MODEL=claude-sonnet-4-6

# MongoDB (P5-E3)
MONGODB_URL=mongodb+srv://...
MONGODB_DB=fleetopsx
```
