'use client'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import {
  ArrowLeft, Plus, Sparkles, Users, Pencil, Eye, RefreshCw, Save, Loader2,
  LayoutDashboard, Maximize2, Minimize2, Settings2,
} from 'lucide-react'
import { useState, useEffect, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { motion } from 'framer-motion'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove, SortableContext, sortableKeyboardCoordinates, rectSortingStrategy,
} from '@dnd-kit/sortable'
import { useApiData } from '@/hooks/use-api-data'
import {
  parseSharedWith, type CustomDashboardDTO, type CustomWidgetDTO,
} from './types'
import { DASHBOARD_ACCENTS, getDataSource, type AccentColor, type WidgetType } from './widget-catalog'
import { DashboardWidget } from './widget'
import { WidgetLibrary } from './widget-library'
import { WidgetConfigModal } from './widget-config-modal'
import { AiWidgetBuilder } from './ai-builder'
import { ShareDialog } from './share-dialog'
import { PresenceIndicator } from './presence-indicator'
import { cn } from '@/lib/utils'

interface Props {
  dashboardId: string
  onBack: () => void
}

export function DashboardEditor({ dashboardId, onBack }: Props) {
  const { data: dashboard, loading, refetch } = useApiData<CustomDashboardDTO>(
    `/api/dashboards/${dashboardId}`,
    15000,
  )
  const [editMode, setEditMode] = useState(false)
  const [libraryOpen, setLibraryOpen] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [configWidget, setConfigWidget] = useState<CustomWidgetDTO | null>(null)
  const [localWidgets, setLocalWidgets] = useState<CustomWidgetDTO[]>([])
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  // Sync from server when not dirty
  useEffect(() => {
    if (dashboard && !dirty) {
      setLocalWidgets(dashboard.widgets)
    }
  }, [dashboard, dirty])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      if (!over || active.id === over.id) return
      setLocalWidgets((items) => {
        const oldIndex = items.findIndex((w) => w.id === active.id)
        const newIndex = items.findIndex((w) => w.id === over.id)
        if (oldIndex < 0 || newIndex < 0) return items
        return arrayMove(items, oldIndex, newIndex)
      })
      setDirty(true)
    },
    [],
  )

  async function persistLayout() {
    setSaving(true)
    try {
      // Persist the visual order using posY as a sequential index. The GET
      // handler orders widgets by posY (then createdAt as tiebreaker), so the
      // reordering survives a refetch. posX is kept at 0 for now since the
      // grid uses implicit CSS flow (widget.width spans columns automatically).
      const layout = localWidgets.map((w, idx) => ({
        id: w.id,
        posX: 0,
        posY: idx,
        width: w.width,
        height: w.height,
      }))
      const res = await fetch(`/api/dashboards/${dashboardId}/widgets`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout }),
      })
      if (!res.ok) throw new Error(await res.text())
      setDirty(false)
      toast.success('Layout saved')
      refetch()
    } catch {
      toast.error('Failed to save layout')
    } finally {
      setSaving(false)
    }
  }

  async function handleAddWidget(sourceKey: string, type: WidgetType) {
    const meta = getDataSource(sourceKey)
    if (!meta) return
    try {
      const res = await fetch(`/api/dashboards/${dashboardId}/widgets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type,
          title: meta.label,
          subtitle: meta.group,
          dataSource: sourceKey,
          config: {},
          width:
            type === 'kpi' ? 4
              : type === 'table' ? 12
              : 6,
          height:
            type === 'kpi' ? 2
              : type === 'table' ? 4
              : 3,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      toast.success(`Added ${meta.label}`)
      // Note: do NOT clear `dirty` here — doing so would let the server data
      // overwrite any unsaved drag-and-drop reordering the user already made.
      // The server appends the new widget at the end (posY = max + 1), so it
      // will appear after the user's reordered widgets on the next refetch.
      refetch()
    } catch {
      toast.error('Failed to add widget')
    }
  }

  async function handleDeleteWidget(id: string) {
    try {
      const res = await fetch(`/api/widgets/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(await res.text())
      toast.success('Widget removed')
      refetch()
    } catch {
      toast.error('Failed to remove widget')
    }
  }

  async function handleResize(id: string, dir: 'wider' | 'narrower' | 'taller' | 'shorter') {
    const w = localWidgets.find((x) => x.id === id)
    if (!w) return
    const updates: Partial<CustomWidgetDTO> = {}
    if (dir === 'wider') updates.width = Math.min(12, w.width + 2)
    if (dir === 'narrower') updates.width = Math.max(2, w.width - 2)
    if (dir === 'taller') updates.height = Math.min(6, w.height + 1)
    if (dir === 'shorter') updates.height = Math.max(1, w.height - 1)
    try {
      await fetch(`/api/widgets/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      refetch()
    } catch {
      toast.error('Failed to resize')
    }
  }

  const shared = useMemo(
    () => (dashboard ? parseSharedWith(dashboard.sharedWith) : []),
    [dashboard],
  )
  const accent = dashboard
    ? DASHBOARD_ACCENTS[(dashboard.color as AccentColor) || 'emerald'] ?? DASHBOARD_ACCENTS.emerald
    : DASHBOARD_ACCENTS.emerald

  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        Dashboard not found.{' '}
        <Button variant="link" onClick={onBack}>Go back</Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Sticky top bar */}
      <div className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur-md">
        <div className="px-4 md:px-6 py-3 flex items-center gap-3 flex-wrap">
          <Button size="sm" variant="ghost" onClick={onBack} className="gap-1.5 -ml-2">
            <ArrowLeft className="h-4 w-4" />
            All dashboards
          </Button>
          <div className="h-5 w-px bg-border" />
          <div
            className="h-8 w-8 rounded-md flex items-center justify-center shrink-0"
            style={{ background: `linear-gradient(135deg, ${accent.from}, ${accent.to})` }}
          >
            <LayoutDashboard className="h-4 w-4 text-white" />
          </div>
          <div className="min-w-0">
            <div className="font-semibold text-base truncate flex items-center gap-2">
              {dashboard.name}
              {dirty && (
                <Badge variant="outline" className="text-[10px] gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500 nexus-pulse" />
                  unsaved
                </Badge>
              )}
            </div>
            {dashboard.description && (
              <div className="text-[11px] text-muted-foreground truncate">
                {dashboard.description}
              </div>
            )}
          </div>

          <div className="ml-auto flex items-center gap-2 flex-wrap">
            <PresenceIndicator dashboardId={dashboard.id} sharedWith={shared} />

            {dirty && (
              <Button size="sm" onClick={persistLayout} disabled={saving} className="gap-1.5">
                {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                Save layout
              </Button>
            )}

            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              onClick={() => setShareOpen(true)}
            >
              <Users className="h-3.5 w-3.5" />
              Share
              {shared.length > 0 && (
                <Badge variant="secondary" className="ml-1 h-4 px-1 text-[10px]">
                  {shared.length}
                </Badge>
              )}
            </Button>

            <Button
              size="sm"
              variant={editMode ? 'default' : 'outline'}
              className="gap-1.5"
              onClick={() => setEditMode((v) => !v)}
            >
              {editMode ? (
                <>
                  <Eye className="h-3.5 w-3.5" />
                  View mode
                </>
              ) : (
                <>
                  <Pencil className="h-3.5 w-3.5" />
                  Edit
                </>
              )}
            </Button>

            <Button size="icon" variant="ghost" onClick={() => refetch()} aria-label="Refresh">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {editMode && (
          <div className="px-4 md:px-6 pb-3 flex items-center gap-2 flex-wrap border-t border-border/40 pt-3">
            <Button size="sm" onClick={() => setLibraryOpen(true)} className="gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              Widget library
            </Button>
            <Button size="sm" variant="outline" onClick={() => setAiOpen(true)} className="gap-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              Build with AI
            </Button>
            <span className="text-[11px] text-muted-foreground ml-2 hidden md:inline">
              Drag widgets to reorder. Use the gear icon to configure each widget.
            </span>
          </div>
        )}
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        {localWidgets.length === 0 ? (
          <EmptyCanvas
            onLibrary={() => {
              setEditMode(true)
              setLibraryOpen(true)
            }}
            onAi={() => {
              setEditMode(true)
              setAiOpen(true)
            }}
          />
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={localWidgets.map((w) => w.id)}
              strategy={rectSortingStrategy}
            >
              <motion.div
                layout
                className="grid grid-cols-12 auto-rows-[80px] gap-3 md:gap-4"
              >
                {localWidgets.map((w) => (
                  <WidgetWithControls
                    key={w.id}
                    widget={w}
                    editMode={editMode}
                    onConfigure={() => setConfigWidget(w)}
                    onDelete={() => handleDeleteWidget(w.id)}
                    onResize={(d) => handleResize(w.id, d)}
                  />
                ))}
              </motion.div>
            </SortableContext>
          </DndContext>
        )}
      </div>

      {/* Modals */}
      <WidgetLibrary
        open={libraryOpen}
        onOpenChange={setLibraryOpen}
        onAdd={handleAddWidget}
      />
      <WidgetConfigModal
        widget={configWidget}
        open={configWidget !== null}
        onOpenChange={(v) => !v && setConfigWidget(null)}
        onSaved={refetch}
      />
      <AiWidgetBuilder
        dashboardId={dashboardId}
        open={aiOpen}
        onOpenChange={setAiOpen}
        onWidgetAdded={refetch}
      />
      <ShareDialog
        dashboard={dashboard}
        open={shareOpen}
        onOpenChange={setShareOpen}
        onUpdated={refetch}
      />
    </div>
  )
}

function WidgetWithControls({
  widget,
  editMode,
  onConfigure,
  onDelete,
  onResize,
}: {
  widget: CustomWidgetDTO
  editMode: boolean
  onConfigure: () => void
  onDelete: () => void
  onResize: (dir: 'wider' | 'narrower' | 'taller' | 'shorter') => void
}) {
  return (
    // `group` must live on the same ancestor as the resize controls so the
    // `group-hover:opacity-100` toggle on the controls activates correctly.
    <div
      className="relative group"
      style={{
        gridColumn: `span ${widget.width} / span ${widget.width}`,
        gridRow: `span ${widget.height} / span ${widget.height}`,
      }}
    >
      <DashboardWidget
        widget={widget}
        editMode={editMode}
        onConfigure={onConfigure}
        onDelete={onDelete}
      />
      {editMode && (
        <div className="absolute bottom-1 right-1 z-10 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="icon"
                variant="secondary"
                className="h-6 w-6 shadow-sm"
                aria-label="Resize widget"
              >
                <Settings2 className="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel className="text-[10px]">Resize</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => onResize('wider')}>
                <Maximize2 className="h-3.5 w-3.5 mr-2" /> Wider
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onResize('narrower')}>
                <Minimize2 className="h-3.5 w-3.5 mr-2" /> Narrower
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onResize('taller')}>
                <Maximize2 className="h-3.5 w-3.5 mr-2 rotate-90" /> Taller
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onResize('shorter')}>
                <Minimize2 className="h-3.5 w-3.5 mr-2 rotate-90" /> Shorter
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  )
}

function EmptyCanvas({
  onLibrary, onAi,
}: { onLibrary: () => void; onAi: () => void }) {
  return (
    <Card className="p-12 flex flex-col items-center justify-center text-center max-w-2xl mx-auto mt-12">
      <div className="h-14 w-14 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4">
        <Sparkles className="h-7 w-7" />
      </div>
      <h3 className="font-semibold text-lg mb-1">Empty canvas — let&apos;s add some widgets</h3>
      <p className="text-sm text-muted-foreground max-w-md mb-5">
        Pick from the widget library to mount live NEXUS metrics, or describe what you
        want to see and let the AI builder assemble it for you.
      </p>
      <div className="flex items-center gap-2 flex-wrap justify-center">
        <Button onClick={onLibrary} className="gap-1.5">
          <Plus className="h-4 w-4" />
          Open widget library
        </Button>
        <Button variant="outline" onClick={onAi} className="gap-1.5">
          <Sparkles className="h-4 w-4" />
          Build with AI
        </Button>
      </div>
    </Card>
  )
}
