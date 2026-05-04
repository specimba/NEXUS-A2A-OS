'use client'

import dynamic from 'next/dynamic'
import { useNexusStore } from '@/store/nexus-store'
import { motion, AnimatePresence } from 'framer-motion'

function TabLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
        <span className="text-sm text-muted-foreground">Loading tab...</span>
      </div>
    </div>
  )
}

const OverviewTab = dynamic(() => import('./tabs/overview-tab').then(m => ({ default: m.OverviewTab })), { ssr: false, loading: () => <TabLoader /> })
const StressLabTab = dynamic(() => import('./tabs/stresslab-tab').then(m => ({ default: m.StressLabTab })), { ssr: false, loading: () => <TabLoader /> })
const GmrTab = dynamic(() => import('./tabs/gmr-tab').then(m => ({ default: m.GmrTab })), { ssr: false, loading: () => <TabLoader /> })
const ProviderTab = dynamic(() => import('./tabs/provider-tab').then(m => ({ default: m.ProviderTab })), { ssr: false, loading: () => <TabLoader /> })
const GovernorTab = dynamic(() => import('./tabs/governor-tab').then(m => ({ default: m.GovernorTab })), { ssr: false, loading: () => <TabLoader /> })
const VaultTab = dynamic(() => import('./tabs/vault-tab').then(m => ({ default: m.VaultTab })), { ssr: false, loading: () => <TabLoader /> })
const ResearchTab = dynamic(() => import('./tabs/research-tab').then(m => ({ default: m.ResearchTab })), { ssr: false, loading: () => <TabLoader /> })
const SwarmTab = dynamic(() => import('./tabs/swarm-tab').then(m => ({ default: m.SwarmTab })), { ssr: false, loading: () => <TabLoader /> })
const TokensTab = dynamic(() => import('./tabs/tokens-tab').then(m => ({ default: m.TokensTab })), { ssr: false, loading: () => <TabLoader /> })
const RateLimitTab = dynamic(() => import('./tabs/rate-limit-tab').then(m => ({ default: m.RateLimitTab })), { ssr: false, loading: () => <TabLoader /> })
const KpiTab = dynamic(() => import('./tabs/kpi-tab').then(m => ({ default: m.KpiTab })), { ssr: false, loading: () => <TabLoader /> })

const tabComponents: Record<string, React.ComponentType> = {
  overview: OverviewTab,
  stresslab: StressLabTab,
  gmr: GmrTab,
  providers: ProviderTab,
  governor: GovernorTab,
  vault: VaultTab,
  research: ResearchTab,
  swarm: SwarmTab,
  tokens: TokensTab,
  ratelimit: RateLimitTab,
  kpi: KpiTab,
}

// Stagger container variants — children will animate in with delay
export const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.05,
    },
  },
  exit: {
    opacity: 0,
    transition: {
      staggerChildren: 0.03,
      staggerDirection: -1,
    },
  },
}

export const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: [0.25, 0.46, 0.45, 0.94] as [number, number, number, number],
    },
  },
  exit: {
    opacity: 0,
    y: -6,
    transition: {
      duration: 0.15,
    },
  },
}

export function TabContent() {
  const { activeTab } = useNexusStore()
  const Component = tabComponents[activeTab] || OverviewTab

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 8, scale: 0.995 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -4, scale: 0.998 }}
        transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="flex-1 overflow-auto"
      >
        <Component />
      </motion.div>
    </AnimatePresence>
  )
}
