'use client'

import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Users, X, Eye, Pencil, Copy, Check } from 'lucide-react'
import { parseSharedWith, type SharedMember, type CustomDashboardDTO } from './types'

// Common teammates suggestions (in a multi-tenant deployment these come from a /api/team endpoint)
const SUGGESTED_TEAMMATES: { id: string; name: string }[] = [
  { id: 'op-2', name: 'Avery Quinn' },
  { id: 'op-3', name: 'Jordan Park' },
  { id: 'op-4', name: 'Sam Rivera' },
  { id: 'op-5', name: 'Morgan Chen' },
  { id: 'op-6', name: 'Riley Hayes' },
]

interface Props {
  dashboard: CustomDashboardDTO
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdated: () => void
}

export function ShareDialog({ dashboard, open, onOpenChange, onUpdated }: Props) {
  const [members, setMembers] = useState<SharedMember[]>(() => parseSharedWith(dashboard.sharedWith))
  const [newName, setNewName] = useState('')
  const [newRole, setNewRole] = useState<'viewer' | 'editor'>('viewer')
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(false)

  // Reset members only when the upstream sharing data actually changes —
  // depending on the whole `dashboard` object would also reset on every poll
  // (15s) and silently discard in-flight edits in the dialog.
  useEffect(() => {
    setMembers(parseSharedWith(dashboard.sharedWith))
  }, [dashboard.sharedWith])

  const shareLink =
    typeof window !== 'undefined'
      ? `${window.location.origin}/?dashboard=${dashboard.id}`
      : `?dashboard=${dashboard.id}`

  function addMember(name: string, role: 'viewer' | 'editor') {
    const trimmed = name.trim()
    if (!trimmed) return
    if (members.some((m) => m.name.toLowerCase() === trimmed.toLowerCase())) {
      toast.error('Already shared with that person')
      return
    }
    setMembers([
      ...members,
      {
        id: `op-${Date.now()}`,
        name: trimmed,
        role,
      },
    ])
    setNewName('')
  }

  function removeMember(id: string) {
    setMembers(members.filter((m) => m.id !== id))
  }

  function updateRole(id: string, role: 'viewer' | 'editor') {
    setMembers(members.map((m) => (m.id === id ? { ...m, role } : m)))
  }

  async function handleSave() {
    setSaving(true)
    try {
      const res = await fetch(`/api/dashboards/${dashboard.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sharedWith: members }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success(`Shared with ${members.length} ${members.length === 1 ? 'person' : 'people'}`)
      onUpdated()
      onOpenChange(false)
    } catch {
      toast.error('Failed to update sharing')
    } finally {
      setSaving(false)
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareLink)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Could not copy link')
    }
  }

  const availableSuggestions = SUGGESTED_TEAMMATES.filter(
    (s) =>
      !members.some(
        (m) => m.id === s.id || m.name.toLowerCase() === s.name.toLowerCase(),
      ),
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            Share &ldquo;{dashboard.name}&rdquo;
          </DialogTitle>
          <DialogDescription>
            Invite teammates to view or edit this dashboard.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Link */}
          <div className="grid gap-2">
            <Label>Share link</Label>
            <div className="flex items-center gap-2">
              <Input value={shareLink} readOnly className="font-mono text-xs flex-1" />
              <Button size="sm" variant="outline" onClick={copyLink}>
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              </Button>
            </div>
          </div>

          {/* Add by name */}
          <div className="grid gap-2">
            <Label>Add by name</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Teammate name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    addMember(newName, newRole)
                  }
                }}
                className="flex-1"
              />
              <Select value={newRole} onValueChange={(v) => setNewRole(v as 'viewer' | 'editor')}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="viewer">Viewer</SelectItem>
                  <SelectItem value="editor">Editor</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={() => addMember(newName, newRole)} disabled={!newName.trim()}>
                Add
              </Button>
            </div>
          </div>

          {/* Suggestions */}
          {availableSuggestions.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-[11px] text-muted-foreground">Suggested teammates</Label>
              <div className="flex flex-wrap gap-1.5">
                {availableSuggestions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => addMember(s.name, 'viewer')}
                    className="text-[11px] px-2 py-1 rounded-md border border-border/60 hover:border-primary/40 hover:bg-accent transition-colors"
                  >
                    + {s.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Current members */}
          <div className="space-y-1.5">
            <Label>Shared with ({members.length})</Label>
            {members.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">
                Not shared yet. Only you can see this dashboard.
              </p>
            ) : (
              <div className="space-y-1 max-h-48 overflow-auto custom-scrollbar">
                {members.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center gap-2 p-2 rounded-md border border-border/40 bg-card/50"
                  >
                    <div className="h-7 w-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-semibold">
                      {m.name.slice(0, 1).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0 text-sm truncate">{m.name}</div>
                    <Select
                      value={m.role}
                      onValueChange={(v) => updateRole(m.id, v as 'viewer' | 'editor')}
                    >
                      <SelectTrigger className="h-7 w-24 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="viewer">
                          <span className="flex items-center gap-1.5">
                            <Eye className="h-3 w-3" /> Viewer
                          </span>
                        </SelectItem>
                        <SelectItem value="editor">
                          <span className="flex items-center gap-1.5">
                            <Pencil className="h-3 w-3" /> Editor
                          </span>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={() => removeMember(m.id)}
                      aria-label="Remove member"
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save sharing'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
