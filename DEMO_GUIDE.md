# FleetOpsX — Demo Guide

> **Audience:** Investor demos, pilot customer walkthroughs, internal stakeholder presentations.
> **Duration:** 10–15 minutes for the full flow. 5 minutes for the express version.
> **Goal:** Show end-to-end: orders exist → one click assigns them to drivers → driver receives route → driver marks deliveries done.

---

## Pre-Demo Setup (Do this before the audience arrives)

### 1. Start all services

```bash
cd FleetOpsX-API
docker compose up -d
```

Verify everything is running:

```bash
docker compose ps
```

All six services should show `Up`:

| Service | Port | Expected Status |
|---------|------|----------------|
| fleetopsx-ui | 5173 | Up |
| fleetopsx-api | 8000 | Up |
| fleetopsx-db | 5600 | Up (healthy) |
| fleetopsx-redis | 6379 | Up (healthy) |
| fleetopsx-prometheus | 9090 | Up |
| fleetopsx-grafana | 3000 | Up |

### 2. Run migrations (first time only)

```bash
docker compose exec api alembic upgrade head
```

### 3. Seed demo data

```bash
# Clean any existing demo data first
docker compose exec api python scripts/seed_data.py --clean

# Seed fresh data for today
docker compose exec api python scripts/seed_data.py --start-date $(date +%Y-%m-%d)
```

**Save the Tenant ID printed at the end:**

```
🎉 Done! Tenant ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> **Tip:** Set `--start-date` to tomorrow if you want fresh undelivered orders at any time during the demo without re-seeding.

### 4. Pre-open browser tabs

Open these tabs before the demo starts:

| Tab | URL | Purpose |
|-----|-----|---------|
| Tab 1 | http://localhost:5173/login | Dispatcher login |
| Tab 2 | http://localhost:5173/login | Driver login (open in separate browser/incognito) |
| Tab 3 | http://localhost:8000/docs | API docs (optional, for technical audiences) |

---

## Demo Script

### Act 1 — The Problem (30 seconds, no screen)

> *"Today, most fleet operations teams start their morning with a spreadsheet, a WhatsApp group, and a prayer. Dispatchers manually assign 50–200 orders to drivers, which takes 1–2 hours and still results in suboptimal routes. FleetOpsX eliminates that entirely."*

---

### Act 2 — Login as Dispatcher (1 minute)

**Navigate to:** http://localhost:5173/login

Enter:
- **Email:** `dispatcher@demo.com`
- **Password:** `demo1234`

Click **Sign In**.

> **Admin account:** `admin@demo.com` / `demo1234`
> **Driver account:** `driver@demo.com` / `demo1234`

**Talking point:**
> *"The platform is fully multi-tenant. Each fleet company — we call them tenants — has complete data isolation. Enterprise clients can have multiple depots, hundreds of drivers, thousands of orders, all under the same account."*

---

### Act 3 — Dashboard Overview (1–2 minutes)

You land on the **Dashboard** at `/`.

Point out the four stat cards:

| Card | What to say |
|------|-------------|
| **Total Orders** | "We have X orders scheduled for today across Bangalore." |
| **Unassigned** | "None of them have been assigned to a driver yet — this is the dispatcher's morning problem." |
| **Assigned** | "Zero assigned. We're about to change that in one click." |
| **Active Drivers** | "We have 20 drivers on shift, vehicles fuelled, ready to go." |

**Talking point:**
> *"This is what a dispatcher sees at 8 AM. Orders are pouring in from the order management system. Drivers are clocking in. The clock is ticking."*

---

### Act 4 — Generate the Plan (2–3 minutes) ★ KEY MOMENT

Click **"Generate Plan"** button (top right of Dashboard) or navigate to **`/planning`**.

**On the Planning screen:**

1. Confirm today's date is selected in the date picker.
2. The table shows all unassigned orders — addresses, priorities (CRITICAL in red, HIGH in orange), time windows.
3. Click the **"Generate Plan (X unassigned)"** button.

Watch the toast notification:
```
✓ Plan generated! 33 orders assigned across 10 routes.
```

The **Plan Result** table appears below, showing:
- Each assignment: driver name, order, stop sequence number
- All 33 orders distributed across drivers

**Talking point:**
> *"That just replaced 90 minutes of manual work. Our Phase 1 planner uses a greedy nearest-driver algorithm with Haversine distance. In Phase 2, we're integrating OR-Tools for constraint-based VRPTW optimisation and a LangGraph agent that re-plans dynamically when a driver calls in sick or a delivery fails."*

> *"Notice the priority ordering — CRITICAL and HIGH priority stops are weighted to be assigned first. Time windows are respected."*

---

### Act 5 — CRUD Screens (2 minutes, optional for non-technical)

Navigate through the sidebar to show operational management:

**Drivers (`/drivers`):**
- Show the list of 20 drivers with home depots
- Click the pencil icon on any driver → slide-over form appears
- *"Dispatchers can add a new driver in seconds — no backend access needed."*

**Vehicles (`/vehicles`):**
- Show registration numbers, types (VAN, BIKE), capacity
- Point out the "Cold Chain" toggle
- *"Refrigerated vehicle flag flows through to planning — cold-chain orders only get assigned to refrigerated vehicles in Phase 2."*

**Orders (`/orders`):**
- Change the date filter to see a different day's orders
- Use the status filter to show only ASSIGNED orders
- Click "Add Order" to show the create form
- *"Dispatchers or integrated systems can inject ad-hoc orders at any time. The plan can be re-generated."*

---

### Act 6 — Driver View (2–3 minutes) ★ CLOSES THE LOOP

Open a **new incognito / private browser window** (or a second device).

**Navigate to:** http://localhost:5173/login

Log in as the driver:
- **Email:** `driver@demo.com`
- **Password:** `demo1234`
- **Tenant ID:** *(same as before)*

The app automatically redirects to `/driver` — the mobile view.

**What to show:**

1. The driver sees their **ordered list of stops** for today
2. Progress bar at the top shows 0 / N done
3. Click **Stop 1** to expand it — the address is shown with the time window

**Mark a delivery:**
1. Tap **"Arrived"** → stop card turns blue
2. Tap **"Delivered ✓"** → stop card turns green, "Delivered" confirmation appears
3. Progress bar advances

**Switch back to the dispatcher tab** and refresh the Dashboard:
- The "Assigned" count has decreased, "Delivered" count is up.

**Talking point:**
> *"The driver never needs to call the dispatcher. No WhatsApp, no phone calls. They open this on their phone, tap through their stops, and the system updates in real time. The dispatcher's dashboard reflects the live state of every delivery."*

> *"This is a mobile-first progressive web app — no app store, no installation. The driver just opens a browser link."*

---

### Act 7 — API & Observability (1 minute, for technical audiences)

**Navigate to:** http://localhost:8000/docs

- Show the Swagger UI with all endpoints grouped by tag
- Expand `POST /api/v1/plan/day` — show it takes just a `plan_date` query parameter
- *"Every action the UI takes is a clean REST API call. Any ERP or WMS can integrate directly."*

**Navigate to:** http://localhost:3000 (Grafana, admin/admin)
- *"We have full observability out of the box — request latency, error rates, database query times, all in Grafana. Production-ready from day one."*

---

## Express Demo (5 minutes)

If time is short, cover only these four screens in order:

1. **Login** → in as dispatcher
2. **Dashboard** → show unassigned order count
3. **Planning** → click Generate Plan → show result table
4. **Driver View** → login as driver, tap Delivered on one stop → switch back to dashboard to show count change

---

## Common Questions & Answers

**Q: How does the AI assignment work?**
> Phase 1 uses a rule-based greedy algorithm — it finds the nearest available driver to each order, respects time windows and vehicle capacity. Phase 2 replaces this with OR-Tools VRPTW (vehicle routing with time windows) and a LangGraph agent that reasons about re-planning when conditions change.

**Q: Can it handle real-time traffic?**
> Phase 1 uses straight-line Haversine distance. Phase 2 integrates with Google Maps Platform for real road distances and live traffic. The planner interface is already abstracted — swapping in the new engine is a configuration change, not a rewrite.

**Q: Is this multi-tenant?**
> Yes. Every database record is scoped to a `tenant_id` extracted from the JWT token. Tenant A cannot see Tenant B's data. All APIs enforce this at the dependency injection layer.

**Q: What happens when a driver fails a delivery?**
> The driver taps "Failed" on their stop card. The order status updates to `FAILED`. The dispatcher sees it immediately on the dashboard and can manually reassign or trigger a re-plan.

**Q: Can the plan be run multiple times a day?**
> Yes. You can generate a plan, then add new urgent orders, and generate again — the planner only picks up unassigned orders, so already-assigned stops are not disrupted.

---

## Troubleshooting

**Services not starting:**
```bash
docker compose down && docker compose up -d
```

**UI shows blank page or login fails:**
```bash
docker compose logs ui --tail=20
docker compose logs api --tail=20
```

**"No driver record linked to this account" on driver view:**
> The seed script links `driver@demo.com` to the first driver record. If you re-seeded without `--clean` first, there may be a conflict. Run:
```bash
docker compose exec api python scripts/seed_data.py --clean
docker compose exec api python scripts/seed_data.py --start-date $(date +%Y-%m-%d)
```

**"No unassigned orders" on Planning screen:**
> The date picker may be set to a date with no seeded data. Change it to the date you used with `--start-date`.

**Docker build fails after code changes:**
```bash
docker compose build --no-cache ui
docker compose up -d
```

---

## Post-Demo Checklist

After the demo, if you want to reset for the next session:

```bash
# Wipe demo data (keeps DB schema intact)
docker compose exec api python scripts/seed_data.py --clean

# Stop all services
docker compose down
```

---

*FleetOpsX — Phase 1 MVP — Last updated 2026-03-29*
