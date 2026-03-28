# Ops Dashboard – Fully Functional CRUD Screens (Addendum)

> **Purpose:** This addendum extends `GENSPEC_P1-E5_ops_dashboard_v1.md`.
> That spec covers Login, AppLayout, Dashboard, and Planning pages.
> This spec covers the remaining 4 CRUD screens (Orders, Drivers, Vehicles, Depots)
> with complete working code — not prose descriptions.
>
> **For AI Coding Assistants:** Implement the base E5 spec first (Login → Dashboard → Planning),
> then implement this addendum. Every page here follows the same pattern:
> table list + slide-over form modal + react-hook-form + zod validation.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Ops Dashboard – Full CRUD Screens |
| **Epic** | P1-E5 (Addendum) |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | `GENSPEC_P1-E5_ops_dashboard_v1.md` base spec complete |

---

## Shared Pattern — Read First

Every CRUD screen follows this exact structure:

```
Page
├── AppLayout wrapper
├── Page header (title + "Add X" button)
├── Filter bar (search input + status/type filters)
├── DataTable component (sortable, shows all records)
│   ├── Row with edit icon button → opens FormModal in edit mode
│   └── Row with toggle (is_active) → PATCH inline
└── FormModal (slide-over panel)
    ├── react-hook-form + zod schema
    ├── On submit → POST (create) or PATCH (edit)
    └── On success → close modal + refetch query
```

---

## 1. Shared Components

### `src/components/shared/FormModal.tsx`

Reusable slide-over panel that wraps any form.

```tsx
import { X } from 'lucide-react'

interface FormModalProps {
  title: string
  isOpen: boolean
  onClose: () => void
  children: React.ReactNode
}

export default function FormModal({ title, isOpen, onClose, children }: FormModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
      />
      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-full max-w-md bg-white dark:bg-gray-900 shadow-xl flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold dark:text-white">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </div>
  )
}
```

### `src/components/shared/DataTable.tsx`

Reusable table wrapper with consistent styling.

```tsx
interface Column<T> {
  key: string
  header: string
  render: (row: T) => React.ReactNode
  width?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  isLoading?: boolean
  emptyMessage?: string
}

export default function DataTable<T>({ columns, data, isLoading, emptyMessage = 'No records found' }: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-40">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-400 text-xs uppercase tracking-wide"
                style={col.width ? { width: col.width } : {}}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-900">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center py-10 text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-3 dark:text-gray-200">
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
```

### `src/components/shared/StatusBadge.tsx`

```tsx
const STATUS_STYLES: Record<string, string> = {
  // Order statuses
  PENDING:    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  ASSIGNED:   'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  IN_TRANSIT: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  DELIVERED:  'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  FAILED:     'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  CANCELLED:  'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  // Active/Inactive
  ACTIVE:     'bg-green-100 text-green-800',
  INACTIVE:   'bg-gray-100 text-gray-500',
  // Priority
  CRITICAL:   'bg-red-100 text-red-700',
  HIGH:       'bg-orange-100 text-orange-700',
  NORMAL:     'bg-gray-100 text-gray-600',
  LOW:        'bg-blue-100 text-blue-600',
}

export default function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[value] || STATUS_STYLES.NORMAL}`}>
      {value}
    </span>
  )
}
```

### `src/components/shared/FormField.tsx`

Reusable labeled form field wrapper.

```tsx
interface FormFieldProps {
  label: string
  error?: string
  required?: boolean
  children: React.ReactNode
}

export default function FormField({ label, error, required, children }: FormFieldProps) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}
```

### `src/components/shared/ToggleSwitch.tsx`

```tsx
interface ToggleSwitchProps {
  checked: boolean
  onChange: (val: boolean) => void
  disabled?: boolean
}

export default function ToggleSwitch({ checked, onChange, disabled }: ToggleSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors
        ${checked ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform
          ${checked ? 'translate-x-4' : 'translate-x-0'}`}
      />
    </button>
  )
}
```

---

## 2. Complete API Client Files

### `src/api/depots.ts`

```typescript
import client from './client'
import { Depot } from '../types'

export const fetchDepots = (params?: { active_only?: boolean }): Promise<Depot[]> =>
  client.get('/api/v1/depots/', { params }).then(r => r.data)

export const fetchDepot = (id: string): Promise<Depot> =>
  client.get(`/api/v1/depots/${id}`).then(r => r.data)

export const createDepot = (data: Partial<Depot>): Promise<Depot> =>
  client.post('/api/v1/depots/', data).then(r => r.data)

export const updateDepot = (id: string, data: Partial<Depot>): Promise<Depot> =>
  client.patch(`/api/v1/depots/${id}`, data).then(r => r.data)

export const deleteDepot = (id: string): Promise<void> =>
  client.delete(`/api/v1/depots/${id}`).then(r => r.data)
```

### `src/api/drivers.ts`

```typescript
import client from './client'
import { Driver } from '../types'

export const fetchDrivers = (params?: { active_only?: boolean; depot_id?: string }): Promise<Driver[]> =>
  client.get('/api/v1/drivers/', { params }).then(r => r.data)

export const fetchDriver = (id: string): Promise<Driver> =>
  client.get(`/api/v1/drivers/${id}`).then(r => r.data)

export const createDriver = (data: Partial<Driver>): Promise<Driver> =>
  client.post('/api/v1/drivers/', data).then(r => r.data)

export const updateDriver = (id: string, data: Partial<Driver>): Promise<Driver> =>
  client.patch(`/api/v1/drivers/${id}`, data).then(r => r.data)

export const deleteDriver = (id: string): Promise<void> =>
  client.delete(`/api/v1/drivers/${id}`).then(r => r.data)
```

### `src/api/vehicles.ts`

```typescript
import client from './client'
import { Vehicle } from '../types'

export const fetchVehicles = (params?: { active_only?: boolean; depot_id?: string }): Promise<Vehicle[]> =>
  client.get('/api/v1/vehicles/', { params }).then(r => r.data)

export const fetchVehicle = (id: string): Promise<Vehicle> =>
  client.get(`/api/v1/vehicles/${id}`).then(r => r.data)

export const createVehicle = (data: Partial<Vehicle>): Promise<Vehicle> =>
  client.post('/api/v1/vehicles/', data).then(r => r.data)

export const updateVehicle = (id: string, data: Partial<Vehicle>): Promise<Vehicle> =>
  client.patch(`/api/v1/vehicles/${id}`, data).then(r => r.data)

export const deleteVehicle = (id: string): Promise<void> =>
  client.delete(`/api/v1/vehicles/${id}`).then(r => r.data)
```

### `src/api/orders.ts` (complete version)

```typescript
import client from './client'
import { Order } from '../types'

export const fetchOrders = (params?: {
  plan_date?: string
  status?: string
  unassigned_only?: boolean
}): Promise<Order[]> =>
  client.get('/api/v1/orders/', { params }).then(r => r.data)

export const fetchOrder = (id: string): Promise<Order> =>
  client.get(`/api/v1/orders/${id}`).then(r => r.data)

export const createOrder = (data: Partial<Order>): Promise<Order> =>
  client.post('/api/v1/orders/', data).then(r => r.data)

export const updateOrder = (id: string, data: Partial<Order>): Promise<Order> =>
  client.patch(`/api/v1/orders/${id}`, data).then(r => r.data)
```

---

## 3. `src/pages/Depots.tsx` — Full Implementation

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Pencil, Plus, MapPin } from 'lucide-react'
import toast from 'react-hot-toast'
import AppLayout from '../components/layout/AppLayout'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Card from '../components/ui/Card'
import FormModal from '../components/shared/FormModal'
import FormField from '../components/shared/FormField'
import DataTable from '../components/shared/DataTable'
import ToggleSwitch from '../components/shared/ToggleSwitch'
import { fetchDepots, createDepot, updateDepot } from '../api/depots'
import { Depot } from '../types'

const depotSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  address: z.string().optional(),
  city: z.string().optional(),
  state: z.string().optional(),
  country: z.string().default('India'),
  pincode: z.string().optional(),
  latitude: z.preprocess(v => v === '' ? undefined : Number(v), z.number().optional()),
  longitude: z.preprocess(v => v === '' ? undefined : Number(v), z.number().optional()),
})

type DepotFormData = z.infer<typeof depotSchema>

export default function Depots() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingDepot, setEditingDepot] = useState<Depot | null>(null)
  const [search, setSearch] = useState('')

  const { data: depots = [], isLoading } = useQuery({
    queryKey: ['depots'],
    queryFn: () => fetchDepots({ active_only: false }),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<DepotFormData>({
    resolver: zodResolver(depotSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: DepotFormData) =>
      editingDepot
        ? updateDepot(editingDepot.id, data)
        : createDepot(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['depots'] })
      toast.success(editingDepot ? 'Depot updated' : 'Depot created')
      handleClose()
    },
    onError: () => toast.error('Something went wrong'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateDepot(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['depots'] }),
  })

  const handleOpen = (depot?: Depot) => {
    setEditingDepot(depot || null)
    reset(depot ? {
      name: depot.name,
      address: depot.address || '',
      city: depot.city || '',
      state: '',
      country: 'India',
      pincode: '',
      latitude: depot.latitude,
      longitude: depot.longitude,
    } : { country: 'India' })
    setModalOpen(true)
  }

  const handleClose = () => {
    setModalOpen(false)
    setEditingDepot(null)
    reset()
  }

  const filtered = depots.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    (d.city || '').toLowerCase().includes(search.toLowerCase())
  )

  const columns = [
    {
      key: 'name', header: 'Name',
      render: (d: Depot) => (
        <div className="flex items-center gap-2">
          <MapPin size={14} className="text-blue-500 shrink-0" />
          <span className="font-medium">{d.name}</span>
        </div>
      ),
    },
    { key: 'city', header: 'City', render: (d: Depot) => d.city || '—' },
    {
      key: 'coords', header: 'Coordinates',
      render: (d: Depot) => d.latitude
        ? <span className="text-xs text-gray-400">{d.latitude.toFixed(4)}, {d.longitude?.toFixed(4)}</span>
        : <span className="text-xs text-gray-400">—</span>,
    },
    {
      key: 'active', header: 'Active', width: '80px',
      render: (d: Depot) => (
        <ToggleSwitch
          checked={d.is_active}
          onChange={(val) => toggleMutation.mutate({ id: d.id, is_active: val })}
        />
      ),
    },
    {
      key: 'actions', header: '', width: '60px',
      render: (d: Depot) => (
        <button onClick={() => handleOpen(d)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
          <Pencil size={14} className="text-gray-400" />
        </button>
      ),
    },
  ]

  return (
    <AppLayout>
      <div className="space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold dark:text-white">Depots</h2>
            <p className="text-sm text-gray-500">{depots.length} total</p>
          </div>
          <Button onClick={() => handleOpen()}>
            <Plus size={16} className="mr-1" /> Add Depot
          </Button>
        </div>

        {/* Search */}
        <Input
          placeholder="Search depots..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-xs"
        />

        {/* Table */}
        <Card>
          <DataTable columns={columns} data={filtered} isLoading={isLoading} emptyMessage="No depots yet. Add your first depot." />
        </Card>
      </div>

      {/* Form Modal */}
      <FormModal
        title={editingDepot ? 'Edit Depot' : 'Add Depot'}
        isOpen={modalOpen}
        onClose={handleClose}
      >
        <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
          <FormField label="Name" error={errors.name?.message} required>
            <Input {...register('name')} placeholder="Koramangala Depot" error={!!errors.name} />
          </FormField>
          <FormField label="Address" error={errors.address?.message}>
            <Input {...register('address')} placeholder="123, 5th Block..." />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="City">
              <Input {...register('city')} placeholder="Bangalore" />
            </FormField>
            <FormField label="Pincode">
              <Input {...register('pincode')} placeholder="560034" />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Latitude" error={errors.latitude?.message}>
              <Input {...register('latitude')} type="number" step="any" placeholder="12.9716" />
            </FormField>
            <FormField label="Longitude" error={errors.longitude?.message}>
              <Input {...register('longitude')} type="number" step="any" placeholder="77.5946" />
            </FormField>
          </div>
          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={mutation.isPending} className="flex-1">
              {mutation.isPending ? 'Saving...' : editingDepot ? 'Update Depot' : 'Create Depot'}
            </Button>
            <button type="button" onClick={handleClose}
              className="flex-1 py-2 rounded border border-gray-300 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800">
              Cancel
            </button>
          </div>
        </form>
      </FormModal>
    </AppLayout>
  )
}
```

---

## 4. `src/pages/Drivers.tsx` — Full Implementation

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Pencil, Plus, User } from 'lucide-react'
import toast from 'react-hot-toast'
import AppLayout from '../components/layout/AppLayout'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Card from '../components/ui/Card'
import FormModal from '../components/shared/FormModal'
import FormField from '../components/shared/FormField'
import DataTable from '../components/shared/DataTable'
import ToggleSwitch from '../components/shared/ToggleSwitch'
import { fetchDrivers, createDriver, updateDriver } from '../api/drivers'
import { fetchDepots } from '../api/depots'
import { Driver, Depot } from '../types'

const driverSchema = z.object({
  full_name: z.string().min(1, 'Name is required'),
  phone: z.string().optional(),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  license_number: z.string().optional(),
  license_class: z.string().optional(),
  home_depot_id: z.string().uuid('Select a depot').optional().or(z.literal('')),
  default_shift_start: z.string().optional(),
  default_shift_end: z.string().optional(),
})

type DriverFormData = z.infer<typeof driverSchema>

export default function Drivers() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingDriver, setEditingDriver] = useState<Driver | null>(null)
  const [search, setSearch] = useState('')

  const { data: drivers = [], isLoading } = useQuery({
    queryKey: ['drivers'],
    queryFn: () => fetchDrivers({ active_only: false }),
  })

  const { data: depots = [] } = useQuery({
    queryKey: ['depots'],
    queryFn: () => fetchDepots({ active_only: true }),
  })

  const depotMap = Object.fromEntries(depots.map((d: Depot) => [d.id, d.name]))

  const { register, handleSubmit, reset, formState: { errors } } = useForm<DriverFormData>({
    resolver: zodResolver(driverSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: DriverFormData) => {
      const payload = { ...data, home_depot_id: data.home_depot_id || undefined }
      return editingDriver
        ? updateDriver(editingDriver.id, payload)
        : createDriver(payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['drivers'] })
      toast.success(editingDriver ? 'Driver updated' : 'Driver created')
      handleClose()
    },
    onError: () => toast.error('Something went wrong'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateDriver(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drivers'] }),
  })

  const handleOpen = (driver?: Driver) => {
    setEditingDriver(driver || null)
    reset(driver ? {
      full_name: driver.full_name,
      phone: driver.phone || '',
      email: driver.email || '',
      license_number: '',
      license_class: '',
      home_depot_id: driver.home_depot_id || '',
      default_shift_start: '',
      default_shift_end: '',
    } : {})
    setModalOpen(true)
  }

  const handleClose = () => { setModalOpen(false); setEditingDriver(null); reset() }

  const filtered = drivers.filter((d: Driver) =>
    d.full_name.toLowerCase().includes(search.toLowerCase()) ||
    (d.phone || '').includes(search)
  )

  const columns = [
    {
      key: 'name', header: 'Driver',
      render: (d: Driver) => (
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
            <User size={13} className="text-blue-600" />
          </div>
          <div>
            <p className="font-medium text-sm">{d.full_name}</p>
            <p className="text-xs text-gray-400">{d.phone || '—'}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'depot', header: 'Home Depot',
      render: (d: Driver) => d.home_depot_id ? depotMap[d.home_depot_id] || '—' : '—',
    },
    { key: 'email', header: 'Email', render: (d: Driver) => d.email || '—' },
    {
      key: 'active', header: 'Active', width: '80px',
      render: (d: Driver) => (
        <ToggleSwitch checked={d.is_active} onChange={(val) => toggleMutation.mutate({ id: d.id, is_active: val })} />
      ),
    },
    {
      key: 'actions', header: '', width: '60px',
      render: (d: Driver) => (
        <button onClick={() => handleOpen(d)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
          <Pencil size={14} className="text-gray-400" />
        </button>
      ),
    },
  ]

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold dark:text-white">Drivers</h2>
            <p className="text-sm text-gray-500">{drivers.filter((d: Driver) => d.is_active).length} active of {drivers.length}</p>
          </div>
          <Button onClick={() => handleOpen()}>
            <Plus size={16} className="mr-1" /> Add Driver
          </Button>
        </div>

        <Input placeholder="Search drivers..." value={search} onChange={e => setSearch(e.target.value)} className="max-w-xs" />

        <Card>
          <DataTable columns={columns} data={filtered} isLoading={isLoading} emptyMessage="No drivers yet." />
        </Card>
      </div>

      <FormModal title={editingDriver ? 'Edit Driver' : 'Add Driver'} isOpen={modalOpen} onClose={handleClose}>
        <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
          <FormField label="Full Name" error={errors.full_name?.message} required>
            <Input {...register('full_name')} placeholder="Ravi Kumar" error={!!errors.full_name} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Phone">
              <Input {...register('phone')} placeholder="9812345678" />
            </FormField>
            <FormField label="Email" error={errors.email?.message}>
              <Input {...register('email')} type="email" placeholder="ravi@email.com" />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="License Number">
              <Input {...register('license_number')} placeholder="KA0120220001234" />
            </FormField>
            <FormField label="License Class">
              <select {...register('license_class')}
                className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600">
                <option value="">Select...</option>
                <option value="LMV">LMV</option>
                <option value="HMV">HMV</option>
                <option value="TRANS">TRANS</option>
              </select>
            </FormField>
          </div>
          <FormField label="Home Depot">
            <select {...register('home_depot_id')}
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600">
              <option value="">No depot assigned</option>
              {depots.map((d: Depot) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Shift Start">
              <Input {...register('default_shift_start')} type="time" />
            </FormField>
            <FormField label="Shift End">
              <Input {...register('default_shift_end')} type="time" />
            </FormField>
          </div>
          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={mutation.isPending} className="flex-1">
              {mutation.isPending ? 'Saving...' : editingDriver ? 'Update Driver' : 'Create Driver'}
            </Button>
            <button type="button" onClick={handleClose}
              className="flex-1 py-2 rounded border border-gray-300 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800">
              Cancel
            </button>
          </div>
        </form>
      </FormModal>
    </AppLayout>
  )
}
```

---

## 5. `src/pages/Vehicles.tsx` — Full Implementation

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Pencil, Plus, Truck, Snowflake } from 'lucide-react'
import toast from 'react-hot-toast'
import AppLayout from '../components/layout/AppLayout'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Card from '../components/ui/Card'
import FormModal from '../components/shared/FormModal'
import FormField from '../components/shared/FormField'
import DataTable from '../components/shared/DataTable'
import ToggleSwitch from '../components/shared/ToggleSwitch'
import { fetchVehicles, createVehicle, updateVehicle } from '../api/vehicles'
import { fetchDepots } from '../api/depots'
import { Vehicle, Depot } from '../types'

const vehicleSchema = z.object({
  registration_number: z.string().min(1, 'Registration number is required'),
  vehicle_type: z.string().min(1, 'Select a type'),
  capacity_kg: z.preprocess(v => v === '' ? undefined : Number(v), z.number().positive().optional()),
  capacity_volume_liters: z.preprocess(v => v === '' ? undefined : Number(v), z.number().positive().optional()),
  capacity_units: z.preprocess(v => v === '' ? undefined : Number(v), z.number().int().positive().optional()),
  is_refrigerated: z.boolean().default(false),
  home_depot_id: z.string().uuid().optional().or(z.literal('')),
})

type VehicleFormData = z.infer<typeof vehicleSchema>

const VEHICLE_TYPES = ['BIKE', 'AUTO', 'VAN', 'TRUCK_SMALL', 'TRUCK_LARGE']

export default function Vehicles() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null)
  const [search, setSearch] = useState('')

  const { data: vehicles = [], isLoading } = useQuery({
    queryKey: ['vehicles'],
    queryFn: () => fetchVehicles({ active_only: false }),
  })

  const { data: depots = [] } = useQuery({
    queryKey: ['depots'],
    queryFn: () => fetchDepots({ active_only: true }),
  })

  const depotMap = Object.fromEntries((depots as Depot[]).map(d => [d.id, d.name]))

  const { register, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<VehicleFormData>({
    resolver: zodResolver(vehicleSchema),
    defaultValues: { is_refrigerated: false, vehicle_type: 'VAN' },
  })

  const isRefrigerated = watch('is_refrigerated')

  const mutation = useMutation({
    mutationFn: (data: VehicleFormData) => {
      const payload = { ...data, home_depot_id: data.home_depot_id || undefined }
      return editingVehicle
        ? updateVehicle(editingVehicle.id, payload)
        : createVehicle(payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicles'] })
      toast.success(editingVehicle ? 'Vehicle updated' : 'Vehicle created')
      handleClose()
    },
    onError: () => toast.error('Something went wrong'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateVehicle(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vehicles'] }),
  })

  const handleOpen = (vehicle?: Vehicle) => {
    setEditingVehicle(vehicle || null)
    reset(vehicle ? {
      registration_number: vehicle.registration_number,
      vehicle_type: vehicle.vehicle_type,
      capacity_kg: vehicle.capacity_kg,
      is_refrigerated: vehicle.is_refrigerated || false,
      home_depot_id: vehicle.home_depot_id || '',
    } : { vehicle_type: 'VAN', is_refrigerated: false })
    setModalOpen(true)
  }

  const handleClose = () => { setModalOpen(false); setEditingVehicle(null); reset() }

  const filtered = (vehicles as Vehicle[]).filter(v =>
    v.registration_number.toLowerCase().includes(search.toLowerCase()) ||
    v.vehicle_type.toLowerCase().includes(search.toLowerCase())
  )

  const columns = [
    {
      key: 'reg', header: 'Registration',
      render: (v: Vehicle) => (
        <div className="flex items-center gap-2">
          <Truck size={14} className="text-blue-500 shrink-0" />
          <div>
            <p className="font-medium text-sm font-mono">{v.registration_number}</p>
            <p className="text-xs text-gray-400">{v.vehicle_type}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'depot', header: 'Depot',
      render: (v: Vehicle) => v.home_depot_id ? depotMap[v.home_depot_id] || '—' : '—',
    },
    {
      key: 'capacity', header: 'Capacity',
      render: (v: Vehicle) => v.capacity_kg ? `${v.capacity_kg} kg` : '—',
    },
    {
      key: 'refrigerated', header: 'Cold Chain',
      render: (v: Vehicle) => v.is_refrigerated
        ? <span className="flex items-center gap-1 text-xs text-blue-500"><Snowflake size={11} /> Yes</span>
        : <span className="text-xs text-gray-400">No</span>,
    },
    {
      key: 'active', header: 'Active', width: '80px',
      render: (v: Vehicle) => (
        <ToggleSwitch checked={v.is_active} onChange={(val) => toggleMutation.mutate({ id: v.id, is_active: val })} />
      ),
    },
    {
      key: 'actions', header: '', width: '60px',
      render: (v: Vehicle) => (
        <button onClick={() => handleOpen(v)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
          <Pencil size={14} className="text-gray-400" />
        </button>
      ),
    },
  ]

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold dark:text-white">Vehicles</h2>
            <p className="text-sm text-gray-500">{(vehicles as Vehicle[]).filter(v => v.is_active).length} active of {vehicles.length}</p>
          </div>
          <Button onClick={() => handleOpen()}>
            <Plus size={16} className="mr-1" /> Add Vehicle
          </Button>
        </div>

        <Input placeholder="Search vehicles..." value={search} onChange={e => setSearch(e.target.value)} className="max-w-xs" />

        <Card>
          <DataTable columns={columns} data={filtered} isLoading={isLoading} emptyMessage="No vehicles yet." />
        </Card>
      </div>

      <FormModal title={editingVehicle ? 'Edit Vehicle' : 'Add Vehicle'} isOpen={modalOpen} onClose={handleClose}>
        <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
          <FormField label="Registration Number" error={errors.registration_number?.message} required>
            <Input {...register('registration_number')} placeholder="KA-01-AB-1234" error={!!errors.registration_number} />
          </FormField>
          <FormField label="Vehicle Type" error={errors.vehicle_type?.message} required>
            <select {...register('vehicle_type')}
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600">
              {VEHICLE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Capacity (kg)">
              <Input {...register('capacity_kg')} type="number" step="0.1" placeholder="500" />
            </FormField>
            <FormField label="Capacity (units)">
              <Input {...register('capacity_units')} type="number" placeholder="100" />
            </FormField>
          </div>
          <FormField label="Home Depot">
            <select {...register('home_depot_id')}
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600">
              <option value="">No depot</option>
              {(depots as Depot[]).map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </FormField>
          <div className="flex items-center gap-3">
            <ToggleSwitch checked={isRefrigerated} onChange={(v) => setValue('is_refrigerated', v)} />
            <label className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-1">
              <Snowflake size={13} className="text-blue-400" /> Refrigerated / Cold Chain
            </label>
          </div>
          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={mutation.isPending} className="flex-1">
              {mutation.isPending ? 'Saving...' : editingVehicle ? 'Update' : 'Create Vehicle'}
            </Button>
            <button type="button" onClick={handleClose}
              className="flex-1 py-2 rounded border border-gray-300 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800">
              Cancel
            </button>
          </div>
        </form>
      </FormModal>
    </AppLayout>
  )
}
```

---

## 6. `src/pages/Orders.tsx` — Full Implementation

```tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Pencil, Plus, Package } from 'lucide-react'
import toast from 'react-hot-toast'
import AppLayout from '../components/layout/AppLayout'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import Card from '../components/ui/Card'
import FormModal from '../components/shared/FormModal'
import FormField from '../components/shared/FormField'
import DataTable from '../components/shared/DataTable'
import StatusBadge from '../components/shared/StatusBadge'
import { fetchOrders, createOrder, updateOrder } from '../api/orders'
import { Order } from '../types'

const orderSchema = z.object({
  delivery_address: z.string().min(1, 'Delivery address is required'),
  delivery_latitude: z.preprocess(v => v === '' ? undefined : Number(v), z.number().optional()),
  delivery_longitude: z.preprocess(v => v === '' ? undefined : Number(v), z.number().optional()),
  scheduled_date: z.string().min(1, 'Date is required'),
  time_window_start: z.string().optional(),
  time_window_end: z.string().optional(),
  priority: z.string().default('NORMAL'),
  weight_kg: z.preprocess(v => v === '' ? undefined : Number(v), z.number().positive().optional()),
  quantity_units: z.preprocess(v => v === '' ? undefined : Number(v), z.number().int().positive().optional()),
  notes: z.string().optional(),
  external_ref: z.string().optional(),
})

type OrderFormData = z.infer<typeof orderSchema>

const STATUS_OPTIONS = ['', 'PENDING', 'ASSIGNED', 'IN_TRANSIT', 'DELIVERED', 'FAILED', 'CANCELLED']
const PRIORITY_OPTIONS = ['LOW', 'NORMAL', 'HIGH', 'CRITICAL']

export default function Orders() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingOrder, setEditingOrder] = useState<Order | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split('T')[0])

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ['orders', dateFilter, statusFilter],
    queryFn: () => fetchOrders({ plan_date: dateFilter || undefined, status: statusFilter || undefined }),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
    defaultValues: { priority: 'NORMAL' },
  })

  const mutation = useMutation({
    mutationFn: (data: OrderFormData) => {
      const payload = {
        ...data,
        scheduled_date: new Date(data.scheduled_date).toISOString(),
      }
      return editingOrder
        ? updateOrder(editingOrder.id, payload)
        : createOrder(payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      toast.success(editingOrder ? 'Order updated' : 'Order created')
      handleClose()
    },
    onError: () => toast.error('Something went wrong'),
  })

  const handleOpen = (order?: Order) => {
    setEditingOrder(order || null)
    reset(order ? {
      delivery_address: order.delivery_address,
      delivery_latitude: order.delivery_latitude,
      delivery_longitude: order.delivery_longitude,
      scheduled_date: order.scheduled_date.split('T')[0],
      time_window_start: order.time_window_start || '',
      time_window_end: order.time_window_end || '',
      priority: order.priority,
      weight_kg: order.weight_kg,
      quantity_units: order.quantity_units,
      notes: order.notes || '',
      external_ref: order.external_ref || '',
    } : { priority: 'NORMAL', scheduled_date: dateFilter })
    setModalOpen(true)
  }

  const handleClose = () => { setModalOpen(false); setEditingOrder(null); reset() }

  const filtered = (orders as Order[]).filter(o =>
    o.delivery_address.toLowerCase().includes(search.toLowerCase()) ||
    (o.external_ref || '').toLowerCase().includes(search.toLowerCase())
  )

  const columns = [
    {
      key: 'ref', header: 'Order',
      render: (o: Order) => (
        <div className="flex items-center gap-2">
          <Package size={14} className="text-blue-500 shrink-0" />
          <div>
            <p className="text-xs font-mono text-gray-400">{o.external_ref || o.id.slice(0, 8)}</p>
            <p className="text-sm text-gray-700 dark:text-gray-200 truncate max-w-xs">{o.delivery_address}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'date', header: 'Date',
      render: (o: Order) => new Date(o.scheduled_date).toLocaleDateString('en-IN'),
    },
    {
      key: 'window', header: 'Time Window',
      render: (o: Order) => o.time_window_start
        ? <span className="text-xs text-gray-500">{o.time_window_start} – {o.time_window_end}</span>
        : <span className="text-xs text-gray-400">—</span>,
    },
    {
      key: 'priority', header: 'Priority',
      render: (o: Order) => <StatusBadge value={o.priority} />,
    },
    {
      key: 'status', header: 'Status',
      render: (o: Order) => <StatusBadge value={o.status} />,
    },
    {
      key: 'actions', header: '', width: '60px',
      render: (o: Order) => (
        <button onClick={() => handleOpen(o)} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
          <Pencil size={14} className="text-gray-400" />
        </button>
      ),
    },
  ]

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold dark:text-white">Orders</h2>
            <p className="text-sm text-gray-500">{orders.length} orders for selected date</p>
          </div>
          <Button onClick={() => handleOpen()}>
            <Plus size={16} className="mr-1" /> Add Order
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <Input
            type="date"
            value={dateFilter}
            onChange={e => setDateFilter(e.target.value)}
            className="w-auto"
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600"
          >
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
          </select>
          <Input
            placeholder="Search address or ref..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 min-w-[200px]"
          />
        </div>

        <Card>
          <DataTable columns={columns} data={filtered} isLoading={isLoading} emptyMessage="No orders for this date." />
        </Card>
      </div>

      <FormModal title={editingOrder ? 'Edit Order' : 'Create Order'} isOpen={modalOpen} onClose={handleClose}>
        <form onSubmit={handleSubmit(d => mutation.mutate(d))} className="space-y-4">
          <FormField label="External Reference">
            <Input {...register('external_ref')} placeholder="ORD-2026-001" />
          </FormField>
          <FormField label="Delivery Address" error={errors.delivery_address?.message} required>
            <Input {...register('delivery_address')} placeholder="123, Koramangala..." error={!!errors.delivery_address} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Latitude">
              <Input {...register('delivery_latitude')} type="number" step="any" placeholder="12.9716" />
            </FormField>
            <FormField label="Longitude">
              <Input {...register('delivery_longitude')} type="number" step="any" placeholder="77.5946" />
            </FormField>
          </div>
          <FormField label="Scheduled Date" error={errors.scheduled_date?.message} required>
            <Input {...register('scheduled_date')} type="date" error={!!errors.scheduled_date} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Window Start">
              <Input {...register('time_window_start')} type="time" />
            </FormField>
            <FormField label="Window End">
              <Input {...register('time_window_end')} type="time" />
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Priority">
              <select {...register('priority')}
                className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600">
                {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </FormField>
            <FormField label="Weight (kg)">
              <Input {...register('weight_kg')} type="number" step="0.1" placeholder="5" />
            </FormField>
          </div>
          <FormField label="Notes">
            <textarea {...register('notes')}
              rows={2}
              className="w-full border rounded px-3 py-2 text-sm dark:bg-gray-800 dark:text-white dark:border-gray-600 resize-none"
              placeholder="Leave at door, call on arrival..." />
          </FormField>
          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={mutation.isPending} className="flex-1">
              {mutation.isPending ? 'Saving...' : editingOrder ? 'Update Order' : 'Create Order'}
            </Button>
            <button type="button" onClick={handleClose}
              className="flex-1 py-2 rounded border border-gray-300 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-800">
              Cancel
            </button>
          </div>
        </form>
      </FormModal>
    </AppLayout>
  )
}
```

---

## 7. Complete File Checklist (Addendum Only)

These are IN ADDITION TO the base E5 spec checklist.

| Action | File | Status |
|--------|------|--------|
| CREATE | `src/components/shared/FormModal.tsx` | ⬜ |
| CREATE | `src/components/shared/DataTable.tsx` | ⬜ |
| CREATE | `src/components/shared/StatusBadge.tsx` | ⬜ |
| CREATE | `src/components/shared/FormField.tsx` | ⬜ |
| CREATE | `src/components/shared/ToggleSwitch.tsx` | ⬜ |
| CREATE (full) | `src/api/depots.ts` | ⬜ |
| CREATE (full) | `src/api/drivers.ts` | ⬜ |
| CREATE (full) | `src/api/vehicles.ts` | ⬜ |
| UPDATE (full) | `src/api/orders.ts` | ⬜ |
| CREATE | `src/pages/Depots.tsx` | ⬜ |
| CREATE | `src/pages/Drivers.tsx` | ⬜ |
| CREATE | `src/pages/Vehicles.tsx` | ⬜ |
| CREATE | `src/pages/Orders.tsx` | ⬜ |

---

## 8. Verification

```bash
# Start UI
cd FleetOpsX-UI && npm run dev

# Login as dispatcher → check each screen:

# Depots screen
# - Open http://localhost:5173/depots
# - Click "Add Depot" → fill form → Submit → depot appears in table
# - Click pencil icon → form pre-fills → change city → Update → change shows in table
# - Toggle active switch → row reflects change

# Drivers screen (same pattern, also tests depot dropdown)
# Vehicles screen (same pattern, tests refrigerated toggle)

# Orders screen
# - Shows orders for today's date by default
# - Change date filter → orders change
# - Change status filter → orders filter
# - Click "Add Order" → fill address + date → create → appears in table
# - Click pencil → edit priority → update → shows new priority badge
```

---

**Document Status:** Not Started
**Last Updated:** 2026-03-29
