'use client'

import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('[NEXUS-OS Global Error]', error)
  }, [error])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <div className="max-w-lg w-full rounded-2xl border border-red-500/30 bg-gradient-to-br from-red-950/40 via-card to-card p-8 shadow-2xl">
        {/* NEXUS-OS branding */}
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-600/20 border border-emerald-600/30">
            <span className="text-emerald-500 font-bold text-sm">N</span>
          </div>
          <span className="text-sm font-semibold tracking-wider text-emerald-600 dark:text-emerald-400 uppercase">
            NEXUS-OS v3.1
          </span>
        </div>

        {/* Error icon */}
        <div className="flex items-center justify-center w-20 h-20 rounded-full bg-red-500/15 border border-red-500/25 mx-auto mb-6">
          <AlertCircle className="h-10 w-10 text-red-500 dark:text-red-400" />
        </div>

        {/* Title */}
        <h1 className="text-center text-2xl font-bold text-foreground mb-2">
          Something went wrong
        </h1>

        {/* Subtitle */}
        <p className="text-center text-sm text-muted-foreground mb-6">
          The NEXUS-OS dashboard encountered an unexpected error. You can try again or check the console for details.
        </p>

        {/* Error message */}
        <div className="rounded-lg bg-black/40 dark:bg-black/60 border border-border/50 p-4 mb-6 overflow-x-auto">
          <code className="text-xs font-mono text-red-400 dark:text-red-300 break-all whitespace-pre-wrap">
            {error.message || 'An unknown error occurred'}
          </code>
          {error.digest && (
            <p className="mt-2 text-[10px] font-mono text-muted-foreground/50">
              Error digest: {error.digest}
            </p>
          )}
        </div>

        {/* Action button */}
        <div className="flex justify-center">
          <Button
            onClick={reset}
            className="bg-emerald-600 hover:bg-emerald-700 text-white dark:bg-emerald-700 dark:hover:bg-emerald-600 gap-2 px-8"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
        </div>

        {/* Footer text */}
        <p className="text-center text-[10px] text-muted-foreground/40 mt-6">
          If this issue persists, please contact the NEXUS-OS system administrator.
        </p>
      </div>
    </div>
  )
}
