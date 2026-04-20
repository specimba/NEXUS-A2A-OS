'use client'

import { useNexusStore } from '@/store/nexus-store'
import { OverviewTab } from './tabs/overview-tab'
import { StressLabTab } from './tabs/stresslab-tab'
import { GmrTab } from './tabs/gmr-tab'
import { GovernorTab } from './tabs/governor-tab'
import { VaultTab } from './tabs/vault-tab'
import { ResearchTab } from './tabs/research-tab'
import { SwarmTab } from './tabs/swarm-tab'
import { TokensTab } from './tabs/tokens-tab'
import { motion, AnimatePresence } from 'framer-motion'

const tabComponents: Record<string, React.ComponentType> = {
  overview: OverviewTab,
  stresslab: StressLabTab,
  gmr: GmrTab,
  governor: GovernorTab,
  vault: VaultTab,
  research: ResearchTab,
  swarm: SwarmTab,
  tokens: TokensTab,
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
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.15 }}
        className="flex-1 overflow-auto"
      >
        <Component />
      </motion.div>
    </AnimatePresence>
  )
}
