# GENSPEC – UI Infrastructure & Setup

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | UI Infrastructure & Setup |
| **Status** | Implemented |
| **Version** | 1.0 |
| **Date** | 2025-12-25 |
| **Author** | Antigravity |

---

## 1. Goal

Initialize the base infrastructure for FleetOpsX UI, including Dockerization and observability integration.

---

## 2. Implementation Guide

### Checkpoint 1: Dockerization

**Tasks:**
- Create a multi-stage `Dockerfile` in the root.
- Stage 1: Build the app using Node.js.
- Stage 2 (Dev): Run Vite dev server.
- Stage 3 (Prod): Serve `dist` using Nginx.

**Verification:**
- `docker build -t fleetopsx-ui .` succeeds.
- Container starts and serves the app on the configured port.

---

### Checkpoint 2: Observability (Sentry)

**Tasks:**
- Add `@sentry/react` to `package.json`.
- Initialize Sentry in `src/main.tsx` using `import.meta.env.VITE_SENTRY_DSN`.
- Configure tracing and replay integrations.

**Verification:**
- Sentry captures errors during development when a test error is thrown.
- No DSN in environment results in silent bypass of initialization.

---

### Checkpoint 3: CI/CD Foundations

**Tasks:**
- Create `.github/workflows/ci-ui.yml`.
- Add steps for `npm ci`, `npm run lint`, and `npm run build`.

**Verification:**
- Workflow correctly identifies linting errors or build failures.
