'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Check, Copy, Link2, Loader2, Globe, Lock } from 'lucide-react'
import type { Dashboard, ShareResponse } from '@/lib/dashboard-types'

interface ShareDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  dashboard: Dashboard | null
}

export function ShareDialog({ open, onOpenChange, dashboard }: ShareDialogProps) {
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [isPublic, setIsPublic] = useState(dashboard?.isPublic ?? false)
  const [generating, setGenerating] = useState(false)
  const [copied, setCopied] = useState(false)
  const [toggling, setToggling] = useState(false)

  const handleGenerateLink = async () => {
    if (!dashboard) return
    setGenerating(true)
    try {
      const res = await fetch(`/api/dashboards/${dashboard.id}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPublic }),
      })
      if (res.ok) {
        const data: ShareResponse = await res.json()
        setShareUrl(data.shareUrl)
        setIsPublic(data.isPublic)
      }
    } catch {
      // Error handled silently — share URL remains null
    }
    setGenerating(false)
  }

  const handleCopyLink = async () => {
    if (!shareUrl) return
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard write failed — user can copy manually
    }
  }

  const handleTogglePublic = async (checked: boolean) => {
    if (!dashboard) return
    setToggling(true)
    try {
      const res = await fetch(`/api/dashboards/${dashboard.id}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPublic: checked }),
      })
      if (res.ok) {
        const data: ShareResponse = await res.json()
        setIsPublic(data.isPublic)
        if (data.shareUrl) {
          setShareUrl(data.shareUrl)
        }
      }
    } catch {
      // Error handled silently
    }
    setToggling(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            Share Dashboard
          </DialogTitle>
          <DialogDescription>
            Share &quot;{dashboard?.name || 'Dashboard'}&quot; with others via a link.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Public/Private Toggle */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 p-3">
            <div className="flex items-center gap-3">
              {isPublic ? (
                <Globe className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <Lock className="h-4 w-4 text-muted-foreground" />
              )}
              <div>
                <Label className="text-sm font-medium">
                  {isPublic ? 'Public' : 'Private'}
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  {isPublic
                    ? 'Anyone with the link can view this dashboard'
                    : 'Only you can access this dashboard'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {toggling && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
              <Switch
                checked={isPublic}
                onCheckedChange={handleTogglePublic}
                disabled={toggling}
                className="data-[state=checked]:bg-emerald-600"
              />
            </div>
          </div>

          {/* Share Link */}
          {shareUrl ? (
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Share Link</Label>
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={shareUrl}
                  className="text-xs font-mono h-9 flex-1"
                />
                <Button
                  size="sm"
                  variant="outline"
                  className="h-9 px-3 gap-1.5 shrink-0"
                  onClick={handleCopyLink}
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                      <span className="text-xs">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span className="text-xs">Copy</span>
                    </>
                  )}
                </Button>
              </div>
              <div className="flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className={`text-[9px] h-4 ${
                    isPublic
                      ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400'
                      : 'border-border text-muted-foreground'
                  }`}
                >
                  {isPublic ? 'PUBLIC' : 'PRIVATE'}
                </Badge>
                <span className="text-[10px] text-muted-foreground">
                  Link generated successfully
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-emerald-600/10 flex items-center justify-center mb-3">
                <Link2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <p className="text-sm text-muted-foreground mb-3">
                Generate a shareable link for this dashboard
              </p>
              <Button
                onClick={handleGenerateLink}
                disabled={generating}
                className="bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
              >
                {generating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Link2 className="h-4 w-4" />
                )}
                Generate Share Link
              </Button>
            </div>
          )}
        </div>

        <DialogFooter className="sm:justify-start">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="text-xs"
          >
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
