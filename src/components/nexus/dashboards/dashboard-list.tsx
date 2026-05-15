'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogAction,
  AlertDialogCancel,
} from '@/components/ui/alert-dialog'
import {
  Plus,
  LayoutDashboard,
  Pencil,
  Share2,
  Trash2,
  Clock,
  Blocks,
  Loader2,
  LayoutGrid,
  LayoutList,
  Search,
  Grid3x3,
  ArrowUpRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'
import type { DashboardListItem, CreateDashboardRequest, LayoutType } from '@/lib/dashboard-types'

interface DashboardListProps {
  onEditDashboard: (id: string) => void
  onShareDashboard: (id: string) => void
}

const MOCK_DASHBOARDS: DashboardListItem[] = [
  {
    id: 'dash-1',
    name: 'System Overview',
    description: 'High-level system health, uptime, and resource utilization at a glance.',
    layout: 'grid',
    columns: 12,
    widgetCount: 8,
    tags: ['system', 'health', 'monitoring'],
    isPublic: false,
    updatedAt: '2025-03-04T11:00:00.000Z',
  },
  {
    id: 'dash-2',
    name: 'Agent Performance',
    description: 'Track agent trust scores, task completion rates, and model assignments.',
    layout: 'grid',
    columns: 12,
    widgetCount: 6,
    tags: ['agents', 'performance', 'ai'],
    isPublic: true,
    updatedAt: '2025-03-04T10:00:00.000Z',
  },
  {
    id: 'dash-3',
    name: 'Token Economics',
    description: 'Monitor token usage, burn rates, budget allocation, and cost efficiency.',
    layout: 'grid',
    columns: 8,
    widgetCount: 5,
    tags: ['tokens', 'cost', 'budget'],
    isPublic: false,
    updatedAt: '2025-03-03T12:00:00.000Z',
  },
  {
    id: 'dash-4',
    name: 'Governor Audit',
    description: 'Constitutional compliance, blocked actions, and security posture.',
    layout: 'freeform',
    columns: 12,
    widgetCount: 4,
    tags: ['governor', 'security', 'compliance'],
    isPublic: false,
    updatedAt: '2025-03-02T12:00:00.000Z',
  },
]

export function DashboardList({ onEditDashboard, onShareDashboard }: DashboardListProps) {
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  // Create dialog state
  const [createOpen, setCreateOpen] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createDescription, setCreateDescription] = useState('')
  const [createLayout, setCreateLayout] = useState<LayoutType>('grid')
  const [createColumns, setCreateColumns] = useState('12')
  const [createSeedDefaults, setCreateSeedDefaults] = useState(true)
  const [creating, setCreating] = useState(false)

  // Delete dialog state
  const [deleteTarget, setDeleteTarget] = useState<DashboardListItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchDashboards = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/dashboards')
      if (res.ok) {
        const data = await res.json()
        setDashboards(data.dashboards || [])
        return
      }
    } catch {
      // Fall back to mock data
    }
    // Use mock data when API is unavailable
    setDashboards(MOCK_DASHBOARDS)
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchDashboards()
  }, [fetchDashboards])

  const handleCreate = async () => {
    if (!createName.trim()) return
    setCreating(true)
    const req: CreateDashboardRequest = {
      name: createName,
      description: createDescription || undefined,
      layout: createLayout,
      columns: parseInt(createColumns),
      seedWithDefaults: createSeedDefaults,
    }
    try {
      const res = await fetch('/api/dashboards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      })
      if (res.ok) {
        const data = await res.json()
        onEditDashboard(data.id)
        setCreateOpen(false)
        resetCreateForm()
        setCreating(false)
        return
      }
    } catch {
      // Fall back to local creation
    }
    // Mock: create locally
    const newDash: DashboardListItem = {
      id: `dash-${Date.now()}`,
      name: createName,
      description: createDescription,
      layout: createLayout,
      columns: parseInt(createColumns),
      widgetCount: createSeedDefaults ? 4 : 0,
      tags: [],
      isPublic: false,
      updatedAt: new Date().toISOString(),
    }
    setDashboards((prev) => [newDash, ...prev])
    onEditDashboard(newDash.id)
    setCreateOpen(false)
    resetCreateForm()
    setCreating(false)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      const res = await fetch(`/api/dashboards/${deleteTarget.id}`, { method: 'DELETE' })
      if (res.ok) {
        setDashboards((prev) => prev.filter((d) => d.id !== deleteTarget.id))
        setDeleteTarget(null)
        setDeleting(false)
        return
      }
    } catch {
      // Fall back to local deletion
    }
    setDashboards((prev) => prev.filter((d) => d.id !== deleteTarget.id))
    setDeleteTarget(null)
    setDeleting(false)
  }

  const resetCreateForm = () => {
    setCreateName('')
    setCreateDescription('')
    setCreateLayout('grid')
    setCreateColumns('12')
    setCreateSeedDefaults(true)
  }

  const filteredDashboards = dashboards.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.description.toLowerCase().includes(search.toLowerCase()) ||
      d.tags.some((t) => t.toLowerCase().includes(search.toLowerCase())),
  )

  const formatTimeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime()
    const minutes = Math.floor(diff / 60000)
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        <span className="ml-3 text-sm text-muted-foreground">Loading dashboards...</span>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Top Bar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search dashboards..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 h-8 text-xs"
          />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex border border-border rounded-md">
            <Button
              size="sm"
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
              className="h-7 w-7 p-0 rounded-r-none"
              onClick={() => setViewMode('grid')}
              aria-label="Grid view"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              className="h-7 w-7 p-0 rounded-l-none"
              onClick={() => setViewMode('list')}
              aria-label="List view"
            >
              <LayoutList className="h-3.5 w-3.5" />
            </Button>
          </div>
          <Button
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 h-8"
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="h-3.5 w-3.5" />
            Create Dashboard
          </Button>
        </div>
      </div>

      {/* Empty State */}
      {filteredDashboards.length === 0 && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-16"
        >
          <div className="mx-auto w-20 h-20 rounded-2xl bg-emerald-600/10 flex items-center justify-center mb-4">
            <LayoutDashboard className="h-10 w-10 text-emerald-600 dark:text-emerald-400" />
          </div>
          <h3 className="text-lg font-semibold mb-2">
            {search ? 'No dashboards found' : 'No dashboards yet'}
          </h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
            {search
              ? `No dashboards match "${search}". Try a different search term.`
              : 'Create your first custom dashboard with drag-and-drop widgets, live metrics, and personalized layouts.'}
          </p>
          {!search && (
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
              onClick={() => setCreateOpen(true)}
            >
              <Plus className="h-4 w-4" />
              Create Your First Dashboard
            </Button>
          )}
        </motion.div>
      )}

      {/* Grid View */}
      {viewMode === 'grid' && filteredDashboards.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDashboards.map((dashboard, index) => (
            <motion.div
              key={dashboard.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card className="bg-card/50 border-border/50 hover:border-emerald-600/30 transition-all group h-full flex flex-col">
                <CardContent className="p-4 flex-1 flex flex-col">
                  {/* Header */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="p-1.5 rounded bg-emerald-600/10 shrink-0">
                        <LayoutDashboard className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <h3 className="text-sm font-semibold truncate">{dashboard.name}</h3>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {dashboard.isPublic && (
                        <Badge className="text-[8px] h-4 px-1 bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
                          PUBLIC
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-[8px] h-4 px-1">
                        {dashboard.layout === 'grid' ? 'Grid' : 'Freeform'}
                      </Badge>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-3 flex-1">
                    {dashboard.description || 'No description'}
                  </p>

                  {/* Meta */}
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground mb-3">
                    <div className="flex items-center gap-1">
                      <Blocks className="h-3 w-3" />
                      {dashboard.widgetCount} widgets
                    </div>
                    <div className="flex items-center gap-1">
                      <Grid3x3 className="h-3 w-3" />
                      {dashboard.columns} cols
                    </div>
                    <div className="flex items-center gap-1" suppressHydrationWarning>
                      <Clock className="h-3 w-3" />
                      {formatTimeAgo(dashboard.updatedAt)}
                    </div>
                  </div>

                  {/* Tags */}
                  {dashboard.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {dashboard.tags.slice(0, 4).map((tag) => (
                        <Badge
                          key={tag}
                          variant="outline"
                          className="text-[9px] h-4 px-1.5 border-emerald-600/20 text-emerald-700 dark:text-emerald-400"
                        >
                          {tag}
                        </Badge>
                      ))}
                      {dashboard.tags.length > 4 && (
                        <Badge variant="outline" className="text-[9px] h-4 px-1.5">
                          +{dashboard.tags.length - 4}
                        </Badge>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-1 pt-2 border-t border-border/30">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-[10px] gap-1 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-600/10"
                      onClick={() => onEditDashboard(dashboard.id)}
                    >
                      <Pencil className="h-3 w-3" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-[10px] gap-1"
                      onClick={() => onShareDashboard(dashboard.id)}
                    >
                      <Share2 className="h-3 w-3" />
                      Share
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-[10px] gap-1 ml-auto text-muted-foreground hover:text-red-500 hover:bg-red-500/10"
                      onClick={() => setDeleteTarget(dashboard)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* List View */}
      {viewMode === 'list' && filteredDashboards.length > 0 && (
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-0">
            <div className="divide-y divide-border/30">
              {filteredDashboards.map((dashboard) => (
                <div
                  key={dashboard.id}
                  className="flex items-center gap-4 p-3 hover:bg-muted/30 transition-colors group"
                >
                  <div className="p-2 rounded-lg bg-emerald-600/10 shrink-0">
                    <LayoutDashboard className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate">{dashboard.name}</span>
                      {dashboard.isPublic && (
                        <Badge className="text-[8px] h-3.5 px-1 bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
                          PUBLIC
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {dashboard.description || 'No description'}
                    </p>
                  </div>
                  <div className="hidden sm:flex items-center gap-3 text-[10px] text-muted-foreground shrink-0">
                    <span className="flex items-center gap-1">
                      <Blocks className="h-3 w-3" />
                      {dashboard.widgetCount}
                    </span>
                    <span className="flex items-center gap-1" suppressHydrationWarning>
                      <Clock className="h-3 w-3" />
                      {formatTimeAgo(dashboard.updatedAt)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {dashboard.tags.slice(0, 2).map((tag) => (
                      <Badge
                        key={tag}
                        variant="outline"
                        className="text-[9px] h-4 px-1 border-emerald-600/20 text-emerald-700 dark:text-emerald-400 hidden md:inline-flex"
                      >
                        {tag}
                      </Badge>
                    ))}
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0"
                      onClick={() => onEditDashboard(dashboard.id)}
                      aria-label="Edit dashboard"
                    >
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-red-500"
                      onClick={() => setDeleteTarget(dashboard)}
                      aria-label="Delete dashboard"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Dashboard Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              Create Dashboard
            </DialogTitle>
            <DialogDescription>
              Set up a new custom dashboard with your preferred layout and widgets.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs">Name</Label>
              <Input
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                placeholder="My Dashboard"
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Description</Label>
              <Textarea
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="What this dashboard shows..."
                className="text-xs min-h-[60px] resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Layout Type</Label>
                <Select value={createLayout} onValueChange={(v: LayoutType) => setCreateLayout(v)}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="grid" className="text-xs">Grid</SelectItem>
                    <SelectItem value="freeform" className="text-xs">Freeform</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Columns</Label>
                <Select value={createColumns} onValueChange={setCreateColumns}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="6" className="text-xs">6 columns</SelectItem>
                    <SelectItem value="8" className="text-xs">8 columns</SelectItem>
                    <SelectItem value="12" className="text-xs">12 columns</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-2 p-3 rounded-lg bg-muted/30">
              <Checkbox
                id="seed-defaults"
                checked={createSeedDefaults}
                onCheckedChange={(checked) => setCreateSeedDefaults(checked === true)}
                className="data-[state=checked]:bg-emerald-600 data-[state=checked]:border-emerald-600"
              />
              <div>
                <Label htmlFor="seed-defaults" className="text-xs font-medium cursor-pointer">
                  Seed with default widgets
                </Label>
                <p className="text-[10px] text-muted-foreground">
                  Add a basic set of monitoring widgets to get started quickly
                </p>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCreateOpen(false)} className="text-xs">
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleCreate}
              disabled={!createName.trim() || creating}
              className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 text-xs"
            >
              {creating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Dashboard</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteTarget?.name}&quot;? This action cannot be undone.
              All widgets and configuration will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className={cn(
                'bg-red-600 hover:bg-red-700 text-white',
                deleting && 'opacity-50',
              )}
            >
              {deleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
