'use client'

import dynamic from 'next/dynamic'
import { Suspense } from 'react'

// Load the entire dashboard dynamically — ssr: false prevents server-side rendering
// This minimizes memory footprint since the server only serves a lightweight HTML shell
const NexusDashboard = dynamic(
  () => import('@/components/nexus/dashboard-shell'),
  {
    ssr: false,
    loading: () => <DashboardBootScreen />,
  }
)

function DashboardBootScreen() {
  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-6">
        {/* Logo */}
        <div className="relative">
          <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-600/30">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="absolute -inset-4 rounded-3xl bg-emerald-500/10 animate-pulse" />
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">NEXUS OS</h1>
          <p className="text-sm text-muted-foreground mt-1">v3.1 — Intelligence Dashboard</p>
        </div>

        {/* Boot sequence animation */}
        <div className="space-y-2 w-64">
          <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>Initializing kernel...</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse [animation-delay:200ms]" />
            <span>Loading governance modules...</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground/60">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse [animation-delay:400ms]" />
            <span>Connecting agent swarm...</span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-48 h-1 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full animate-[loading_2s_ease-in-out_infinite]" />
        </div>
      </div>

      <style jsx>{`
        @keyframes loading {
          0% { width: 0%; }
          50% { width: 70%; }
          100% { width: 100%; }
        }
      `}</style>
    </div>
  )
}

export default function Home() {
  return (
    <Suspense fallback={<DashboardBootScreen />}>
      <NexusDashboard />
    </Suspense>
  )
}
