'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { useNexusStore } from '@/store/nexus-store'
import { NexusSidebar } from '@/components/nexus/sidebar'
import { NexusHeader } from '@/components/nexus/header'
import { NexusFooter } from '@/components/nexus/footer'
import { TabContent } from '@/components/nexus/tab-content'
import { NexusAssistant } from '@/components/nexus/ai-assistant'
import { CommandPalette } from '@/components/nexus/command-palette'

export function NexusDashboard() {
  const { activeTab } = useNexusStore()

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar (desktop: inline, mobile: sheet) */}
      <NexusSidebar />

      {/* Main Area */}
      <div className="flex flex-1 flex-col min-w-0">
        <NexusHeader />

        {/* Content with animated grid background */}
        <main className="relative flex-1 overflow-y-auto overflow-x-hidden bg-background">
          {/* Subtle grid/particle background */}
          <div className="pointer-events-none absolute inset-0 grid-pattern-animated opacity-40" />

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="relative z-10 p-4 md:p-6"
            >
              <TabContent />
            </motion.div>
          </AnimatePresence>
        </main>

        {/* Sticky Footer */}
        <NexusFooter />
      </div>

      {/* Floating AI Assistant (bottom-right) */}
      <NexusAssistant />

      {/* Command Palette (Cmd+K) */}
      <CommandPalette />
    </div>
  )
}
