'use client'

import dynamic from 'next/dynamic'
import { Shield, Loader2 } from 'lucide-react'

// Dynamically import the entire dashboard with ssr: false
// This prevents hydration mismatch and reduces SSR memory usage
const NexusDashboard = dynamic(
  () => import('@/components/nexus/dashboard-content').then(m => ({ default: m.NexusDashboard })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-14 w-14 rounded-xl bg-emerald-600/10 border border-emerald-600/30 flex items-center justify-center">
            <Shield className="h-7 w-7 text-emerald-600" />
          </div>
          <div className="text-center">
            <div className="text-lg font-bold gradient-text mb-1">NEXUS-OS</div>
            <div className="text-xs text-muted-foreground mb-3">v3.1 Command Center</div>
          </div>
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
            <span className="text-sm text-muted-foreground">Initializing systems...</span>
          </div>
          <div className="flex gap-1 mt-2">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" style={{ animationDelay: '0ms' }} />
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" style={{ animationDelay: '200ms' }} />
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" style={{ animationDelay: '400ms' }} />
          </div>
        </div>
      </div>
    ),
  }
)

export default function Page() {
  return <NexusDashboard />
}
