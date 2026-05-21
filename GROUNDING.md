# NEXUS-OS v3.1 — UI/UX Grounding Document

> **PURPOSE**: This document is the ground truth for the NEXUS-OS v3.1 dashboard UI/UX.
> If the UI is ever broken by an unwanted rollback, bad merge, or other disaster,
> refer back to this document and the git tag `grounding-uiux-v3.1` to restore the known-good state.
>
> **Git Tag**: `grounding-uiux-v3.1`
> **Date**: 2026-04-18
> **Commit**: See `git log --oneline -1` at tag

---

## 1. Architecture Overview

### Tech Stack
- **Framework**: Next.js 16 (App Router) + React 19
- **Styling**: Tailwind CSS 4 + CSS custom properties (oklch color space)
- **UI Library**: shadcn/ui (Radix primitives + CVA)
- **State**: Zustand (`nexus-store.ts`)
- **Data Fetching**: SWR for real-time polling
- **Animation**: Framer Motion
- **Theme**: next-themes (class-based dark/light)
- **Icons**: Lucide React
- **Fonts**: Geist Sans + Geist Mono (via next/font/google)
- **Build**: Bun runtime, Turbopack dev server

### Entry Point
```
src/app/page.tsx → Home() component
  └─ src/app/layout.tsx → RootLayout (ThemeProvider, PostHog, Toaster, fonts)
```

### Page Layout Structure
```tsx
<div className="flex h-screen overflow-hidden">
  <NexusSidebar />                    {/* Left sidebar (collapsible) */}
  <div className="flex flex-1 flex-col min-w-0">
    <NexusHeader />                   {/* Top bar */}
    <main className="flex-1 overflow-auto bg-background">
      <TabErrorBoundary>
        <TabContent />                {/* Active tab content */}
      </TabErrorBoundary>
    </main>
    <NexusFooter />                   {/* Bottom status bar */}
  </div>
  <NexusAssistant />                  {/* AI Chat (floating + slide panel) */}
  <NexusCommandPalette />             {/* Cmd+K overlay */}
  <QuickStatsWidget />                {/* Floating stats (desktop) */}
  <KeyboardShortcuts />               {/* ? key overlay */}
</div>
```

---

## 2. Color Scheme

### CSS Custom Properties (oklch)

All colors defined in `src/app/globals.css` using oklch color space:

#### Dark Theme (default, `.dark` class — same values as `:root`)
```css
--background:   oklch(0.07 0.012 285);     /* Near-black with purple tint */
--foreground:   oklch(0.92 0.02 285);      /* Near-white */
--card:         oklch(0.10 0.015 285);      /* Slightly lighter than bg */
--card-foreground: oklch(0.92 0.02 285);
--primary:      oklch(0.55 0.25 285);      /* Purple primary */
--primary-foreground: oklch(0.98 0.005 285);
--secondary:    oklch(0.18 0.02 285);
--muted:        oklch(0.15 0.015 285);      /* Subtle surfaces */
--muted-foreground: oklch(0.55 0.03 285);
--accent:       oklch(0.20 0.03 285);
--destructive:  oklch(0.60 0.25 30);       /* Red */
--border:       oklch(1 0 0 / 10%);        /* 10% white */
--input:        oklch(1 0 0 / 14%);        /* 14% white */
--ring:         oklch(0.55 0.25 285);
```

#### NEXUS Custom Colors (emerald-based)
```css
--nexus:        oklch(0.55 0.25 285);
--nexus-foreground: oklch(0.98 0.005 285);
--nexus-dim:    oklch(0.30 0.10 285);
--nexus-glow:   oklch(0.65 0.28 285);
```

#### Accent Color System
- **Emerald** (primary accent): `oklch(0.65 0.2 155)` — used for status, glows, badges, active states
- **Purple** (secondary accent): `oklch(0.55 0.25 285)` — used for primary buttons, charts, branding
- **Red** (destructive): `oklch(0.577 0.245 27.325)` — errors, CRIT, denied
- **Yellow/Orange** (warning): `oklch(0.828 0.189 84.429)` — degraded, caution
- **Blue** (info): `oklch(0.6094 0.1262 257.42)` — info, mid pool

### Tailwind Usage Pattern
Colors reference CSS variables via `hsl(var(--xxx))` in `tailwind.config.ts`.
Most component styling uses Tailwind utilities like:
- `text-emerald-600 dark:text-emerald-400` — semantic accent
- `bg-card`, `text-foreground` — theme-aware
- `border-border/60` — 60% opacity borders
- `bg-gradient-to-br from-emerald-500 to-emerald-700` — gradient accents

---

## 3. Component File Structure

### Shell Components
| File | Component | Role |
|------|-----------|------|
| `src/app/page.tsx` | `Home` | Root page, assembles all shell components |
| `src/components/nexus/dashboard-shell.tsx` | `NexusDashboard` | Alternative shell with animated grid bg |
| `src/components/nexus/sidebar.tsx` | `NexusSidebar` | Collapsible sidebar (desktop) / Sheet (mobile) |
| `src/components/nexus/header.tsx` | `NexusHeader` | Top bar with tab title, actions, config dialog |
| `src/components/nexus/footer.tsx` | `NexusFooter` | Status bar with pool status, errors, rate limits, uptime |
| `src/components/nexus/tab-content.tsx` | `TabContent` | Tab router with AnimatePresence transitions |

### Tab Components (`src/components/nexus/tabs/`)
| File | Tab ID | Label | Key Features |
|------|--------|-------|-------------|
| `overview-tab.tsx` | `overview` | Overview | System pillars, agent status, token budget, health timeline, diagnostics |
| `stresslab-tab.tsx` | `stresslab` | StressLab | ISC test runner, collapse analysis, templates |
| `gmr-tab.tsx` | `gmr` | GMR Router | Model routing pools (PREMIUM/MID/FAST), failover status |
| `governor-tab.tsx` | `governor` | Governor | Trust scores, constitutional rules, decision log |
| `vault-tab.tsx` | `vault` | Vault | Memory tracks, trust store, encrypted entries |
| `research-tab.tsx` | `research` | Research | Paper pipeline, vetting, auto-analysis |
| `swarm-tab.tsx` | `swarm` | Swarm | Agent monitor, auction, foreman, workers |
| `tokens-tab.tsx` | `tokens` | Token Budget | Session budget, burn rate, usage logs |
| `rate-limit-tab.tsx` | `ratelimit` | Rate Limits | Per-provider rate limit status, circuit breaker |
| `kpi-tab.tsx` | `kpi` | KPI Dashboard | Key performance indicators |
| `dashboards-tab.tsx` | `dashboards` | My Dashboards | Custom dashboards, widget builder |
| `mcp-hub-tab.tsx` | `mcp` | MCP Hub | Model Context Protocol connections |
| `config-tab.tsx` | `config` | Config | System configuration editor |

### Feature Components
| File | Component | Role |
|------|-----------|------|
| `ai-assistant.tsx` | `NexusAssistant` | Floating chat button + slide-in panel with SSE streaming |
| `command-palette.tsx` | `NexusCommandPalette` | Cmd+K search/action palette |
| `notification-center.tsx` | `NotificationCenter` | Bell icon + dropdown with notifications |
| `quick-stats-widget.tsx` | `QuickStatsWidget` | Floating desktop stats |
| `keyboard-shortcuts.tsx` | `KeyboardShortcuts` | ? key shortcuts reference |
| `global-export-dialog.tsx` | `GlobalExportDialog` | Export dashboard data |
| `system-logs.tsx` | `SystemLogsPanel` | Ctrl+L system logs viewer |
| `tab-error-boundary.tsx` | `TabErrorBoundary` | Catches tab render errors |
| `live-ticker.tsx` | `LiveTicker` | Scrolling ticker |
| `data-source-badge.tsx` | `DataSourceBadge` | DB vs simulated indicator |

### MCP Sub-components (`src/components/nexus/mcp/`)
- `connections-panel.tsx`
- `analytics-panel.tsx`
- `event-stream-panel.tsx`
- `settings-panel.tsx`

### Custom Dashboards Sub-components (`src/components/nexus/dashboards/`)
- `dashboard-list.tsx`, `dashboard-editor.tsx`, `widget.tsx`, `widget-renderer.tsx`
- `widget-library.tsx`, `widget-catalog.ts`, `widget-config-modal.tsx`
- `ai-builder.tsx`, `share-dialog.tsx`, `presence-indicator.tsx`, `types.ts`

### shadcn/ui Primitives (`src/components/ui/`)
Full set of 40+ Radix-based components: `card.tsx`, `badge.tsx`, `button.tsx`, `dialog.tsx`,
`dropdown-menu.tsx`, `tooltip.tsx`, `tabs.tsx`, `input.tsx`, `select.tsx`, `sheet.tsx`,
`progress.tsx`, `switch.tsx`, `separator.tsx`, `command.tsx`, `scroll-area.tsx`, etc.

---

## 4. Sidebar Design

### Navigation Items (13 tabs)
```typescript
const navItems = [
  { id: 'overview',     label: 'Overview',       icon: LayoutDashboard },
  { id: 'stresslab',    label: 'StressLab',      icon: FlaskConical,   badge: 'ISC' },
  { id: 'gmr',          label: 'GMR Router',     icon: Router },
  { id: 'governor',     label: 'Governor',        icon: Shield },
  { id: 'vault',        label: 'Vault',           icon: Database },
  { id: 'research',     label: 'Research',        icon: BookOpen,       badge: '20' },
  { id: 'swarm',        label: 'Swarm',           icon: Bug },
  { id: 'tokens',       label: 'Token Budget',    icon: Coins },
  { id: 'ratelimit',    label: 'Rate Limits',     icon: Gauge },
  { id: 'kpi',          label: 'KPI Dashboard',   icon: Target },
  { id: 'dashboards',   label: 'My Dashboards',   icon: LayoutGrid },
  { id: 'mcp',          label: 'MCP Hub',         icon: Network,        badge: 'NEW' },
  { id: 'config',       label: 'Config',          icon: FileCode2 },
]
```

### Sidebar Styles
- **Desktop**: `w-56` (expanded) / `w-16` (collapsed), `bg-card/80 backdrop-blur-sm`
- **Mobile**: Sheet component, `w-64`
- **Active tab indicator**: `bg-gradient-to-r from-emerald-600/20 to-emerald-600/5` with left border `bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]`
- **Logo**: Gradient emerald icon + "NEXUS OS" + "v3.1 — Intelligence Dashboard"
- **Status**: Animated ping dot + "System Operational"
- **Keyboard shortcuts**: Number keys (1-13) shown inline

---

## 5. Header Design

### Key Elements (left to right)
1. **Mobile menu trigger** (md:hidden)
2. **Tab title** — dynamic from `tabTitles` map
3. **Token budget indicator** — emerald gradient badge showing "73,450 / 100,000"
4. **Active agents badge** — "3 agents" with green dot
5. **Notification center** — bell icon with unread count
6. **Export button** — download icon
7. **System Logs** — terminal icon (Ctrl+L shortcut)
8. **Clock** — monospace `HH:MM:SS`
9. **System Config** — gear icon (opens dialog)
10. **Theme toggle** — sun/moon animation

### Header Style
- `h-14`, `bg-card/80 backdrop-blur-sm`, `border-b border-border/60`
- Gradient bottom border: `from-transparent via-emerald-600/30 to-transparent`

### System Config Dialog
- Constitution limits (maxAgents, apiCallsLimit, fileWritesLimit, maxConcurrent)
- GMR settings (healthCheckInterval, fallbackEnabled)
- Governor settings (autoBlockCrit, trustDecayRate, sensitivity)
- Save button: `bg-emerald-600 hover:bg-emerald-700 text-white`

---

## 6. Footer Design

### Three Sections
1. **Left**: "NEXUS OS v3.1 — Cloud Intelligence Dashboard | Constitution: 5 agents/hr · 20 API/session · 2 concurrent · 30 writes"
2. **Center** (md+): Model pool status (PREMIUM/MID/FAST with colored dots), Error count (5m), Rate limit status
3. **Right**: Session uptime, Live indicator (animated pulse), "Powered by z-ai"

### Pool Colors
- PREMIUM: `#34d399` (emerald)
- MID: `#60a5fa` (blue)
- FAST: `#fb923c` (orange)

### Footer Style
- `bg-card`, `border-t border-border`, gradient top border emerald
- `text-[11px]` throughout

---

## 7. AI Assistant Design

### Floating Button
- Fixed bottom-right, `h-14 w-14`, gradient emerald circle
- `shadow-lg shadow-emerald-500/30`
- Spring animation on mount/hover/tap
- Unread badge with ping animation

### Chat Panel
- Slide-in from right: `w-full sm:w-[420px]`, `bg-card/95 backdrop-blur-xl`
- Header: Logo + "NEXUS AI" + online status + model selector + clear + close
- Messages: User (emerald gradient) / Assistant (muted bg)
- Streaming: Blinking cursor, SSE parser for real-time tokens
- Model options: NEXUS AI (GLM-4.7), Llama 3.3 70B, DeepSeek R1, Llama 3.1 8B
- Quick prompts: System Status, StressLab Results, Show Trust Scores, etc.
- Chat history persisted in localStorage (key: `nexus-chat-history`, max 50 messages)
- Auto-scroll management with scroll-to-bottom button

---

## 8. State Management (Zustand)

### Store: `src/store/nexus-store.ts`
```typescript
type NexusTab = 'overview' | 'stresslab' | 'gmr' | 'governor' | 'vault' | 'research'
  | 'swarm' | 'tokens' | 'ratelimit' | 'kpi' | 'dashboards' | 'mcp' | 'config'

interface NexusState {
  activeTab: NexusTab           // Default: 'overview'
  sidebarOpen: boolean          // Default: true
  isChatOpen: boolean           // Default: false
  chatMessages: ChatMessage[]   // Persisted in localStorage
  notifications: Notification[] // Pre-seeded with 10 notifications
  isNotificationCenterOpen: boolean
  isExportDialogOpen: boolean
  // Daily Practice Timer
  timerStartedAt: number | null
  timerIsRunning: boolean
  timerDuration: number         // 1920 seconds (32 min)
  timerElapsedOnPause: number
}
```

---

## 9. Key Design Patterns & Code Snippets

### Card Style (glass morphism)
```tsx
<div className="rounded-xl border border-white/5 bg-gradient-to-br from-white/[0.04] to-transparent p-4 
  transition-all hover:border-purple-500/20 hover:from-purple-500/[0.06]">
```

### Active Sidebar Item
```tsx
<button className={cn(
  'relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all',
  isActive
    ? 'bg-gradient-to-r from-emerald-600/20 to-emerald-600/5 text-emerald-600 dark:text-emerald-400 shadow-sm shadow-emerald-600/10'
    : 'text-muted-foreground hover:bg-accent/70 hover:text-accent-foreground'
)}>
  {isActive && (
    <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-r bg-emerald-400 
      shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
  )}
</button>
```

### Badge Styles
```tsx
// Emerald badge
<Badge variant="secondary" className="h-4 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 
  dark:text-emerald-400 border-0">

// LIVE badge
<Badge variant="outline" className="text-[9px] border-purple-500/20 text-purple-300">LIVE</Badge>

// Decision badge
<Badge variant="outline" className={cn('text-[10px] font-mono border',
  action === 'ALLOW' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20' :
  action === 'DENY' ? 'bg-red-500/15 text-red-400 border-red-500/20' :
  'bg-yellow-500/15 text-yellow-400 border-yellow-500/20'
)}>
```

### Status Dot Pattern
```tsx
function statusDot(status: string): string {
  switch (status) {
    case 'operational': return 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]'
    case 'degraded':    return 'bg-yellow-400 shadow-[0_0_6px_rgba(250,204,21,0.5)]'
    default:            return 'bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.5)]'
  }
}
```

### Health Progress Bar
```tsx
<div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-white/5">
  <div className={cn(
    'h-full rounded-full transition-all duration-500',
    health >= 95 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' :
    health >= 80 ? 'bg-gradient-to-r from-yellow-500 to-yellow-400' :
    'bg-gradient-to-r from-red-500 to-red-400'
  )} style={{ width: `${health}%` }} />
</div>
```

### Animated Ping Dot
```tsx
<span className="relative flex h-2.5 w-2.5">
  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
</span>
```

---

## 10. CSS Animations & Effects (globals.css)

### Key Custom Classes
| Class | Purpose |
|-------|---------|
| `.gradient-text` | Emerald gradient text effect |
| `.glass-card` | Glass morphism card (backdrop-blur, inner shadow) |
| `.nexus-glow-effect` | Pulsing emerald glow on element |
| `.hover-lift` | translateY(-2px) + scale(1.01) + border glow on hover |
| `.shimmer` / `.shimmer-skeleton` | Loading shimmer animation |
| `.pulse-border` | Pulsing border color animation |
| `.grid-pattern-animated` | Drifting dot grid background |
| `.nexus-gradient-border` | Animated gradient border (mask trick) |
| `.status-pulse-green` | Pulsing green status indicator |
| `.status-glow-green/red/yellow/purple/blue/orange` | Status glow effects |
| `.live-badge-glow` | Pulsing glow for LIVE badge |
| `.badge-glow-emerald/red` | Badge glow effects |
| `.hover-glow` | Emerald glow on hover |
| `.custom-scrollbar` | Thin 4px scrollbar |
| `.cid-card` | AWS CID-inspired clean card |
| `.section-divider` | Gradient horizontal divider |
| `.data-fresh` | Fresh data indicator with pulse dot |
| `.kpi-value` | Large bold tabular number |
| `.budget-alert-pulse` / `.budget-over-pulse` | Budget warning animations |
| `.token-flow-bar` | Animated token consumption bar |
| `.vap-chain-line` | Flowing dash animation for VAP chains |
| `.throughput-animated` | Sweeping highlight bar |
| `.ripple-effect` | Button click ripple |
| `.btn-press` | Scale-down on active press |
| `.skeleton-pulse` / `.skeleton-pulse-text` | Loading placeholders |
| `.animate-fade-in` / `.animate-slide-up` / `.animate-scale-in` | Entrance animations |
| `.focus-ring-enhanced` | Accessibility focus ring |
| `.log-entry-real` / `.log-entry-simulated` | Log entry source indicators |
| `.pipeline-step-animate` | Pipeline progress animation |
| `.relevance-bar-animate` | Relevance bar fill animation |
| `.priority-p0-glow` / `.priority-p1-glow` | Priority tier glow effects |
| `.chart-glow-emerald` | Chart drop shadow glow |

---

## 11. API Routes

### Key endpoints (`src/app/api/`)
| Route | Purpose |
|-------|---------|
| `/api/system` | System overview (pillars, stats, decisions, health timeline) |
| `/api/agents` | Agent list with status/trust |
| `/api/models` | Model pool status |
| `/api/chat` | AI chat (SSE streaming + JSON fallback) |
| `/api/ai-bridge` | Cerebras/OpenRouter bridge |
| `/api/claude` | Claude proxy |
| `/api/stresslab` | StressLab test data |
| `/api/governor` | Governor decisions |
| `/api/vault` | Vault entries |
| `/api/research` | Research pipeline |
| `/api/swarm` | Swarm status |
| `/api/tokens` | Token budget |
| `/api/rate-limit` | Rate limit status |
| `/api/dashboards` | Custom dashboards CRUD |
| `/api/mcp/connections` | MCP Hub connections |
| `/api/metrics` | System metrics |
| `/api/notifications` | Notifications |
| `/api/settings` | Settings |
| `/api/config` | System config |

---

## 12. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `1`-`9`, `0`, `-`, `=` | Switch sidebar tabs by position |
| `Cmd+K` / `Ctrl+K` | Open command palette |
| `?` | Toggle keyboard shortcuts panel |
| `Ctrl+L` | Toggle system logs |
| `Ctrl+E` | Open export dialog |

---

## 13. Responsive Design

- **Mobile** (<768px): Sidebar becomes Sheet (overlay), header shows menu button, footer hides center section
- **Tablet** (768-1024px): Full sidebar, some header elements hidden
- **Desktop** (>1024px): Full experience with floating widgets

### Key Breakpoints
- `sm:` — 640px
- `md:` — 768px (sidebar switches from Sheet to inline)
- `lg:` — 1024px (full header elements visible)

---

## 14. Recovery Instructions

If the UI is broken:

1. **Check git tag**: `git checkout grounding-uiux-v3.1`
2. **Compare current state**: `git diff grounding-uiux-v3.1 -- src/components/nexus/ src/app/page.tsx src/app/globals.css`
3. **Restore specific files**: `git checkout grounding-uiux-v3.1 -- <file>`
4. **Run backup restore**: `bash scripts/backup-ui-snapshot.sh` (creates timestamped tar.gz)
5. **Reference this document** for correct color values, component structure, and layout patterns

---

## 15. Dependencies (key versions)

```json
{
  "next": "^16.1.1",
  "react": "^19.0.0",
  "zustand": "^5.0.6",
  "framer-motion": "^12.23.2",
  "lucide-react": "^0.525.0",
  "next-themes": "^0.4.6",
  "swr": "^2.4.1",
  "recharts": "^2.15.4",
  "sonner": "^2.0.6",
  "tailwindcss": "^4",
  "z-ai-web-dev-sdk": "^0.0.17"
}
```

---

*Document generated as part of NEXUS-OS v3.1 UI/UX grounding point. Do not modify this document without updating the git tag.*
