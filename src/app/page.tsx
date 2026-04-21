'use client'

import { NexusSidebar } from '@/components/nexus/sidebar'
import { NexusHeader } from '@/components/nexus/header'
import { NexusFooter } from '@/components/nexus/footer'
import { TabContent } from '@/components/nexus/tab-content'
import { NexusAssistant } from '@/components/nexus/ai-assistant'
import { NexusCommandPalette } from '@/components/nexus/command-palette'
import { QuickStatsWidget } from '@/components/nexus/quick-stats-widget'
import { KeyboardShortcuts } from '@/components/nexus/keyboard-shortcuts'
import { useState, useEffect } from 'react'

export default function Home() {
  const [shortcutsOpen, setShortcutsOpen] = useState(false)

  // ? key to open keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = e.target as HTMLElement
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return
        e.preventDefault()
        setShortcutsOpen(prev => !prev)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

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

      {/* Keyboard Shortcuts Panel (triggered by ? key) */}
      <KeyboardShortcuts open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  )
}
