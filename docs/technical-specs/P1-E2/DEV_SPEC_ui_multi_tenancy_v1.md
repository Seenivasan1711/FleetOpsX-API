# GENSPEC – UI Multi-Tenant Integration

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | UI Multi-Tenant Foundations (P1-E2) |
| **Status** | Draft |
| **Version** | 1.0 |
| **Date** | 2025-12-25 |
| **Author** | Antigravity |

---

## 1. Goal

Update the FleetOpsX UI to support multi-tenancy by managing tenant state and passing the `X-Tenant-ID` header in API requests.

---

## 2. Implementation Guide

### Checkpoint 1: Global Tenant State

**Tasks:**
- Create `src/store/useTenantStore.ts` using Zustand.
- Store `currentTenantId` (UUID string).
- Initialize from a constant or environment variable for Phase 1.

**Verification:**
- Components can successfully read and log the `currentTenantId` from the store.

---

### Checkpoint 2: Axios Interceptor

**Tasks:**
- Modify `src/api/apiClient.ts`.
- Add a request interceptor that reads the `currentTenantId` from the Zustand store.
- Append `headers['X-Tenant-ID'] = currentTenantId` to every outgoing request.

**Verification:**
- Network tab in DevTools shows the `X-Tenant-ID` header in all outgoing requests.

---

### Checkpoint 3: UI Feedback (Optional)

**Tasks:**
- Add a small "Active Tenant" badge in the main layout to verify visually which tenant is active.

**Verification:**
- Badge correctly reflects the state in the store.
