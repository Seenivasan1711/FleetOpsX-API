# FleetOpsX — UI/UX Design System

---

## 1. Color System (Phase 5 — DataGuard-inspired)

### Dark theme (default — pure black variant)

```css
--c-bg:         #0a0a0a;   /* near-pure black (DataGuard style) */
--c-surface:    #141414;   /* card backgrounds */
--c-elevated:   #1c1c1c;   /* dropdown, hover states */
--c-border:     #2a2a2a;   /* subtle borders */
--c-text:       #f0f0f0;   /* primary text */
--c-muted:      #6b7280;   /* secondary text, labels */

/* Accent — purple (matching DataGuard) */
--c-accent:     #7c3aed;
--c-accent-dim: rgba(124, 58, 237, 0.12);
--c-accent-glow: rgba(124, 58, 237, 0.28);

/* Semantic */
--c-green:  #10b981;  --c-green-dim:  rgba(16, 185, 129, 0.10);
--c-red:    #ef4444;  --c-red-dim:    rgba(239, 68, 68, 0.10);
--c-orange: #f59e0b;  --c-orange-dim: rgba(245, 158, 11, 0.10);
--c-blue:   #3b82f6;  --c-blue-dim:   rgba(59, 130, 246, 0.10);
```

> Existing midnight theme (`#060c1a`) becomes "Midnight Blue" variant.  
> New default becomes "Obsidian" (pure black, purple accent).

---

## 2. Chat AI — DataGuard-Style Design Spec

### Position and layout

```
Desktop: Bottom-right floating button (56px circle, purple)
         → Click → slide-over panel (420px wide, full height)
         → "Expand" button → full-page modal

Mobile:  Bottom-right fab → full-screen slide-up
```

### Panel structure

```
┌─────────────────────────────────┐
│ [◉] FleetOpsX AI          [↺][×] │  ← header: status dot, reset, close
│ ● Reading 47 orders · 3 drivers  │  ← context status line
├─────────────────────────────────┤
│                                 │
│   Hi {name} — what would        │  ← entry state: personalised greeting
│   you like to know about        │
│   your fleet today?             │
│                                 │
│   SUGGESTED FOR YOU             │
│   ○ Why is Route 3 at risk?     │  ← suggested chips with icon
│   △ Show unassigned orders      │
│   → Compare today vs yesterday  │
│                                 │
│   ⊙ Type / for commands like    │  ← slash command hint
│     /plan, /explain, /status    │
├─────────────────────────────────┤
│ Ask about your fleet...   [📎][↑]│  ← input bar
│ [⎵] send · [⏎] new line · context: 47 orders │
└─────────────────────────────────┘
```

### Slash command autocomplete

```
Triggered when user types "/"
Appears as a card above the input:

┌─────────────────────────────────┐
│ <> COMMANDS MATCHING "/pl"      │
│ /plan      Generate today's AI plan     ↵ │
│ /planhistory  View past plans           ↵ │
└─────────────────────────────────┘

Available slash commands:
  /plan          → Trigger multi-scenario AI plan generation
  /reroute       → Reroute a specific driver
  /explain       → Explain the current plan reasoning
  /status        → Fleet status summary (orders, drivers, GPS)
  /forecast      → Tomorrow's volume forecast
  /compare       → Compare two plans or two time periods
  /export        → Export current plan to Excel
  /atRisk        → Show at-risk deliveries
```

### Response card types

**1. Summary card** (text response)
```
┌─ [◉] response ──────────────────┐
│ User message bubble (right-aligned, muted bg)
│
│ [FleetOpsX AI]
│ Your fleet has **3 at-risk deliveries** today.
│ Driver Ravi is 45 minutes behind schedule on
│ Route North-2, affecting 4 stops.
│
│ ┌────────────────────────────────┐
│ │ △ At-risk summary    CRITICAL  │
│ │ Driver: Ravi Kumar             │
│ │ Route: North-2 · 4 stops       │
│ │ Delay: ~45 min                 │
│ │ [View on map] [Reassign stops] │
│ └────────────────────────────────┘
│
│ ↳ Show Ravi's full route
│ ↳ Which stops can be reassigned?
│ ↳ Compare to yesterday
│
│ Based on 47 orders · 3 drivers active · 10:23 AM
└─────────────────────────────────┘
```

**2. Plan scenarios card** (`/plan`)
```
┌─ [◉] plan generated ────────────┐
│ I've generated 4 plan scenarios for today.
│ Select one to confirm:
│
│ ┌──────────┬──────────┬──────────┬──────────┐
│ │ FASTEST  │ECONOMICAL│ BALANCED │DRIVER_AV.│
│ │ 4h 12m   │ ₹ 1,820  │ 4h 45m   │ 98%      │
│ │ 47 orders│47 orders │47 orders │45 orders │
│ │ 6 routes │5 routes  │5 routes  │5 routes  │
│ │[Select →]│[Select →]│[Select →]│[Select →]│
│ └──────────┴──────────┴──────────┴──────────┘
│
│ ↳ Explain why Economical uses 5 routes
│ ↳ Apply natural language constraint
│ ↳ Compare Fastest vs Balanced
│
│ Based on 47 orders · 19 drivers available · today
└─────────────────────────────────┘
```

**3. Thinking state** (while AI is processing)
```
┌─ [◉] Thinking... ─── [□][×] ───┐
│ Show at-risk deliveries
│
│ [FleetOpsX AI]
│  ✓ Reading today's orders (47)
│  ✓ Checking GPS positions
│  ○ Analysing SLA windows...     ← current step, spinning
│  ○ ...
│
│  Generating response...      [○]
│  ● Streaming · 1.8s    Click stop to cancel
└─────────────────────────────────┘
```

---

## 3. Superadmin Tenant Selector Screen

```
┌──────────────────────────────────────────────────────┐
│                                                       │
│  F  FleetOpsX                          [Seenivasan ▾]│
│                                                       │
│  Select a tenant workspace                           │
│  ─────────────────────────────────────────────────── │
│  You are logged in as platform admin.                 │
│  Choose a tenant to work within, or manage the        │
│  platform below.                                      │
│                                                       │
│  [🔍 Search tenants...]                               │
│                                                       │
│  ┌─────────────────┐  ┌─────────────────┐             │
│  │ 🏢 Demo Corp     │  │ 🏢 Acme Logistics │            │
│  │ demo-corp        │  │ acme-logistics   │            │
│  │ 47 orders today  │  │ 12 orders today  │            │
│  │ 19 drivers       │  │ 8 drivers        │            │
│  │                  │  │                  │            │
│  │ [Act as tenant] [👁 Read-only]       │            │
│  └─────────────────┘  └─────────────────┘             │
│                                                       │
│  ─ Platform Management ──────────────────────────── │
│  [⚙ AI Providers] [👥 All Tenants] [📊 System Health]│
│                                                       │
└──────────────────────────────────────────────────────┘
```

### Superadmin banner (shown when acting as tenant)

```
┌──────────────────────────────────────────────────────┐
│ ⚡ SUPERADMIN MODE  │  Acting as: Demo Corp  │ [👁 Read-only ◉] │ [Exit Tenant →] │
└──────────────────────────────────────────────────────┘
```

- Yellow/amber background banner below the topbar
- Toggle read-only/full-access (full access = orange warning)
- Every mutating action shows: "Are you sure? You are acting as Demo Corp."

---

## 4. Typography Scale

```
Display:   32px · 800 · Plus Jakarta Sans
H1:        24px · 700
H2:        18px · 700
H3:        15px · 600
Body:      14px · 400
Small:     12px · 400
Micro:     11px · 500 (labels, badges)
Mono:      13px · JetBrains Mono (IDs, coords, code)
```

---

## 5. Component Standards

### Cards
```
background: var(--c-surface)
border: 1px solid var(--c-border)
border-radius: 12px (standard) | 16px (featured) | 20px (hero)
padding: 20px
```

### Response card (chat)
```
background: var(--c-elevated)
border: 1px solid var(--c-border)
border-left: 3px solid var(--c-accent)
border-radius: 12px
padding: 16px
```

### Badges / type pills
```
Severity: CRITICAL (red), WARNING (orange), INFO (blue), SUCCESS (green)
Plan type: FASTEST (blue), ECONOMICAL (green), BALANCED (purple), DRIVER_AV (orange)
Role: SUPERADMIN (amber), ADMIN (purple), DISPATCHER (blue), DRIVER (muted)
```

### Confirmation dialog (superadmin actions)
```
Title: "Confirm action as superadmin"
Body:  "You are about to [action] for tenant [Tenant Name]. This will affect live data."
CTA:   [Cancel] [Yes, proceed]
Style: Modal, red border accent on proceed button
```

---

## 6. Animation Tokens

```css
page-slide-in:   0.22s ease (translateY 10px → 0)
dropdown-in:     0.15s ease (translateY -6px → 0)
chat-slide-in:   0.25s cubic-bezier(0.4, 0, 0.2, 1) (translateX 100% → 0)
thinking-pulse:  0.8s ease infinite (opacity 0.4 → 1 → 0.4)
```
