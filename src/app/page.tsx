'use client'

import { NexusSidebar } from '@/components/nexus/sidebar'
import { NexusHeader } from '@/components/nexus/header'
import { NexusFooter } from '@/components/nexus/footer'
import { TabContent } from '@/components/nexus/tab-content'
import { NexusAssistant } from '@/components/nexus/ai-assistant'
import { NexusCommandPalette } from '@/components/nexus/command-palette'
import { QuickStatsWidget } from '@/components/nexus/quick-stats-widget'

export default function Home() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar (desktop: inline, mobile: sheet) */}
      <NexusSidebar />

      {/* Main Area */}
      <div className="flex flex-1 flex-col min-w-0">
        <NexusHeader />

        {/* Content */}
        <main className="flex-1 overflow-auto bg-background">
          <TabContent />
        </main>

        {/* Sticky Footer */}
        <NexusFooter />
      </div>

      {/* AI Assistant Chat Panel */}
      <NexusAssistant />

      {/* Command Palette (global overlay, triggered by Ctrl+K / Cmd+K) */}
      <NexusCommandPalette />

      {/* Quick Stats Floating Widget (desktop only) */}
      <QuickStatsWidget />
    </div>
  )
}
