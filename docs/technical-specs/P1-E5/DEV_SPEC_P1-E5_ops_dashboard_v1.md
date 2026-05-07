# Ops Dashboard UI – Technical Specification

> **For AI Coding Assistants:** Build with React + TypeScript + Tailwind. Every screen fetches from the backend API using React Query hooks. Use the existing component primitives (Button, Card, Input) already in `src/components/ui/`. Build screens in order — login → layout → orders → planning → drivers/vehicles/depots.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Ops Dashboard UI |
| **Epic** | P1-E5 |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | P1-E3 APIs + P1-E3-S6 Auth JWT |
| **Implementation Branch** | feat/p1-e5-ops-dashboard |

---

## Executive Summary

**Purpose:** Build the dispatcher-facing web dashboard. Dispatcher logs in, sees today's orders, generates a plan with one click, reviews assignments, and confirms. Also has management screens for drivers, vehicles, depots. This is the primary investor demo surface.

### Key Deliverables

| Screen | Route | Status |
|--------|-------|--------|
| Login page | `/login` | 🔄 Shell exists |
| Dashboard home | `/` | ⬜ |
| Orders list + create | `/orders` | ⬜ |
| Planning view + generate | `/planning` | ⬜ |
| Drivers management | `/drivers` | ⬜ |
| Vehicles management | `/vehicles` | ⬜ |
| Depots management | `/depots` | ⬜ |

### Demo Flow (investor walkthrough)
```
1. Login as dispatcher
2. See today's dashboard — X orders unassigned
3. Click "Generate Plan" → AI assigns orders to drivers
4. Review assignments table
5. Confirm plan → status changes to Published
6. Show driver list with route count
```

---

## 1. Project Structure

```
src/
  api/
    client.ts              ← axios instance (exists)
    auth.ts                ← login/register calls
    depots.ts              ← depot CRUD calls
    drivers.ts             ← driver CRUD calls
    vehicles.ts            ← vehicle CRUD calls
    orders.ts              ← order CRUD calls
    planning.ts            ← plan/day call
  hooks/
    useAuth.ts             ← login mutation + token storage
    useDepots.ts           ← useQuery + useMutation for depots
    useDrivers.ts
    useVehicles.ts
    useOrders.ts
    usePlanning.ts
  components/
    ui/                    ← exists: Button, Card, Input
    layout/
      AppLayout.tsx        ← sidebar + topbar shell
      PageLayout.tsx       ← exists (update it)
      Sidebar.tsx          ← nav links
      TopBar.tsx           ← tenant name + user info + logout
    orders/
      OrdersTable.tsx      ← table of orders with status badges
      OrderForm.tsx        ← create/edit order modal
    planning/
      PlanResult.tsx       ← assignments table after plan generated
    drivers/
      DriversTable.tsx
    vehicles/
      VehiclesTable.tsx
    depots/
      DepotsTable.tsx
    shared/
      StatusBadge.tsx      ← colored badge for PENDING/ASSIGNED/etc
      LoadingSpinner.tsx
      EmptyState.tsx
      ConfirmDialog.tsx
  pages/
    Login.tsx              ← update existing shell
    Dashboard.tsx          ← home — stats + quick actions
    Orders.tsx
    Planning.tsx
    Drivers.tsx
    Vehicles.tsx
    Depots.tsx
  routes/
    AppRoutes.tsx          ← update: add all routes + auth guard
    ProtectedRoute.tsx     ← redirect to /login if not authenticated
  store/
    useAppStore.ts         ← exists: add currentTenant, user info
  types/
    index.ts               ← TypeScript interfaces matching API responses
```

---

## 2. TypeScript Types — `src/types/index.ts`

```typescript
export interface Tenant {
  id: string
  name: string
  slug: string
}

export interface User {
  user_id: string
  tenant_id: string
  role: 'dispatcher' | 'driver' | 'admin'
  full_name: string
  access_token: string
}

export interface Depot {
  id: string
  tenant_id: string
  name: string
  address?: string
  city?: string
  latitude?: number
  longitude?: number
  is_active: boolean
  created_at: string
}

export interface Driver {
  id: string
  tenant_id: string
  full_name: string
  phone?: string
  email?: string
  home_depot_id?: string
  is_active: boolean
}

export interface Vehicle {
  id: string
  tenant_id: string
  registration_number: string
  vehicle_type: string
  capacity_kg?: number
  is_active: boolean
}

export interface Order {
  id: string
  tenant_id: string
  external_ref?: string
  customer_id?: string
  delivery_address: string
  delivery_latitude?: number
  delivery_longitude?: number
  scheduled_date: string
  time_window_start?: string
  time_window_end?: string
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL'
  status: 'PENDING' | 'ASSIGNED' | 'IN_TRANSIT' | 'DELIVERED' | 'FAILED' | 'CANCELLED'
  assigned_driver_id?: string
  weight_kg?: number
  created_at: string
}

export interface Assignment {
  order_id: string
  driver_id: string
  driver_name: string
  sequence: number
}

export interface PlanResult {
  plan_id: string
  plan_date: string
  status: 'DRAFT' | 'PUBLISHED'
  total_orders: number
  assigned_orders: number
  total_routes: number
  assignments: Assignment[]
}
```

---

## 3. API Client Modules

### `src/api/client.ts` (update existing)

```typescript
import axios from 'axios'
import useAppStore from '../store/useAppStore'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Attach JWT token to every request
client.interceptors.request.use((config) => {
  const token = useAppStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default client
```

### `src/api/auth.ts`

```typescript
import client from './client'
import { User } from '../types'

export const loginApi = (email: string, password: string, tenant_id: string): Promise<User> =>
  client.post('/api/v1/auth/login', { email, password, tenant_id }).then(r => r.data)
```

### `src/api/orders.ts`

```typescript
import client from './client'
import { Order } from '../types'

export const fetchOrders = (params?: { plan_date?: string; status?: string; unassigned_only?: boolean }): Promise<Order[]> =>
  client.get('/api/v1/orders/', { params }).then(r => r.data)

export const createOrder = (data: Partial<Order>): Promise<Order> =>
  client.post('/api/v1/orders/', data).then(r => r.data)

export const updateOrder = (id: string, data: Partial<Order>): Promise<Order> =>
  client.patch(`/api/v1/orders/${id}`, data).then(r => r.data)
```

### `src/api/planning.ts`

```typescript
import client from './client'
import { PlanResult } from '../types'

export const generatePlan = (plan_date: string): Promise<PlanResult> =>
  client.post('/api/v1/plan/day', null, { params: { plan_date } }).then(r => r.data)
```

Create similar files for `depots.ts`, `drivers.ts`, `vehicles.ts` — same CRUD pattern.

---

## 4. Auth Store Update — `src/store/useAppStore.ts`

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '../types'

interface AppState {
  theme: 'light' | 'dark'
  accessToken: string | null
  user: User | null
  setTheme: (theme: 'light' | 'dark') => void
  setAuth: (user: User) => void
  clearAuth: () => void
}

const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'light',
      accessToken: null,
      user: null,
      setTheme: (theme) => set({ theme }),
      setAuth: (user) => set({ accessToken: user.access_token, user }),
      clearAuth: () => set({ accessToken: null, user: null }),
    }),
    {
      name: 'app-store',
      partialize: (state) => ({ theme: state.theme, accessToken: state.accessToken, user: state.user }),
    }
  )
)

export default useAppStore
```

---

## 5. Routing — `src/routes/AppRoutes.tsx`

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from './ProtectedRoute'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Orders from '../pages/Orders'
import Planning from '../pages/Planning'
import Drivers from '../pages/Drivers'
import Vehicles from '../pages/Vehicles'
import Depots from '../pages/Depots'
import DriverView from '../pages/DriverView'
import useAppStore from '../store/useAppStore'

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        {/* Dispatcher routes */}
        <Route path="/" element={<ProtectedRoute role="dispatcher"><Dashboard /></ProtectedRoute>} />
        <Route path="/orders" element={<ProtectedRoute role="dispatcher"><Orders /></ProtectedRoute>} />
        <Route path="/planning" element={<ProtectedRoute role="dispatcher"><Planning /></ProtectedRoute>} />
        <Route path="/drivers" element={<ProtectedRoute role="dispatcher"><Drivers /></ProtectedRoute>} />
        <Route path="/vehicles" element={<ProtectedRoute role="dispatcher"><Vehicles /></ProtectedRoute>} />
        <Route path="/depots" element={<ProtectedRoute role="dispatcher"><Depots /></ProtectedRoute>} />
        {/* Driver route */}
        <Route path="/driver" element={<ProtectedRoute role="driver"><DriverView /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### `src/routes/ProtectedRoute.tsx`

```tsx
import { Navigate } from 'react-router-dom'
import useAppStore from '../store/useAppStore'

interface Props {
  children: React.ReactNode
  role?: 'dispatcher' | 'driver'
}

export default function ProtectedRoute({ children, role }: Props) {
  const user = useAppStore(s => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role && user.role !== 'admin') {
    return <Navigate to={user.role === 'driver' ? '/driver' : '/'} replace />
  }
  return <>{children}</>
}
```

---

## 6. Login Page — `src/pages/Login.tsx`

```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginApi } from '../api/auth'
import useAppStore from '../store/useAppStore'
import Input from '../components/ui/Input'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAppStore(s => s.setAuth)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tenantId, setTenantId] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const user = await loginApi(email, password, tenantId)
      setAuth(user)
      navigate(user.role === 'driver' ? '/driver' : '/')
    } catch {
      setError('Invalid credentials. Check your email, password, and Tenant ID.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center p-4">
      <Card>
        <div className="w-full max-w-sm space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">FleetOpsX</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Sign in to your fleet</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <Input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="dispatcher@demo.com" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <Input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Tenant ID</label>
              <Input value={tenantId} onChange={e => setTenantId(e.target.value)} required placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
              <p className="text-xs text-gray-400 mt-1">Found in your welcome email or from the seed script output</p>
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </div>
      </Card>
    </div>
  )
}
```

---

## 7. App Layout — `src/components/layout/AppLayout.tsx`

```tsx
import { Link, useLocation, useNavigate } from 'react-router-dom'
import useAppStore from '../../store/useAppStore'
import { LayoutDashboard, Package, Route, Truck, Car, MapPin, LogOut } from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/orders', label: 'Orders', icon: Package },
  { path: '/planning', label: 'Planning', icon: Route },
  { path: '/drivers', label: 'Drivers', icon: Truck },
  { path: '/vehicles', label: 'Vehicles', icon: Car },
  { path: '/depots', label: 'Depots', icon: MapPin },
]

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, clearAuth } = useAppStore()

  const handleLogout = () => { clearAuth(); navigate('/login') }

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      {/* Sidebar */}
      <aside className="w-56 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-lg font-bold text-blue-600">FleetOpsX</h1>
          <p className="text-xs text-gray-500 truncate">{user?.full_name}</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map(({ path, label, icon: Icon }) => (
            <Link
              key={path}
              to={path}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                ${location.pathname === path
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900 dark:text-blue-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
                }`}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-5 py-4 text-sm text-gray-500 hover:text-red-500 border-t border-gray-200 dark:border-gray-700"
        >
          <LogOut size={16} /> Logout
        </button>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
```

---

## 8. Key Pages

### `src/pages/Dashboard.tsx`

Show stat cards: total orders today, assigned, unassigned, total drivers, total vehicles. Quick link to Planning.

```tsx
import { useQuery } from '@tanstack/react-query'
import AppLayout from '../components/layout/AppLayout'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { fetchOrders } from '../api/orders'
import { fetchDrivers } from '../api/drivers'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const today = new Date().toISOString().split('T')[0]
  const { data: orders = [] } = useQuery({ queryKey: ['orders', today], queryFn: () => fetchOrders({ plan_date: today }) })
  const { data: drivers = [] } = useQuery({ queryKey: ['drivers'], queryFn: () => fetchDrivers() })

  const unassigned = orders.filter(o => o.status === 'PENDING').length
  const assigned = orders.filter(o => o.status === 'ASSIGNED').length

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold dark:text-white">Today's Overview</h2>
          <Link to="/planning">
            <Button>Generate Plan</Button>
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Orders" value={orders.length} color="blue" />
          <StatCard label="Unassigned" value={unassigned} color="red" />
          <StatCard label="Assigned" value={assigned} color="green" />
          <StatCard label="Active Drivers" value={drivers.filter(d => d.is_active).length} color="purple" />
        </div>
      </div>
    </AppLayout>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    blue: 'text-blue-600', red: 'text-red-500', green: 'text-green-500', purple: 'text-purple-500'
  }
  return (
    <Card>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${colors[color]}`}>{value}</p>
    </Card>
  )
}
```

---

### `src/pages/Planning.tsx` — the key demo screen

```tsx
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import AppLayout from '../components/layout/AppLayout'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { generatePlan } from '../api/planning'
import { fetchOrders } from '../api/orders'
import { PlanResult } from '../types'
import toast from 'react-hot-toast'

export default function Planning() {
  const [planDate, setPlanDate] = useState(new Date().toISOString().split('T')[0])
  const [planResult, setPlanResult] = useState<PlanResult | null>(null)

  const { data: orders = [], refetch: refetchOrders } = useQuery({
    queryKey: ['orders', planDate],
    queryFn: () => fetchOrders({ plan_date: planDate }),
  })

  const planMutation = useMutation({
    mutationFn: () => generatePlan(planDate),
    onSuccess: (data) => {
      setPlanResult(data)
      refetchOrders()
      toast.success(`Plan generated! ${data.assigned_orders} orders assigned across ${data.total_routes} routes.`)
    },
    onError: () => toast.error('Failed to generate plan'),
  })

  const unassigned = orders.filter(o => o.status === 'PENDING')

  return (
    <AppLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold dark:text-white">Planning</h2>
          <div className="flex items-center gap-3">
            <input type="date" value={planDate} onChange={e => setPlanDate(e.target.value)}
              className="border rounded px-3 py-2 text-sm dark:bg-gray-700 dark:text-white" />
            <Button
              onClick={() => planMutation.mutate()}
              disabled={planMutation.isPending || unassigned.length === 0}
            >
              {planMutation.isPending ? 'Planning...' : `Generate Plan (${unassigned.length} unassigned)`}
            </Button>
          </div>
        </div>

        {/* Unassigned orders */}
        <Card>
          <h3 className="font-semibold mb-3 dark:text-white">Unassigned Orders — {planDate}</h3>
          {unassigned.length === 0 ? (
            <p className="text-sm text-gray-400">No unassigned orders for this date.</p>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="text-left text-gray-500 border-b">
                <th className="pb-2">Address</th>
                <th className="pb-2">Priority</th>
                <th className="pb-2">Time Window</th>
              </tr></thead>
              <tbody>
                {unassigned.slice(0, 10).map(order => (
                  <tr key={order.id} className="border-b last:border-0 dark:border-gray-700">
                    <td className="py-2 dark:text-gray-200">{order.delivery_address}</td>
                    <td className="py-2"><PriorityBadge priority={order.priority} /></td>
                    <td className="py-2 text-gray-500">{order.time_window_start} – {order.time_window_end}</td>
                  </tr>
                ))}
                {unassigned.length > 10 && <tr><td colSpan={3} className="text-gray-400 py-2">+{unassigned.length - 10} more...</td></tr>}
              </tbody>
            </table>
          )}
        </Card>

        {/* Plan result */}
        {planResult && (
          <Card>
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold dark:text-white">
                Plan Result — {planResult.assigned_orders}/{planResult.total_orders} orders assigned, {planResult.total_routes} routes
              </h3>
              <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">DRAFT</span>
            </div>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-gray-500 border-b">
                <th className="pb-2">#</th>
                <th className="pb-2">Driver</th>
                <th className="pb-2">Delivery Address</th>
                <th className="pb-2">Stop</th>
              </tr></thead>
              <tbody>
                {planResult.assignments.map((a, i) => (
                  <tr key={i} className="border-b last:border-0 dark:border-gray-700">
                    <td className="py-2 text-gray-400">{i + 1}</td>
                    <td className="py-2 font-medium dark:text-gray-200">{a.driver_name}</td>
                    <td className="py-2 text-gray-500 truncate max-w-xs">{a.order_id.slice(0, 8)}...</td>
                    <td className="py-2 text-gray-400">Stop {a.sequence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </div>
    </AppLayout>
  )
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-700',
    HIGH: 'bg-orange-100 text-orange-700',
    NORMAL: 'bg-gray-100 text-gray-600',
    LOW: 'bg-blue-100 text-blue-600',
  }
  return <span className={`text-xs px-2 py-0.5 rounded ${colors[priority] || colors.NORMAL}`}>{priority}</span>
}
```

---

### `src/pages/Orders.tsx`

Show paginated orders table with status filter. Include a "Create Order" button that opens a simple form modal. Use the same table pattern as Planning page.

Key columns: External Ref, Address, Scheduled Date, Priority, Status, Assigned Driver.

---

### `src/pages/Drivers.tsx`, `Vehicles.tsx`, `Depots.tsx`

Same pattern for all three:
- Table showing list of records
- "Add" button opens a form (use react-hook-form + zod)
- Inline edit via PATCH endpoint
- Toggle `is_active` status

---

## 9. File Checklist

| Action | File | Status |
|--------|------|--------|
| CREATE | `src/types/index.ts` | ⬜ |
| UPDATE | `src/api/client.ts` (add JWT interceptor) | ⬜ |
| CREATE | `src/api/auth.ts` | ⬜ |
| CREATE | `src/api/orders.ts` | ⬜ |
| CREATE | `src/api/planning.ts` | ⬜ |
| CREATE | `src/api/drivers.ts` | ⬜ |
| CREATE | `src/api/vehicles.ts` | ⬜ |
| CREATE | `src/api/depots.ts` | ⬜ |
| UPDATE | `src/store/useAppStore.ts` | ⬜ |
| CREATE | `src/routes/ProtectedRoute.tsx` | ⬜ |
| UPDATE | `src/routes/AppRoutes.tsx` | ⬜ |
| UPDATE | `src/pages/Login.tsx` | ⬜ |
| CREATE | `src/components/layout/AppLayout.tsx` | ⬜ |
| CREATE | `src/components/layout/Sidebar.tsx` | ⬜ |
| CREATE | `src/pages/Dashboard.tsx` | ⬜ |
| CREATE | `src/pages/Planning.tsx` | ⬜ |
| CREATE | `src/pages/Orders.tsx` | ⬜ |
| CREATE | `src/pages/Drivers.tsx` | ⬜ |
| CREATE | `src/pages/Vehicles.tsx` | ⬜ |
| CREATE | `src/pages/Depots.tsx` | ⬜ |
| CREATE | `src/components/shared/StatusBadge.tsx` | ⬜ |
| CREATE | `src/components/shared/LoadingSpinner.tsx` | ⬜ |
| CREATE | `src/components/shared/EmptyState.tsx` | ⬜ |

---

**Document Status:** Not Started  
**Last Updated:** 2026-03-29
