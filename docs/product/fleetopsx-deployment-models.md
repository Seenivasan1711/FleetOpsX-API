# FleetOpsX Deployment & Data-Trust Models

_Cloud SaaS • Dedicated SaaS • On‑Prem • Offline_

This document defines **ALL supported deployment models** for FleetOpsX.
It is intended to be a **permanent reference** for engineering, product, sales, and architecture decisions.

The goal is simple:

> **Deliver FleetOpsX intelligence without forcing customers to share sensitive data.**

This document must be kept in mind **for every feature, API, and architectural decision**.

---

## 1. Core Design Principles (Non‑Negotiable)

These principles apply to **all deployment types**.

### 1.1 Data Ownership

- Customer **always owns their data**
- FleetOpsX never assumes ownership of:
  - Orders
  - Routes
  - Customer names
  - Volumes
  - Locations

### 1.2 Bring AI to the Data

- AI, optimization, and agents must be **deployable where the data lives**
- Never hard‑couple planning logic to a single cloud

### 1.3 Planner as a Black‑Box Engine

- Planning logic must be accessed via **stable APIs**
- Internal implementation can evolve without breaking clients

```text
Input (PlanningContext) → Planner Engine → Output (PlanResult)
```

### 1.4 Cloud‑Agnostic by Default

- Everything runs via:
  - Docker
  - Docker Compose
  - Helm / Kubernetes
- No hard dependency on AWS/GCP/Azure services

---

## 2. Supported Deployment Models (Official)

FleetOpsX supports **FOUR deployment modes**.

Each mode serves a different customer profile.

---

## 3. Deployment Mode A — Multi‑Tenant Cloud SaaS

### 3.1 Description

- Default SaaS offering
- Multiple customers share infrastructure
- Strict logical tenant isolation (`tenant_id`)

### 3.2 Architecture

```text
FleetOpsX Cloud
├── React Ops UI
├── FastAPI Backend (Multi‑tenant)
├── Planner / Agent Layer
├── Postgres (shared)
├── Redis
└── External APIs (Maps, Notifications)
```

### 3.3 Data Handling

- Logical isolation using `tenant_id`
- Encrypted at rest and in transit
- No cross‑tenant data access

### 3.4 Pros / Cons

Pros:

- Fast onboarding
- Lowest cost
- Continuous upgrades

Cons:

- Not acceptable for regulated enterprises

### 3.5 Ideal Customers

- Startups
- SMB logistics
- Pilot customers

---

## 4. Deployment Mode B — Dedicated SaaS (Single‑Tenant Cloud)

### 4.1 Description

- One tenant → one isolated environment
- Runs in:
  - FleetOpsX cloud account **or**
  - Customer cloud account

### 4.2 Architecture

```text
Customer‑Dedicated Environment
├── Ops UI
├── Backend API
├── Planner / Agents
├── Postgres (dedicated)
└── Redis
```

### 4.3 Data Handling

- Full physical isolation
- No shared DB or cache
- Optional private networking

### 4.4 Pros / Cons

Pros:

- Strong isolation
- Easier compliance
- Still managed by FleetOpsX

Cons:

- Higher cost
- Slower scaling than shared SaaS

### 4.5 Ideal Customers

- Mid‑size enterprises
- Companies with security audits
- Regional logistics providers

---

## 5. Deployment Mode C — On‑Prem / Customer VPC

### 5.1 Description

FleetOpsX runs **inside the customer’s infrastructure**.

- Customer controls:
  - Network
  - Data
  - Access
- FleetOpsX provides:
  - Software
  - Updates
  - Support

### 5.2 Architecture

```text
Customer Network / VPC
├── FleetOpsX API (FastAPI)
├── Planner + OR‑Tools
├── Agent Framework (LangGraph)
├── Postgres (customer‑owned)
├── Redis
└── Ops UI (internal)
```

### 5.3 Data Handling

- NO raw data leaves customer environment
- Optional outbound telemetry (opt‑in only)

### 5.4 Connectivity Options

- Fully isolated
- VPN‑connected
- PrivateLink / VPC Peering

### 5.5 Pros / Cons

Pros:

- Maximum data control
- Enterprise‑grade trust
- Regulatory compliance

Cons:

- Operational complexity
- Slower feature rollout

### 5.6 Ideal Customers

- Large enterprises
- Pharma / Food / Govt logistics
- Security‑sensitive organizations

---

## 6. Deployment Mode D — Fully Local / Offline (Air‑Gapped)

### 6.1 Description

FleetOpsX runs **without internet access**.

- No cloud calls
- No telemetry
- No external APIs

### 6.2 Architecture

```text
Offline Customer Environment
├── Ops UI (Local)
├── Backend API
├── Planner Engine
├── Postgres
├── Redis
└── Local Maps / Static Distance Tables
```

### 6.3 Special Constraints

- Maps:
  - Preloaded distance matrices
  - OpenStreetMap offline extracts
- AI:
  - Local LLMs (optional)
  - Rule‑based + OR‑Tools only

### 6.4 Pros / Cons

Pros:

- Zero data leakage
- Works in restricted networks

Cons:

- Limited intelligence
- Manual updates required

### 6.5 Ideal Customers

- Defense
- Government
- Remote industrial fleets

---

## 7. Data Sharing & Telemetry Modes

Telemetry is **always configurable per customer**.

### Mode 0 — No Data Sharing

- No metrics
- No logs
- No telemetry

### Mode 1 — Metadata Only (Recommended)

Examples:

- Fleet size
- Orders/day
- SLA hit rate
- Planner version

NO:

- Locations
- Names
- Routes

### Mode 2 — Federated Learning (Future)

- Models train locally
- Only model updates shared
- No raw data exposure

---

## 8. Planner & Agent Architecture Rule

The planner **must never depend on cloud‑only services**.

### Required Interface

```python
class PlannerInterface:
    def plan_day(context) -> PlanResult
    def replan(context) -> PlanResult
```

Deployment‑specific adapters handle:

- DB access
- Maps
- Telemetry
- LLM availability

---

## 9. Feature Compatibility Matrix

| Feature               | Cloud | Dedicated | On‑Prem      | Offline       |
| --------------------- | ----- | --------- | ------------ | ------------- |
| Route Optimization    | ✅    | ✅        | ✅           | ✅            |
| Agentic Planning      | ✅    | ✅        | ✅           | ⚠️ Limited    |
| Real‑time Tracking    | ✅    | ✅        | ✅           | ❌            |
| External Integrations | ✅    | ✅        | ✅           | ❌            |
| AI Explanations       | ✅    | ✅        | ✅           | ⚠️ Local only |
| Continuous Updates    | ✅    | ✅        | ⚠️ Scheduled | ❌            |

---

## 10. Security & Compliance Notes

- Encryption at rest & transit
- Role‑based access control
- Audit logs (configurable)
- Customer‑controlled backups
- No hardcoded secrets
- Bring‑your‑own‑key (future)

---

## 11. Commercial Alignment (Guidance)

| Deployment        | Pricing Model        |
| ----------------- | -------------------- |
| Multi‑tenant SaaS | Subscription         |
| Dedicated SaaS    | Subscription + Infra |
| On‑Prem           | License + Support    |
| Offline           | Perpetual License    |

---

## 12. Engineering Rules (Must Follow)

1. Assume **offline mode exists**
2. Never hardcode cloud dependencies
3. Always keep planner deployable
4. Telemetry must be optional
5. Data locality is a first‑class concern

---

## 13. Summary

FleetOpsX is not just a SaaS platform.

It is a **deployable fleet intelligence engine** that can run:

- In the cloud
- In private clouds
- On‑prem
- Completely offline

This flexibility is a **strategic moat** and must be preserved.

---

_End of document_
