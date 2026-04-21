'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Command,
  Keyboard,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
} from 'lucide-react'
import { useEffect, useCallback } from 'react'

interface KeyboardShortcutsProps {
  open: boolean
  onClose: () => void
}

const shortcutCategories = [
  {
    name: 'Navigation',
    shortcuts: [
      { keys: ['⌘', 'K'], description: 'Open command palette' },
      { keys: ['1-8'], description: 'Switch between tabs' },
      { keys: ['⌘', 'B'], description: 'Toggle sidebar' },
      { keys: ['?'], description: 'Show keyboard shortcuts' },
    ],
  },
  {
    name: 'Actions',
    shortcuts: [
      { keys: ['⌘', 'L'], description: 'Open system logs' },
      { keys: ['Esc'], description: 'Close current dialog/panel' },
      { keys: ['⌘', 'D'], description: 'Toggle dark/light theme' },
      { keys: ['⌘', 'E'], description: 'Export current data' },
    ],
  },
  {
    name: 'System',
    shortcuts: [
      { keys: ['R'], description: 'Run system diagnostic' },
      { keys: ['S'], description: 'Open AI assistant chat' },
      { keys: ['/'], description: 'Focus search in command palette' },
      { keys: ['P'], description: 'Pause/resume activity feed' },
    ],
  },
]

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-5 min-w-[20px] items-center justify-center rounded border border-border bg-muted px-1.5 text-[10px] font-mono font-medium text-muted-foreground shadow-sm">
      {children}
    </kbd>
  )
}

export function KeyboardShortcuts({ open, onClose }: KeyboardShortcutsProps) {
  // Close on Escape
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && open) {
      onClose()
    }
  }, [open, onClose])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-lg p-0 overflow-hidden">
        {/* Gradient Header */}
        <div className="relative bg-gradient-to-r from-emerald-600/10 via-blue-600/5 to-transparent px-6 py-4 border-b border-border">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Keyboard className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              Keyboard Shortcuts
            </DialogTitle>
          </DialogHeader>
          <p className="text-[11px] text-muted-foreground mt-1">
            Use these shortcuts to navigate and control NEXUS OS faster
          </p>
        </div>

        {/* Shortcuts List */}
        <div className="max-h-[60vh] overflow-y-auto custom-scrollbar p-6 space-y-5">
          {shortcutCategories.map((category, catIdx) => (
            <div key={category.name}>
              {catIdx > 0 && <Separator className="mb-4 bg-border/50" />}
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                <Badge variant="outline" className="text-[9px] font-medium h-5">{category.name}</Badge>
              </h3>
              <div className="space-y-2">
                {category.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between rounded-md px-3 py-2 hover:bg-accent/30 transition-colors"
                  >
                    <span className="text-xs text-foreground">{shortcut.description}</span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIdx) => (
                        <span key={keyIdx} className="flex items-center gap-1">
                          {key === '↑' ? (
                            <Kbd><ArrowUp className="h-2.5 w-2.5" /></Kbd>
                          ) : key === '↓' ? (
                            <Kbd><ArrowDown className="h-2.5 w-2.5" /></Kbd>
                          ) : key === '←' ? (
                            <Kbd><ArrowLeft className="h-2.5 w-2.5" /></Kbd>
                          ) : key === '→' ? (
                            <Kbd><ArrowRight className="h-2.5 w-2.5" /></Kbd>
                          ) : key === '⌘' ? (
                            <Kbd>⌘</Kbd>
                          ) : key === 'Esc' ? (
                            <Kbd>Esc</Kbd>
                          ) : (
                            <Kbd>{key}</Kbd>
                          )}
                          {keyIdx < shortcut.keys.length - 1 && (
                            <span className="text-[9px] text-muted-foreground">+</span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-6 py-3 bg-accent/10">
          <p className="text-[10px] text-muted-foreground text-center">
            Press <Kbd>Esc</Kbd> to close · Press <Kbd>?</Kbd> anytime to open this panel
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
