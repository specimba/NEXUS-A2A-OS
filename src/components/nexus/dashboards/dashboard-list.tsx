'use client'

import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import {
  Plus, Search, MoreVertical, Star, Pin, Copy, Trash2, Users, Layers,
  Loader2, Sparkles, Filter, LayoutDashboard,
} from 'lucide-react'
import { useState, useMemo } from 'react'
import { toast } from 'sonner'
import { motion, AnimatePresence } from 'framer-motion'
import { useApiData } from '@/hooks/use-api-data'
import {
  parseSharedWith, parseTags, type CustomDashboardDTO,
} from './types'
import { DASHBOARD_ACCENTS, type AccentColor } from './widget-catalog'
import { cn } from '@/lib/utils'

interface Props {
  onOpen: (id: string) => void
}

export function DashboardList({ onOpen }: Props) {
  const { data, loading, refetch } = useApiData<CustomDashboardDTO[]>(
    '/api/dashboards',
    20000,
  )
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'favorites' | 'shared'>('all')
  const [createOpen, setCreateOpen] = useState(false)

  const dashboards = data ?? []

  const filtered = useMemo(() => {
    let list = [...dashboards]
    if (filter === 'favorites') list = list.filter((d) => d.isFavorite || d.isPinned)
    if (filter === 'shared') list = list.filter((d) => parseSharedWith(d.sharedWith).length > 0)
    const q = query.trim().toLowerCase()
    if (q) {
      list = list.filter(
        (d) =>
          d.name.toLowerCase().includes(q) ||
          (d.description ?? '').toLowerCase().includes(q),
      )
    }
    return list
  }, [dashboards, query, filter])

  async function handleDuplicate(d: CustomDashboardDTO) {
    try {
      const res = await fetch('/api/dashboards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `${d.name} (copy)`,
          description: d.description,
          icon: d.icon,
          color: d.color,
          tags: parseTags(d.tags),
          cloneFromId: d.id,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Dashboard duplicated')
      refetch()
    } catch {
      toast.error('Failed to duplicate')
    }
  }

  async function handleDelete(d: CustomDashboardDTO) {
    if (!confirm(`Delete dashboard "${d.name}"? This cannot be undone.`)) return
    try {
      const res = await fetch(`/api/dashboards/${d.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Dashboard deleted')
      refetch()
    } catch {
      toast.error('Failed to delete')
    }
  }

  async function handleToggle(d: CustomDashboardDTO, field: 'isFavorite' | 'isPinned') {
    try {
      const res = await fetch(`/api/dashboards/${d.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: !d[field] }),
      })
      if (!res.ok) throw new Error(await res.text())
      refetch()
    } catch {
      toast.error('Failed to update')
    }
  }

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <LayoutDashboard className="h-5 w-5 text-primary" />
            Custom Dashboards
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Build and share monitoring dashboards on top of live NEXUS OS telemetry.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search dashboards..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
            <SelectTrigger className="w-[140px]">
              <Filter className="h-3.5 w-3.5 mr-1" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="favorites">Favorites</SelectItem>
              <SelectItem value="shared">Shared</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => setCreateOpen(true)} className="gap-1.5">
            <Plus className="h-4 w-4" />
            New Dashboard
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total" value={dashboards.length} icon={<Layers className="h-4 w-4" />} />
        <StatCard
          label="Favorites"
          value={dashboards.filter((d) => d.isFavorite || d.isPinned).length}
          icon={<Star className="h-4 w-4" />}
        />
        <StatCard
          label="Shared"
          value={dashboards.filter((d) => parseSharedWith(d.sharedWith).length > 0).length}
          icon={<Users className="h-4 w-4" />}
        />
        <StatCard
          label="Total Widgets"
          value={dashboards.reduce((s, d) => s + (d.widgets?.length ?? 0), 0)}
          icon={<Sparkles className="h-4 w-4" />}
        />
      </div>

      {/* Grid */}
      {loading && !data && (
        <div className="flex items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <EmptyState onCreate={() => setCreateOpen(true)} hasAny={dashboards.length > 0} />
      )}

      <motion.div
        layout
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
      >
        <AnimatePresence mode="popLayout">
          {filtered.map((d) => (
            <DashboardCard
              key={d.id}
              dashboard={d}
              onOpen={() => onOpen(d.id)}
              onToggle={(f) => handleToggle(d, f)}
              onDuplicate={() => handleDuplicate(d)}
              onDelete={() => handleDelete(d)}
            />
          ))}
        </AnimatePresence>
      </motion.div>

      <CreateDashboardDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(id) => {
          refetch()
          onOpen(id)
        }}
      />
    </div>
  )
}

function StatCard({
  label, value, icon,
}: { label: string; value: number; icon: React.ReactNode }) {
  return (
    <Card className="p-4 flex items-center justify-between hover-lift">
      <div>
        <div className="text-xs text-muted-foreground uppercase tracking-wide">{label}</div>
        <div className="text-2xl font-bold tabular-nums mt-0.5">{value}</div>
      </div>
      <div className="h-9 w-9 rounded-md bg-primary/10 text-primary flex items-center justify-center">
        {icon}
      </div>
    </Card>
  )
}

function DashboardCard({
  dashboard,
  onOpen,
  onToggle,
  onDuplicate,
  onDelete,
}: {
  dashboard: CustomDashboardDTO
  onOpen: () => void
  onToggle: (field: 'isFavorite' | 'isPinned') => void
  onDuplicate: () => void
  onDelete: () => void
}) {
  const tags = parseTags(dashboard.tags)
  const shared = parseSharedWith(dashboard.sharedWith)
  const accent = DASHBOARD_ACCENTS[dashboard.color as AccentColor] ?? DASHBOARD_ACCENTS.emerald

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <Card
        className="group relative overflow-hidden hover-lift cursor-pointer h-full flex flex-col"
        onClick={onOpen}
      >
        {/* Accent strip */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{ background: `linear-gradient(90deg, ${accent.from}, ${accent.to})` }}
        />
        {/* Pin marker */}
        {dashboard.isPinned && (
          <Pin className="absolute top-3 right-12 h-3.5 w-3.5 text-primary fill-primary/30" />
        )}

        <div className="p-4 flex-1 flex flex-col">
          <div className="flex items-start justify-between gap-2 mb-3">
            <div
              className={cn(
                'h-10 w-10 rounded-lg flex items-center justify-center',
                accent.bg,
                accent.text,
              )}
            >
              <LayoutDashboard className="h-5 w-5" />
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-7 w-7"
                  onClick={(e) => e.stopPropagation()}
                  aria-label="Dashboard actions"
                >
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                <DropdownMenuItem onClick={() => onToggle('isFavorite')}>
                  <Star className={cn('h-4 w-4 mr-2', dashboard.isFavorite && 'fill-current')} />
                  {dashboard.isFavorite ? 'Remove favorite' : 'Mark favorite'}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onToggle('isPinned')}>
                  <Pin className={cn('h-4 w-4 mr-2', dashboard.isPinned && 'fill-current')} />
                  {dashboard.isPinned ? 'Unpin' : 'Pin to top'}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={onDuplicate}>
                  <Copy className="h-4 w-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={onDelete} className="text-red-600">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="space-y-1 mb-3">
            <div className="flex items-center gap-1.5">
              <h3 className="font-semibold text-base truncate">{dashboard.name}</h3>
              {dashboard.isFavorite && (
                <Star className="h-3.5 w-3.5 text-amber-500 fill-amber-500 flex-shrink-0" />
              )}
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2 min-h-[2rem]">
              {dashboard.description || 'No description'}
            </p>
          </div>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {tags.slice(0, 3).map((t) => (
                <Badge key={t} variant="secondary" className="text-[10px] h-4 px-1.5">
                  {t}
                </Badge>
              ))}
              {tags.length > 3 && (
                <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                  +{tags.length - 3}
                </Badge>
              )}
            </div>
          )}

          <div className="mt-auto pt-3 border-t border-border/40 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1">
                <Layers className="h-3 w-3" />
                {dashboard.widgets?.length ?? 0}
              </span>
              {shared.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users className="h-3 w-3" />
                  {shared.length}
                </span>
              )}
            </div>
            <span>{formatRelative(dashboard.lastViewed)}</span>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}

function EmptyState({ onCreate, hasAny }: { onCreate: () => void; hasAny: boolean }) {
  return (
    <Card className="p-12 flex flex-col items-center justify-center text-center">
      <div className="h-14 w-14 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4">
        <LayoutDashboard className="h-7 w-7" />
      </div>
      <h3 className="font-semibold text-lg mb-1">
        {hasAny ? 'No matching dashboards' : 'No dashboards yet'}
      </h3>
      <p className="text-sm text-muted-foreground max-w-md mb-4">
        {hasAny
          ? 'Try a different search or filter.'
          : 'Create your first custom dashboard to monitor agents, tokens, governor decisions, and more — all in one place.'}
      </p>
      {!hasAny && (
        <Button onClick={onCreate} className="gap-1.5">
          <Plus className="h-4 w-4" /> Create your first dashboard
        </Button>
      )}
    </Card>
  )
}

function CreateDashboardDialog({
  open, onOpenChange, onCreated,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onCreated: (id: string) => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState<AccentColor>('emerald')
  const [tagInput, setTagInput] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleCreate() {
    if (!name.trim()) return
    setSaving(true)
    try {
      const tags = tagInput
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
      const res = await fetch('/api/dashboards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description, color, tags }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error)
      toast.success('Dashboard created')
      onCreated(json.id)
      onOpenChange(false)
      setName('')
      setDescription('')
      setTagInput('')
      setColor('emerald')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to create')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create new dashboard</DialogTitle>
          <DialogDescription>
            Give it a name and pick an accent color. You can add widgets in the next step.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid gap-2">
            <Label htmlFor="d-name">Name</Label>
            <Input
              id="d-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Token Watchtower"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleCreate()
                }
              }}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="d-desc">Description</Label>
            <Input
              id="d-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this dashboard track?"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="d-tags">Tags (comma separated)</Label>
            <Input
              id="d-tags"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="ops, tokens, governance"
            />
          </div>
          <div className="grid gap-2">
            <Label>Accent color</Label>
            <div className="flex items-center gap-2 flex-wrap">
              {(Object.keys(DASHBOARD_ACCENTS) as AccentColor[]).map((c) => {
                const a = DASHBOARD_ACCENTS[c]
                return (
                  <button
                    key={c}
                    onClick={() => setColor(c)}
                    className={cn(
                      'h-8 w-8 rounded-md transition-transform hover:scale-105',
                      color === c && 'ring-2 ring-offset-2 ring-offset-background ring-primary',
                    )}
                    style={{ background: `linear-gradient(135deg, ${a.from}, ${a.to})` }}
                    aria-label={`Color ${c}`}
                  />
                )
              })}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!name.trim() || saving}>
            {saving ? 'Creating...' : 'Create dashboard'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function formatRelative(iso: string): string {
  const date = new Date(iso)
  const diff = Date.now() - date.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString()
}
