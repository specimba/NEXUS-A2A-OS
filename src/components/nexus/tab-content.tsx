'use client'

import { type ComponentType } from 'react'
import { useNexusStore } from '@/store/nexus-store'
import { OverviewTab } from '@/components/nexus/tabs/overview-tab'
import { StressLabTab } from '@/components/nexus/tabs/stresslab-tab'
import { GmrTab } from '@/components/nexus/tabs/gmr-tab'
import { ProviderTab } from '@/components/nexus/tabs/provider-tab'
import { GovernorTab } from '@/components/nexus/tabs/governor-tab'
import { VaultTab } from '@/components/nexus/tabs/vault-tab'
import { ResearchTab } from '@/components/nexus/tabs/research-tab'
import { AiChatTab } from '@/components/nexus/tabs/ai-chat-tab'
import { SwarmTab } from '@/components/nexus/tabs/swarm-tab'
import { TokensTab } from '@/components/nexus/tabs/tokens-tab'
import { RateLimitTab } from '@/components/nexus/tabs/rate-limit-tab'
import { KpiTab } from '@/components/nexus/tabs/kpi-tab'

const tabComponents: Record<string, ComponentType> = {
  overview: OverviewTab,
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
}

export function TabContent() {
  const { activeTab } = useNexusStore()
  const Component = tabComponents[activeTab] || OverviewTab

  return (
    <div className="animate-in fade-in-0 duration-200 p-4 md:p-6">
      <Component />
    </div>
  )
}
