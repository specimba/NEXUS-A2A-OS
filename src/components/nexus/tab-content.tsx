'use client'

import { lazy, Suspense, type ComponentType } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNexusStore } from '@/store/nexus-store'
import { OverviewTab } from '@/components/nexus/tabs/overview-tab'

// Lazy-load all tab components to reduce initial bundle size and memory usage
const ArchitectureTab = lazy(() => import('@/components/nexus/tabs/architecture-tab').then(m => ({ default: m.ArchitectureTab })))
const StressLabTab = lazy(() => import('@/components/nexus/tabs/stresslab-tab').then(m => ({ default: m.StressLabTab })))
const GmrTab = lazy(() => import('@/components/nexus/tabs/gmr-tab').then(m => ({ default: m.GmrTab })))
const ProviderTab = lazy(() => import('@/components/nexus/tabs/provider-tab').then(m => ({ default: m.ProviderTab })))
const GovernorTab = lazy(() => import('@/components/nexus/tabs/governor-tab').then(m => ({ default: m.GovernorTab })))
const VaultTab = lazy(() => import('@/components/nexus/tabs/vault-tab').then(m => ({ default: m.VaultTab })))
const ResearchTab = lazy(() => import('@/components/nexus/tabs/research-tab').then(m => ({ default: m.ResearchTab })))
const AiChatTab = lazy(() => import('@/components/nexus/tabs/ai-chat-tab').then(m => ({ default: m.AiChatTab })))
const SwarmTab = lazy(() => import('@/components/nexus/tabs/swarm-tab').then(m => ({ default: m.SwarmTab })))
const TokensTab = lazy(() => import('@/components/nexus/tabs/tokens-tab').then(m => ({ default: m.TokensTab })))
const RateLimitTab = lazy(() => import('@/components/nexus/tabs/rate-limit-tab').then(m => ({ default: m.RateLimitTab })))
const KpiTab = lazy(() => import('@/components/nexus/tabs/kpi-tab').then(m => ({ default: m.KpiTab })))
const ModelRelayTab = lazy(() => import('@/components/nexus/tabs/modelrelay-tab').then(m => ({ default: m.ModelRelayTab })))
const DashboardsTab = lazy(() => import('@/components/nexus/tabs/dashboards-tab').then(m => ({ default: m.DashboardsTab })))
const TasksTab = lazy(() => import('@/components/nexus/tabs/tasks-tab').then(m => ({ default: m.TasksTab })))

const tabComponents: Record<string, ComponentType> = {
  overview: OverviewTab, // Keep overview as eager import (default tab)
  architecture: ArchitectureTab,
  stresslab: StressLabTab,
  gmr: GmrTab,
  providers: ProviderTab,
  governor: GovernorTab,
  vault: VaultTab,
  research: ResearchTab,
  aichat: AiChatTab,
  swarm: SwarmTab,
  tokens: TokensTab,
  ratelimit: RateLimitTab,
  kpi: KpiTab,
  dashboards: DashboardsTab,
  modelrelay: ModelRelayTab,
  tasks: TasksTab,
}

function TabLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    </div>
  )
}

export function TabContent() {
  const { activeTab } = useNexusStore()
  const Component = tabComponents[activeTab] || OverviewTab

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -4 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
      >
        <Suspense fallback={<TabLoader />}>
          <Component />
        </Suspense>
      </motion.div>
    </AnimatePresence>
  )
}
