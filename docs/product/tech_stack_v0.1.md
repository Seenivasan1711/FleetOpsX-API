# Fleet Agentic AI – Tech Stack & Data Strategy

## Technology Choices Overview

| Layer             | Primary Tech                                       |
| ----------------- | -------------------------------------------------- |
| Backend & APIs    | FastAPI (Python 3.11+)                             |
| Agentic Framework | LangChain + LangGraph (ph2+), simple planner (ph1) |
| Optimization      | OR‑Tools (Routing/VRPTW)                           |
| DB                | PostgreSQL + PostGIS                               |
| Cache + Queue     | Redis                                              |
| Frontend          | React + TypeScript                                 |
| Maps & Routing    | Google Maps API / OpenRouteService                 |
| Hosting           | Containerized – deploy on any cloud                |

---

## Backend Architecture

- Planner uses:
  - DB access + routing service
  - Rules (Phase 1)
  - Constraint optimization (Phase 2+)
- Agents orchestrate deterministic tools
- State store maintained in Postgres & Redis

---

## Agentic System Evolution

| Phase | Agent Capabilities                                    |
| ----- | ----------------------------------------------------- |
| 1     | Single planner agent, rule‑based suggestions          |
| 2     | Tool‑calling agent w/ route optimization              |
| 3     | Multi‑agent: planner + monitor + forecast + explainer |
| 4     | Autonomy across depots + partners + time horizons     |

---

## Data Model (Initial Entities)

- Drivers: id, shift window, depot, location
- Vehicles: id, capacity, type
- Orders: pickup/delivery points, time windows, priority
- Assignments: driver + route
- Events: delays, breakdowns

---

## Data Strategy

### Phase 1

- Admin CRUD + CSV import
- Synthetic dataset for Bangalore

### Phase 2

- Historical operations data recorded
- Real-time GPS feed

### Phase 3

- ML models trained for:
  - Travel time adjustment
  - Delay/volume prediction

### Phase 4

- Warehouse + BI dashboards

---

## Synthetic Dataset (Bangalore)

**Will contain:**

- 1–3 depots
- 50–200 drivers w/ shift times
- 200–500 randomized orders/day
- Coordinates inside Bangalore bounding box
- Random leave & maintenance schedules
- Route results for training

---

## Deployment Roadmap

| Phase | Infra                            | Scale            |
| ----- | -------------------------------- | ---------------- |
| 1     | Docker Compose, single node      | 100 drivers      |
| 2     | Cloud DB, scalable worker queues | 500+ drivers     |
| 3     | Kubernetes, multi‑service        | 2000+ drivers    |
| 4     | Multi‑tenant SaaS                | Enterprise scale |

---

## Summary

- Use Python/OR‑Tools/LLM agents for decision automation
- Postgres + PostGIS enables spatial queries
- Data improves model → better planning → lower cost + SLA gain
