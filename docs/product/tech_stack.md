# Fleet Agentic AI – Tech Stack & Data Strategy

This document outlines a **practical, opinionated tech stack** and **data strategy** for all four phases of the Fleet Agentic AI roadmap, optimized for:

- Your background as a **Senior Software Engineer** (Spring Boot + Python + SQL)
- Fast prototyping for **Phase 1 MVP**
- Smooth evolution into **multi-agent, learning-based** system in later phases

---

## 1. Architecture Principles

1. **Start simple, evolve to modular**
   - Phase 1: single backend (Python) + single DB + simple job queue.
   - Later phases: split into services (planner, tracker, analytics, etc.) if needed.

2. **Python-first for Agentic & Optimization Logic**
   - Strong ecosystem for ML, OR-Tools, agent frameworks, and data tooling.
   - Spring Boot can still be used later for enterprise integration APIs if needed.

3. **Use proven building blocks, not exotic tech**
   - Postgres for relational + geospatial data (PostGIS).
   - Redis for caching, ephemeral state, and queues.
   - OR-Tools or similar for routing / VRP.
   - Popular agent frameworks instead of building everything from scratch.

4. **Cloud-agnostic but cloud-friendly**
   - Docker everywhere; can run on any cloud or local DevOps setup.
   - Use managed DB and message broker in production when possible.

---

## 2. Phase-Wise Tech Stack Overview

### 2.1 Stack Summary Table

| Layer / Concern       | Phase 1 (MVP)                               | Phase 2                                    | Phase 3                                                | Phase 4                                   |
| --------------------- | ------------------------------------------- | ------------------------------------------ | ------------------------------------------------------ | ----------------------------------------- |
| Backend API           | **FastAPI (Python)**                        | FastAPI                                    | FastAPI + separate micro-services (opt)                | FastAPI + Spring Boot for enterprise APIs |
| Agent / Orchestration | Simple in-process “Planner” service         | Agent framework (LangChain/LangGraph/Agno) | Multi-agent framework                                  | Same, scaled & hardened                   |
| DB (OLTP)             | **Postgres** (+ basic indexes)              | Postgres + **PostGIS**                     | Postgres + partitions                                  | Managed Postgres / distributed SQL        |
| Cache / Queue         | **Redis** (cache + Celery broker)           | Redis + Celery / RQ                        | Redis + Kafka (optional)                               | Redis + Kafka / cloud message bus         |
| Routing / Maps        | External Directions API (e.g., Google Maps) | OR-Tools + Maps API                        | OR-Tools + learned travel-time models                  | Hybrid (OR-Tools + optimization service)  |
| Frontend              | **React + TypeScript** (single SPA)         | React SPA (more dashboards)                | React + micro-frontends (optional)                     | Same, hardened for enterprise             |
| Data / Analytics      | Simple SQL queries, basic reporting         | ETL to analytics schema                    | Data warehouse + feature store (e.g., DuckDB/BigQuery) | Fully managed DW + BI tools               |
| Infra                 | Docker Compose, single node                 | K8s-ready Docker images                    | Kubernetes (small cluster)                             | Kubernetes managed service                |
| Monitoring & Logs     | Basic logs + health checks                  | Prometheus + Grafana, request tracing      | Full observability stack                               | Enterprise observability & alerting       |

---

## 3. Detailed Stack Choices

### 3.1 Backend & API Layer

**Recommended for Phase 1–4 core:**

- **Language:** Python 3.11+
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
  - Async, very fast to build, great OpenAPI docs, easy to integrate with async DB and external APIs.
- **Alternative (for enterprise integrations):** Spring Boot microservice later for:
  - Integrations with ERP/TMS
  - Authentication/SSO for enterprise customers
  - High-compliance / internal APIs

**Structure (Phase 1):**

- `app/`
  - `routers/` (orders, drivers, vehicles, assignments, planning)
  - `models/` (SQLAlchemy models)
  - `services/` (planning logic, routing calls)
  - `agents/` (simple planner agent wrapper)
  - `schemas/` (Pydantic DTOs)
  - `worker/` (Celery tasks)

Later phases can split `planning`, `tracking`, and `analytics` into separate services if needed.

---

### 3.2 Agentic Layer (LLM + Framework)

#### 3.2.1 LLM Provider

- **Primary:** OpenAI models (for reasoning, tool-calling, explanations)
- **Fallback / future:** Open-source models via Ollama or similar for cost/privacy.

Use LLMs for:

- Complex reasoning over constraints (“given these orders & constraints, propose a plan”)
- Tool orchestration (call DB, routing, optimization service)
- Explanations for human coordinators (“why this driver?”)

#### 3.2.2 Frameworks (Phase by Phase)

**Phase 1 – Light Agentic Layer (No heavy framework required yet)**

- Implement a simple “planner” class that:
  - Reads DB
  - Applies heuristics
  - Calls routing API
  - Returns suggestions
- Optionally call an LLM (via OpenAI) for explanations only.

**Phase 2 – Introduce Agent Framework**  
Use a production-oriented, Python-first framework such as:

- **LangChain + LangGraph**: good for tool-calling, workflows, and stateful agents.
- **Agno or similar**: Python framework focused on LLM agents with tool integration.
- **AutoGen / CrewAI**: if you want multi-agent collaboration patterns out of the box.

The goal is to model: **Planner Agent**, **Guardrail Agent**, **Monitor Agent** as composable flows.

**Phase 3–4 – Multi-Agent & Context Management**

- Promote to explicit multi-agent architecture using your chosen framework.
- Introduce:
  - Shared memory / context store (Redis + Postgres)
  - Strong tool abstractions (routing, optimization, policy engine, metrics)
- Carefully log all agent steps for debugging and replay.

> Important: Treat the agent layer as an **orchestrator** for deterministic services (DB, OR-Tools solver, routing APIs), not as a black-box decision maker.

---

### 3.3 Data Storage & Modeling

#### 3.3.1 OLTP Database: Postgres

Use **Postgres** as your primary operational DB.

- Tables:
  - `drivers`, `vehicles`, `orders`, `assignments`, `routes`, `stops`, `events`
  - `calendars`, `shifts`, `depot`, `zone` (later phases)
- Use **PostGIS** from Phase 2 onwards to store:
  - Geospatial points for depots, addresses, stops
  - Precomputed distance matrices (optional)

Benefits:

- Strong relational consistency for operational workflows
- Native geospatial functions (distance, contains, etc.)

#### 3.3.2 Caching & Ephemeral State: Redis

Use **Redis** for:

- Storing short-lived planning sessions
- Caching distance lookups or directions API results
- Broker for Celery / task queues

#### 3.3.3 Analytics / Warehouse

- Phase 1: Use Postgres itself for basic analytics.
- Phase 2–3: introduce an ETL process to:
  - Either a **separate Postgres schema** optimized for analytics
  - Or a file-based system like **DuckDB** on S3/Blob storage
- Phase 4: Move to a proper cloud data warehouse (BigQuery, Snowflake, Redshift) depending on your cloud provider.

---

### 3.4 Routing & Optimization

#### 3.4.1 Mapping & Directions API

From Phase 1:

- Use a mapping API for:
  - Geocoding addresses → lat/long
  - Getting driving distance & ETA (for single legs or simple routes)

Options:

- Google Maps Directions + Geocoding APIs
- OpenRouteService / Mapbox / OSRM-based services

#### 3.4.2 Route Optimization Engine

From Phase 2:

- Use **OR-Tools** (Google’s open-source optimization library) for:
  - Vehicle Routing Problem (VRP)
  - VRP with Time Windows (VRPTW)
  - Capacity constraints

Wrap OR-Tools in a service:

- `planner-service` with endpoints like:
  - `POST /solve-daily-plan`
  - `POST /reoptimize-route`

Agents call this deterministic service instead of “inventing” routes.

---

### 3.5 Frontend

**Phase 1–2: React SPA**

- **React + TypeScript**
- UI framework: MUI or Tailwind + Headless UI
- Key views:
  - Dashboard (today’s operations)
  - Map view (drivers, routes)
  - Order list & assignment view
  - Driver schedule view (calendar)

**Phase 3–4: Enhancements**

- More analytics dashboards and simulation UIs
- Possibly micro-frontends if the app grows large

---

### 3.6 Observability & Ops

**Phase 1:**

- Basic logging (structured logs via `loguru` or standard logging)
- Health checks & readiness probes for containers

**Phase 2+:**

- Metrics: Prometheus + Grafana
- Tracing: OpenTelemetry + Jaeger (or cloud provider equivalent)
- Log aggregation (ELK stack or cloud logs)

Focus on:

- Tracing agent decisions and tool calls
- Monitoring planning latency and success/failure rates

---

## 4. Data Strategy: Bootstrapping Without Your Own Data

You mentioned you **don’t have your own data yet**. That’s fine. You can:

1. **Design your own synthetic data generator** matching your schema.
2. **Download public logistics/fleet datasets** (Kaggle, open data) and map them into your schema.
3. Use these for demos, early experiments, and investor decks.

### 4.1 Synthetic Data Generation Plan

Create a small Python script or notebook that generates:

1. **Depots**
   - 1–5 depots per city, each with lat/long.

2. **Drivers & Vehicles**
   - 50–200 drivers with:
     - Home depot
     - Shift start/end times (e.g., 8–16, 10–18)
     - Skills / license classes (if needed later)
   - 50–200 vehicles with:
     - Capacity (kg/volume)
     - Type (bike, van, truck)
     - Availability flags

3. **Orders (Deliveries)**
   - Random but realistic addresses or coordinates within city bounds
   - Time windows (e.g., 9–12, 12–15, 15–18)
   - Weight/volume, customer ID, priority flag

4. **Calendars & Events**
   - Random driver leave days
   - Random vehicle maintenance slots

5. **Historical Runs** (for Phase 3)
   - Simulate previous days with:
     - Assignments and routes
     - Actual vs planned times
     - Random delays based on traffic patterns

You can also add noise and realistic patterns:

- Peak order volume in morning and evening.
- Certain zones more congested → higher delay probability.
- Certain drivers are “fast” or “slow” based on a driver multiplier.

This synthetic dataset can be used to:

- Power a **live demo** of Phase 1–2 UI.
- Train simple ML models in Phase 3 (e.g., travel-time adjustment factors).

---

### 4.2 Public Datasets You Can Use

You can combine **realistic public datasets** with your synthetic data. Examples to explore:

- Last-mile and logistics datasets (orders, delivery times, delays)
- Vehicle routing problem (VRP) benchmark sets
- Logistics & fleet revenue/cost datasets

You can map their fields into your schema:

- `order_id` → `orders.id`
- `origin_lat/long`, `destination_lat/long` → stops and depots
- `delivery_time`, `delay` → historical events and metrics
- `driver_id` or `truck_id` → drivers and vehicles

Use public data mainly for **analysis, optimization experiments, and demos** rather than exact production modeling.

---

## 5. How to Start (Concrete First Steps)

1. **Define your DB schema in Postgres** for Phase 1 entities (drivers, vehicles, orders, assignments, calendars).
2. **Bootstrap a FastAPI project** with core CRUD APIs and simple UI in React.
3. **Write a synthetic data generator** to populate 1–2 cities with realistic orders and drivers.
4. Implement the **Phase 1 Planner** as a Python class:
   - Basic rule-based suggestions
   - Calls routing API for ETAs
5. Add **OpenAI integration** to produce natural-language explanations for the coordinator.
6. Once Phase 1 is working end-to-end, iterate towards Phase 2:
   - Introduce OR-Tools service
   - Add real-time tracking mock (simulated GPS)
   - Begin experimenting with a proper agent framework.

This stack and strategy will give you a **clear, credible story** for investors and a strong technical foundation for the later agentic and ML-heavy phases.
