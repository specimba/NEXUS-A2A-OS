'use client'

import { Toaster as Sonner, type ToasterProps } from 'sonner'
import { useTheme } from 'next-themes'

/**
 * NEXUS-themed toast notification system.
 * Wraps Sonner with emerald accent styling and consistent branding.
 */
export function NexusToaster({ ...props }: ToasterProps) {
  const { theme = 'system' } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps['theme']}
      className="nexus-toaster group"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-card group-[.toaster]:text-card-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg group-[.toaster]:rounded-lg group-[.toaster]:pr-6',
          description: 'group-[.toast]:text-muted-foreground',
          actionButton:
            'bg-emerald-600 text-emerald-50 hover:bg-emerald-700 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
          cancelButton:
            'bg-muted text-muted-foreground hover:bg-muted/80 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
          success:
            'group-[.toaster]:border-emerald-600/30 group-[.toaster]:bg-emerald-600/5',
          error:
            'group-[.toaster]:border-red-600/30 group-[.toaster]:bg-red-600/5',
          warning:
            'group-[.toaster]:border-yellow-600/30 group-[.toaster]:bg-yellow-600/5',
          info: 'group-[.toaster]:border-blue-600/30 group-[.toaster]:bg-blue-600/5',
        },
      }}
      style={
        {
          '--normal-bg': 'var(--card)',
          '--normal-text': 'var(--card-foreground)',
          '--normal-border': 'var(--border)',
        } as React.CSSProperties
      }
      {...props}
    />
  )
}
