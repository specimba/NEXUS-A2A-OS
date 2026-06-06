'use client'

import React from 'react'
import { AlertCircle, RefreshCw, Flag } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface TabErrorBoundaryProps {
  children: React.ReactNode
}

interface TabErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class TabErrorBoundary extends React.Component<TabErrorBoundaryProps, TabErrorBoundaryState> {
  constructor(props: TabErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): TabErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[TabErrorBoundary] Caught error:', error, errorInfo)
  }

  resetErrorBoundary = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError && this.state.error) {
      return (
        <div className="flex items-center justify-center min-h-[300px] p-6">
          <div className="max-w-md w-full rounded-xl border border-red-500/30 bg-gradient-to-br from-red-950/40 via-card to-card p-6 shadow-2xl">
            {/* Error icon */}
            <div className="flex items-center justify-center w-14 h-14 rounded-full bg-red-500/15 border border-red-500/25 mx-auto mb-4">
              <AlertCircle className="h-7 w-7 text-red-500 dark:text-red-400" />
            </div>

            {/* Title */}
            <h3 className="text-center text-lg font-semibold text-red-600 dark:text-red-400 mb-2">
              Tab Error
            </h3>

            {/* Subtitle */}
            <p className="text-center text-sm text-muted-foreground mb-4">
              This tab encountered an unexpected error and couldn&apos;t render.
            </p>

            {/* Error message in code block */}
            <div className="rounded-lg bg-black/40 dark:bg-black/60 border border-border/50 p-3 mb-5 overflow-x-auto">
              <code className="text-xs font-mono text-red-400 dark:text-red-300 break-all whitespace-pre-wrap">
                {this.state.error.message || 'An unknown error occurred'}
              </code>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3">
              <Button
                onClick={this.resetErrorBoundary}
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white dark:bg-emerald-700 dark:hover:bg-emerald-600 gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Reload Tab
              </Button>
              <Button
                variant="outline"
                className="flex-1 border-border/50 hover:bg-muted/50 gap-2"
                onClick={() => {
                  // No-op — just for show
                }}
              >
                <Flag className="h-4 w-4" />
                Report Issue
              </Button>
            </div>

            {/* Stack trace hint */}
            {this.state.error.stack && (
              <details className="mt-4">
                <summary className="text-[10px] text-muted-foreground/60 cursor-pointer hover:text-muted-foreground transition-colors">
                  Stack trace
                </summary>
                <pre className="mt-2 text-[9px] font-mono text-muted-foreground/50 overflow-x-auto max-h-32 overflow-y-auto custom-scrollbar whitespace-pre-wrap">
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
