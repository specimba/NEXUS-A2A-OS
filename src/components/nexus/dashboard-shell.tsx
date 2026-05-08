'use client'

import dynamic from 'next/dynamic'
import { useState, useEffect } from 'react'
import { NexusSidebar } from '@/components/nexus/sidebar'
import { NexusHeader } from '@/components/nexus/header'
import { NexusFooter } from '@/components/nexus/footer'

// Dynamic imports for heavy components
const TabContent = dynamic(
  () => import('@/components/nexus/tab-content').then(m => ({ default: m.TabContent })),
  { ssr: false, loading: () => <TabLoader /> }
)
const NexusAssistant = dynamic(
  () => import('@/components/nexus/ai-assistant').then(m => ({ default: m.NexusAssistant })),
  { ssr: false }
)
const NexusCommandPalette = dynamic(
  () => import('@/components/nexus/command-palette').then(m => ({ default: m.NexusCommandPalette })),
  { ssr: false }
)
const QuickStatsWidget = dynamic(
  () => import('@/components/nexus/quick-stats-widget').then(m => ({ default: m.QuickStatsWidget })),
  { ssr: false }
)
const KeyboardShortcuts = dynamic(
  () => import('@/components/nexus/keyboard-shortcuts').then(m => ({ default: m.KeyboardShortcuts })),
  { ssr: false }
)

function TabLoader() {
  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
        <span className="text-sm text-muted-foreground">Loading tab...</span>
      </div>
    </div>
  )
}

export default function NexusDashboard() {
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

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

  if (!mounted) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
      </div>
    )
  }

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
