# GENSPEC – Infrastructure & Project Setup

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Infrastructure & Project Setup |
| **Status** | Implemented |
| **Version** | 1.0 |
| **Date** | 2025-12-25 |
| **Author** | Antigravity |

---

## 1. Goal

Initialize the base infrastructure for FleetOpsX, including API skeleton, UI containerization, and observability tools.

---

## 2. Implementation Guide

### Checkpoint 1: Dockerization

**Tasks:**
- Create `Dockerfile` in `FleetOpsX-API`.
- Create `Dockerfile` in `FleetOpsX-UI` (Multi-stage build).
- Create `docker-compose.yml` in `FleetOpsX-API` to orchestrate both repositories.

**Verification:**
- `docker compose build` succeeds.
- `docker compose up` starts all services.

---

### Checkpoint 2: Observability

**Tasks:**
- Integrate `sentry-sdk` in FastAPI.
- Integrate `@sentry/react` in React UI.
- Add `prometheus-fastapi-instrumentator` to API.
- Configure `prometheus.yml` and add `prometheus/grafana` to Docker Compose.

**Verification:**
- API metrics are available at `/metrics`.
- Sentry receives test errors from both UI and API.

---

### Checkpoint 3: CI/CD Foundations

**Tasks:**
- Create `.github/workflows/ci-api.yml` for backend (Linting, Tests).
- Create `.github/workflows/ci-ui.yml` for frontend (Linting, Build).

**Verification:**
- PRs trigger workflows correctly in GitHub (simulated).

---

### Checkpoint 4: Database Migrations (Alembic)

**Tasks:**
- Configure `alembic/env.py` to pull `DATABASE_URL` from application settings.
- Ensure `sys.path` is updated for local imports within Alembic.

**Verification:**
- `alembic current` shows up-to-date status.
