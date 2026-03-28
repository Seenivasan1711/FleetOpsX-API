# HLD – Initial Infrastructure Overview

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Initial Infrastructure & Monorepo Setup |
| **Status** | Approved |
| **Version** | 1.0 |
| **Date** | 2025-12-25 |
| **Author** | Antigravity |
| **Reference** | Epic P1-E1 |

---

## 1. Executive Summary

This document outlines the high-level design for the FleetOpsX infrastructure setup. The goal is to provide a containerized, cost-effective development and staging environment that supports multi-tenancy from day one.

---

## 2. System Architecture

```mermaid
flowchart LR
    subgraph Clients
        OpsUI[Ops Web App\n(React/Vite)]
        DriverApp[Driver View\n(Mobile Web)]
    end

    subgraph Backend["FleetOpsX Backend (FastAPI)"]
        APIGW[API Gateway & Routers]
        Auth[Auth & Tenant Resolver]
        Observability[Sentry/Loguru/Prometheus]
    end

    subgraph Data["Data & Infra (Docker)"]
        DB[(Postgres + PostGIS)]
        Cache[(Redis)]
        Prometheus[(Prometheus)]
        Grafana[(Grafana)]
    end

    subgraph External["External Services"]
        Sentry[Sentry.io]
    end

    Clients --> APIGW
    APIGW --> Auth
    APIGW --> Observability
    
    Observability --> DB
    Observability --> Cache
    Observability --> Prometheus
    Observability --> Sentry
    Prometheus --> Grafana
```

### 2.1 Components

- **FastAPI API**: The core backend application, serving RESTful endpoints.
- **React UI**: The frontend dashboard built with Vite and Tailwind CSS.
- **PostgreSQL + PostGIS**: Primary relational database with geospatial support.
- **Redis**: Used for session caching and message queuing.
- **Prometheus & Grafana**: Self-hosted metrics and visualization stack.
- **Sentry**: Cloud-based error tracking for both frontend and backend.

---

## 3. Data Flow

1. **User Request**: Client (UI) sends an HTTP request to the API.
2. **Middleware**: API executes CORS, Tenant Resolution, and Observability middlewares.
3. **Processing**: API interacts with Postgres/Redis as needed.
4. **Metrics/Logs**: Decision points and errors are logged to Sentry/Prometheus.
5. **Response**: API returns JSON response to the client.

---

## 4. Security Considerations

- **CORS**: Configured to restrict access (initially open for development).
- **Environment Management**: All secrets and configurations are managed via `.env` files.
- **Tenant Isolation**: Handled via `tenant_id` at the database level (to be implemented in P1-E2).

---

## 5. Deployment Strategy

- **Local**: Docker Compose handles all services.
- **Staging/Prod**: Single EC2 instance running Docker Compose for maximum cost efficiency.
