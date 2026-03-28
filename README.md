# FleetOpsX API

*Autonomy for every fleet*

FleetOpsX is a **multi-tenant Agentic AI platform** designed to centralize fleet operations, including orders, drivers, vehicles, and routes. It uses AI and optimization to plan and re-plan routes, evolving from rule-based heuristics to autonomous, learning-based multi-agent systems.

## 🚀 Getting Started

This repository contains the backend API built with **FastAPI**, **PostgreSQL/PostGIS**, and **Redis**.

### Prerequisites

- **Docker & Docker Compose**
- **Python 3.11+** (for local development)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd FleetOpsX-API
   ```

2. **Configure Environment:**
   Create a `.env` file in the root directory:
   ```env
   POSTGRES_USER=fleetuser
   POSTGRES_PASSWORD=fleetpass
   POSTGRES_DB=fleetopsx
   DATABASE_URL=postgresql+psycopg2://fleetuser:fleetpass@localhost:5432/fleetopsx
   REDIS_URL=redis://localhost:6379/0
   SENTRY_DSN=your-sentry-dsn
   ```

### Running the Project

You can run the entire stack (API, UI, and Database) using Docker Compose:

```bash
docker compose up --build
```

- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Local Development (without Docker)

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations:**
   ```bash
   alembic upgrade head
   ```

3. **Start API:**
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 📊 Observability

- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3000](http://localhost:3000) (Login: admin/admin)
- **Sentry**: Configured via `SENTRY_DSN` in `.env`.

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with PostGIS
- **Cache/Queue**: Redis
- **Migrations**: Alembic
- **Agentic Logic**: LangGraph (Phase 2+)
