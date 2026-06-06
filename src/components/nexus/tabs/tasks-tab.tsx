'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import {
  ListTodo, Loader2, RefreshCw, Sparkles, Plus, CheckCircle2, XCircle,
  AlertTriangle, Play, ChevronRight, Trash2, RotateCcw, ShieldOff,
  FolderOpen, TrendingUp, CalendarClock, Flag, Tag, User, FileText,
  Clock,
} from 'lucide-react'
import { useEffect, useState, useCallback, useMemo, useRef } from 'react'
import { toast } from 'sonner'

// ── Types ──────────────────────────────────────────────────────────

interface Task {
  id: string
  title: string
  description: string
  priority: string
  status: string
  category: string
  source: string
  assignee: string | null
  completionProof: string | null
  completedBy: string | null
  completedAt: string | null
  dueAt: string | null
  parentId: string | null
  tags: string | null
  metadata: string | null
  createdAt: string
  updatedAt: string
}

// ── Helpers ────────────────────────────────────────────────────────

const PRIORITY_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  P0: { label: 'P0 Critical', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/15', border: 'border-red-600/20' },
  P1: { label: 'P1 High', color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-600/15', border: 'border-orange-600/20' },
  P2: { label: 'P2 Medium', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/15', border: 'border-emerald-600/20' },
  P3: { label: 'P3 Low', color: 'text-gray-500 dark:text-gray-400', bg: 'bg-gray-600/15', border: 'border-gray-600/20' },
}

const STATUS_META: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  open: { label: 'Open', color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-600/15', icon: <FolderOpen className="h-3 w-3" /> },
  in_progress: { label: 'In Progress', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-600/15', icon: <Play className="h-3 w-3" /> },
  completed: { label: 'Completed', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/15', icon: <CheckCircle2 className="h-3 w-3" /> },
  failed: { label: 'Failed', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/15', icon: <XCircle className="h-3 w-3" /> },
  blocked: { label: 'Blocked', color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-600/15', icon: <ShieldOff className="h-3 w-3" /> },
}

const CATEGORY_META: Record<string, { label: string; color: string; bg: string }> = {
  ics_testing: { label: 'ICS Testing', color: 'text-cyan-600 dark:text-cyan-400', bg: 'bg-cyan-600/15' },
  evaluation: { label: 'Evaluation', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/15' },
  safety_review: { label: 'Safety Review', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/15' },
  implementation: { label: 'Implementation', color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-600/15' },
  research: { label: 'Research', color: 'text-violet-600 dark:text-violet-400', bg: 'bg-violet-600/15' },
  fleet: { label: 'Fleet', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-600/15' },
  dashboard: { label: 'Dashboard', color: 'text-pink-600 dark:text-pink-400', bg: 'bg-pink-600/15' },
  security: { label: 'Security', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/15' },
  governance: { label: 'Governance', color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-600/15' },
  general: { label: 'General', color: 'text-gray-500 dark:text-gray-400', bg: 'bg-gray-600/15' },
  context_processing: { label: 'Context', color: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-600/15' },
  memory_research: { label: 'Memory', color: 'text-teal-600 dark:text-teal-400', bg: 'bg-teal-600/15' },
  harness_testing: { label: 'Harness', color: 'text-lime-600 dark:text-lime-400', bg: 'bg-lime-600/15' },
  compression: { label: 'Compression', color: 'text-sky-600 dark:text-sky-400', bg: 'bg-sky-600/15' },
  benchmark: { label: 'Benchmark', color: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-600/15' },
  survey_analysis: { label: 'Survey', color: 'text-fuchsia-600 dark:text-fuchsia-400', bg: 'bg-fuchsia-600/15' },
  infra_build: { label: 'Infra', color: 'text-stone-600 dark:text-stone-400', bg: 'bg-stone-600/15' },
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '—'
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay}d ago`
  return d.toLocaleDateString()
}

function isOverdue(task: Task): boolean {
  if (!task.dueAt || task.status === 'completed' || task.status === 'failed') return false
  return new Date(task.dueAt) < new Date()
}

// ── Stat Card ──────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, gradient, border, iconBg, iconColor }: {
  label: string
  value: number | string
  icon: React.ElementType
  gradient: string
  border: string
  iconBg: string
  iconColor: string
}) {
  return (
    <Card className={`relative overflow-hidden ${border} hover-lift`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${gradient}`} />
      <CardContent className="relative p-3">
        <div className="flex items-center gap-2">
          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${iconBg}`}>
            <Icon className={`h-4 w-4 ${iconColor}`} />
          </div>
          <div>
            <p className="text-[10px] text-muted-foreground">{label}</p>
            <p className="text-lg font-bold tabular-nums">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Task Card ──────────────────────────────────────────────────────

function TaskCard({ task, onView, onStatusChange, onDelete }: {
  task: Task
  onView: (task: Task) => void
  onStatusChange: (task: Task, action: string, proof?: string) => void
  onDelete: (id: string) => void
}) {
  const pMeta = PRIORITY_META[task.priority] || PRIORITY_META.P2
  const sMeta = STATUS_META[task.status] || STATUS_META.open
  const cMeta = CATEGORY_META[task.category] || CATEGORY_META.general
  const overdue = isOverdue(task)

  return (
    <Card className={`relative overflow-hidden border ${pMeta.border} hover-lift transition-all duration-200`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${pMeta.bg.replace('/15', '/5')} to-transparent`} />
      <CardContent className="relative p-4">
        <div className="flex items-start gap-3">
          <div className="flex flex-col items-center gap-1 pt-0.5">
            <Badge className={`${pMeta.bg} ${pMeta.color} border-0 text-[10px] font-bold`}>{task.priority}</Badge>
            {overdue && <AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-sm font-semibold truncate cursor-pointer hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors" onClick={() => onView(task)}>
                {task.title}
              </h3>
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{task.description}</p>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge className={`${sMeta.bg} ${sMeta.color} border-0 text-[9px] gap-0.5`}>{sMeta.icon}{sMeta.label}</Badge>
              <Badge className={`${cMeta.bg} ${cMeta.color} border-0 text-[9px]`}>{cMeta.label}</Badge>
              <Badge className="bg-muted/50 text-muted-foreground border-0 text-[9px] gap-0.5"><Tag className="h-2.5 w-2.5" />{task.source}</Badge>
              {task.assignee && <Badge className="bg-muted/50 text-muted-foreground border-0 text-[9px] gap-0.5"><User className="h-2.5 w-2.5" />{task.assignee}</Badge>}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <span className="text-[10px] text-muted-foreground" suppressHydrationWarning>{formatDate(task.createdAt)}</span>
            <div className="flex items-center gap-1">
              {task.status === 'open' && (
                <Button variant="outline" size="sm" className="h-6 text-[10px] gap-1" onClick={() => onStatusChange(task, 'start')}>
                  <Play className="h-2.5 w-2.5" /> Start
                </Button>
              )}
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => onView(task)}>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Task Detail Dialog ─────────────────────────────────────────────

function TaskDetailDialog({ task, open, onOpenChange, onStatusChange, onDelete }: {
  task: Task | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onStatusChange: (task: Task, action: string, proof?: string) => void
  onDelete: (id: string) => void
}) {
  const [completeProof, setCompleteProof] = useState('')
  const [failReason, setFailReason] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  if (!task) return null

  const pMeta = PRIORITY_META[task.priority] || PRIORITY_META.P2
  const sMeta = STATUS_META[task.status] || STATUS_META.open
  const cMeta = CATEGORY_META[task.category] || CATEGORY_META.general
  const overdue = isOverdue(task)

  const parsedMetadata = (() => {
    try { return task.metadata ? JSON.parse(task.metadata) : null } catch { return null }
  })()

  const parsedTags = (() => {
    try { return task.tags ? JSON.parse(task.tags) : null } catch { return null }
  })()

  const handleAction = async (action: string, proof?: string) => {
    setActionLoading(true)
    try {
      await onStatusChange(task, action, proof)
      setCompleteProof('')
      setFailReason('')
      onOpenChange(false)
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <ListTodo className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Task Detail
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* Title & Priority */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge className={`${pMeta.bg} ${pMeta.color} border-0 text-[10px] font-bold`}>{pMeta.label}</Badge>
              <Badge className={`${sMeta.bg} ${sMeta.color} border-0 text-[10px] gap-0.5`}>{sMeta.icon}{sMeta.label}</Badge>
              <Badge className={`${cMeta.bg} ${cMeta.color} border-0 text-[10px]`}>{cMeta.label}</Badge>
              {overdue && <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px] gap-0.5"><AlertTriangle className="h-2.5 w-2.5" />OVERDUE</Badge>}
            </div>
            <h3 className="text-sm font-bold mt-2">{task.title}</h3>
          </div>

          {/* Description */}
          <div>
            <Label className="text-[10px] text-muted-foreground uppercase tracking-wider">Description</Label>
            <p className="text-xs text-muted-foreground mt-1 whitespace-pre-wrap">{task.description || 'No description'}</p>
          </div>

          {/* Metadata */}
          {parsedMetadata && (
            <div>
              <Label className="text-[10px] text-muted-foreground uppercase tracking-wider">Metadata</Label>
              <div className="mt-1 rounded-md bg-accent/30 p-2.5">
                <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap break-all">{JSON.stringify(parsedMetadata, null, 2)}</pre>
              </div>
            </div>
          )}

          {/* Tags */}
          {parsedTags && Array.isArray(parsedTags) && parsedTags.length > 0 && (
            <div>
              <Label className="text-[10px] text-muted-foreground uppercase tracking-wider">Tags</Label>
              <div className="flex flex-wrap gap-1 mt-1">
                {parsedTags.map((tag: string) => (
                  <Badge key={tag} variant="secondary" className="text-[9px]">{tag}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md bg-accent/20 p-2">
              <p className="text-[9px] text-muted-foreground">Source</p>
              <p className="text-xs font-medium flex items-center gap-1"><Tag className="h-2.5 w-2.5" />{task.source}</p>
            </div>
            <div className="rounded-md bg-accent/20 p-2">
              <p className="text-[9px] text-muted-foreground">Assignee</p>
              <p className="text-xs font-medium flex items-center gap-1"><User className="h-2.5 w-2.5" />{task.assignee || 'Unassigned'}</p>
            </div>
            <div className="rounded-md bg-accent/20 p-2">
              <p className="text-[9px] text-muted-foreground">Created</p>
              <p className="text-xs font-medium" suppressHydrationWarning>{formatDate(task.createdAt)}</p>
            </div>
            {task.dueAt && (
              <div className="rounded-md bg-accent/20 p-2">
                <p className="text-[9px] text-muted-foreground">Due</p>
                <p className={`text-xs font-medium ${overdue ? 'text-red-600 dark:text-red-400' : ''}`} suppressHydrationWarning>{formatDate(task.dueAt)}</p>
              </div>
            )}
            {task.completedAt && (
              <div className="rounded-md bg-accent/20 p-2">
                <p className="text-[9px] text-muted-foreground">Completed</p>
                <p className="text-xs font-medium" suppressHydrationWarning>{formatDate(task.completedAt)}</p>
              </div>
            )}
            {task.completedBy && (
              <div className="rounded-md bg-accent/20 p-2">
                <p className="text-[9px] text-muted-foreground">Completed By</p>
                <p className="text-xs font-medium">{task.completedBy}</p>
              </div>
            )}
          </div>

          {/* Completion Proof */}
          {task.completionProof && (
            <div>
              <Label className="text-[10px] text-muted-foreground uppercase tracking-wider">
                {task.status === 'failed' ? 'Failure Reason' : 'Completion Proof'}
              </Label>
              <div className="mt-1 rounded-md bg-accent/30 p-2.5 border border-border/50">
                <p className="text-xs text-muted-foreground whitespace-pre-wrap">{task.completionProof}</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-3 border-t border-border/50 pt-3">
            {task.status === 'open' && (
              <Button
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                size="sm"
                disabled={actionLoading}
                onClick={() => handleAction('start')}
              >
                {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                Start Task
              </Button>
            )}

            {task.status === 'in_progress' && (
              <>
                <div>
                  <Label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 block">
                    Completion Proof <span className="text-red-500">*</span>
                  </Label>
                  <Textarea
                    placeholder="Describe what was accomplished, evidence, results... (required)"
                    value={completeProof}
                    onChange={(e) => setCompleteProof(e.target.value)}
                    className="text-xs min-h-[80px] resize-none"
                  />
                  <Button
                    className="w-full mt-2 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
                    size="sm"
                    disabled={actionLoading || completeProof.trim().length === 0}
                    onClick={() => handleAction('complete', completeProof)}
                  >
                    {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                    Complete Task
                  </Button>
                </div>
                <div>
                  <Label className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 block">
                    Failure Reason <span className="text-red-500">*</span>
                  </Label>
                  <Textarea
                    placeholder="Explain why this task failed... (required)"
                    value={failReason}
                    onChange={(e) => setFailReason(e.target.value)}
                    className="text-xs min-h-[60px] resize-none"
                  />
                  <Button
                    variant="destructive"
                    className="w-full mt-2 gap-1.5"
                    size="sm"
                    disabled={actionLoading || failReason.trim().length === 0}
                    onClick={() => handleAction('fail', failReason)}
                  >
                    {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
                    Mark as Failed
                  </Button>
                </div>
              </>
            )}

            {(task.status === 'completed' || task.status === 'failed') && (
              <Button
                variant="outline"
                className="w-full gap-1.5"
                size="sm"
                disabled={actionLoading}
                onClick={() => handleAction('reopen')}
              >
                {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                Reopen Task
              </Button>
            )}

            {task.status === 'blocked' && (
              <Button
                variant="outline"
                className="w-full gap-1.5"
                size="sm"
                disabled={actionLoading}
                onClick={() => handleAction('reopen')}
              >
                {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                Unblock Task
              </Button>
            )}

            <Button
              variant="ghost"
              className="w-full text-red-600 dark:text-red-400 hover:text-red-700 hover:bg-red-600/10 gap-1.5"
              size="sm"
              disabled={actionLoading}
              onClick={() => { onDelete(task.id); onOpenChange(false) }}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete Task
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── New Task Dialog ────────────────────────────────────────────────

function NewTaskDialog({ open, onOpenChange, onCreate }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreate: (data: { title: string; description: string; priority: string; category: string }) => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('P2')
  const [category, setCategory] = useState('general')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) {
      toast.error('Title and description are required')
      return
    }
    setLoading(true)
    try {
      await onCreate({ title, description, priority, category })
      setTitle('')
      setDescription('')
      setPriority('P2')
      setCategory('general')
      onOpenChange(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Plus className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Create New Task
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label className="text-xs">Title <span className="text-red-500">*</span></Label>
            <Input placeholder="Task title..." value={title} onChange={(e) => setTitle(e.target.value)} className="text-xs mt-1" />
          </div>
          <div>
            <Label className="text-xs">Description <span className="text-red-500">*</span></Label>
            <Textarea placeholder="Describe the task..." value={description} onChange={(e) => setDescription(e.target.value)} className="text-xs mt-1 min-h-[80px] resize-none" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger className="mt-1 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="P0">P0 — Critical</SelectItem>
                  <SelectItem value="P1">P1 — High</SelectItem>
                  <SelectItem value="P2">P2 — Medium</SelectItem>
                  <SelectItem value="P3">P3 — Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="mt-1 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="evaluation">Evaluation</SelectItem>
                  <SelectItem value="safety_review">Safety Review</SelectItem>
                  <SelectItem value="implementation">Implementation</SelectItem>
                  <SelectItem value="research">Research</SelectItem>
                  <SelectItem value="security">Security</SelectItem>
                  <SelectItem value="governance">Governance</SelectItem>
                  <SelectItem value="benchmark">Benchmark</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter className="gap-2">
          <DialogClose asChild>
            <Button variant="outline" size="sm">Cancel</Button>
          </DialogClose>
          <Button
            className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
            size="sm"
            disabled={loading || !title.trim() || !description.trim()}
            onClick={handleSubmit}
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            Create Task
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Main Tasks Tab ─────────────────────────────────────────────────

export function TasksTab() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [newTaskOpen, setNewTaskOpen] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [mounted, setMounted] = useState(false)
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterPriority, setFilterPriority] = useState<string>('all')
  const [filterCategory, setFilterCategory] = useState<string>('all')

  // Mount detection for hydration safety
  useEffect(() => {
    setMounted(true)
  }, [])

  const fetchTasks = useCallback(async (silent = false) => {
    try {
      if (!silent) setRefreshing(true)
      const params = new URLSearchParams()
      if (filterStatus !== 'all') params.set('status', filterStatus)
      if (filterPriority !== 'all') params.set('priority', filterPriority)
      if (filterCategory !== 'all') params.set('category', filterCategory)
      const qs = params.toString()
      const url = `/api/tasks${qs ? `?${qs}` : ''}`
      const res = await globalThis.fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setTasks(json.tasks || [])
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [filterStatus, filterPriority, filterCategory])

  // Initial fetch
  useEffect(() => { fetchTasks() }, [fetchTasks])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    refreshTimerRef.current = setInterval(() => {
      fetchTasks(true)
    }, 30000)
    return () => {
      if (refreshTimerRef.current) clearInterval(refreshTimerRef.current)
    }
  }, [fetchTasks])

  const handleRefresh = useCallback(() => {
    setRefreshing(true)
    toast.promise(fetchTasks(), { loading: 'Refreshing...', success: 'Tasks refreshed', error: 'Failed' })
  }, [fetchTasks])

  const handleAutoGenerate = useCallback(async () => {
    setGenerating(true)
    try {
      const res = await globalThis.fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'auto_generate' }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Auto-generate failed')
      toast.success(`Generated ${json.generated} new tasks`)
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Auto-generate failed')
    } finally {
      setGenerating(false)
    }
  }, [fetchTasks])

  const handleStatusChange = useCallback(async (task: Task, action: string, proof?: string) => {
    try {
      const body: Record<string, unknown> = { action, id: task.id }
      if (action === 'complete' && proof) body.completionProof = proof
      if (action === 'fail' && proof) body.reason = proof
      const res = await globalThis.fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Action failed')
      toast.success(`Task ${action === 'start' ? 'started' : action === 'complete' ? 'completed' : action === 'fail' ? 'marked as failed' : action === 'reopen' ? 'reopened' : 'updated'}`)
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Action failed')
    }
  }, [fetchTasks])

  const handleDelete = useCallback(async (id: string) => {
    try {
      const res = await globalThis.fetch(`/api/tasks?id=${id}`, { method: 'DELETE' })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Delete failed')
      toast.success('Task deleted')
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed')
    }
  }, [fetchTasks])

  const handleCreate = useCallback(async (data: { title: string; description: string; priority: string; category: string }) => {
    try {
      const res = await globalThis.fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create', ...data }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Create failed')
      toast.success('Task created')
      fetchTasks()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Create failed')
    }
  }, [fetchTasks])

  // ── Stats ─────────────────────────────────────────────────────
  const stats = useMemo(() => {
    const now = new Date()
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    return {
      open: tasks.filter((t) => t.status === 'open').length,
      inProgress: tasks.filter((t) => t.status === 'in_progress').length,
      completedToday: tasks.filter((t) => t.status === 'completed' && t.completedAt && new Date(t.completedAt) >= todayStart).length,
      overdue: tasks.filter((t) => isOverdue(t)).length,
      total: tasks.length,
    }
  }, [tasks])

  // ── Loading State ─────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600 dark:text-emerald-400" />
          <p className="text-sm text-muted-foreground">Loading tasks...</p>
        </div>
      </div>
    )
  }

  // ── Error State ───────────────────────────────────────────────
  if (error && tasks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
          <p className="text-sm text-red-600 dark:text-red-400">Failed to load tasks</p>
          <p className="text-xs text-muted-foreground">{error}</p>
          <Button variant="outline" size="sm" onClick={handleRefresh}><RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Retry</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6 grid-pattern">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            <ListTodo className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            Task Management
            {lastUpdated && (
              <span className="text-[10px] font-normal text-muted-foreground ml-2 flex items-center gap-1" suppressHydrationWarning>
                <Clock className="h-3 w-3" />
                {mounted ? `Updated ${formatDate(lastUpdated.toISOString())}` : '...'}
              </span>
            )}
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">Track, manage, and validate tasks across NEXUS OS — no task completes without proof</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing} className="gap-1.5">
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button
            className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white gap-1.5"
            size="sm"
            onClick={handleAutoGenerate}
            disabled={generating}
          >
            {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
            Auto-Generate
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => setNewTaskOpen(true)}
          >
            <Plus className="h-3.5 w-3.5" /> New Task
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard label="Open Tasks" value={stats.open} icon={FolderOpen} gradient="from-blue-600/10 via-blue-600/5 to-transparent" border="border-blue-600/20" iconBg="bg-blue-600/15" iconColor="text-blue-600 dark:text-blue-400" />
        <StatCard label="In Progress" value={stats.inProgress} icon={TrendingUp} gradient="from-amber-600/10 via-amber-600/5 to-transparent" border="border-amber-600/20" iconBg="bg-amber-600/15" iconColor="text-amber-600 dark:text-amber-400" />
        <StatCard label="Completed Today" value={stats.completedToday} icon={CheckCircle2} gradient="from-emerald-600/10 via-emerald-600/5 to-transparent" border="border-emerald-600/20" iconBg="bg-emerald-600/15" iconColor="text-emerald-600 dark:text-emerald-400" />
        <StatCard label="Overdue" value={stats.overdue} icon={CalendarClock} gradient="from-red-600/10 via-red-600/5 to-transparent" border="border-red-600/20" iconBg="bg-red-600/15" iconColor="text-red-600 dark:text-red-400" />
        <StatCard label="Total" value={stats.total} icon={ListTodo} gradient="from-slate-600/10 via-slate-600/5 to-transparent" border="border-slate-600/20" iconBg="bg-slate-600/15" iconColor="text-slate-600 dark:text-slate-400" />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1.5">
          <Flag className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Filters</span>
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="h-7 w-[130px] text-[10px]"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="in_progress">In Progress</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="blocked">Blocked</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectTrigger className="h-7 w-[130px] text-[10px]"><SelectValue placeholder="Priority" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Priority</SelectItem>
            <SelectItem value="P0">P0 Critical</SelectItem>
            <SelectItem value="P1">P1 High</SelectItem>
            <SelectItem value="P2">P2 Medium</SelectItem>
            <SelectItem value="P3">P3 Low</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterCategory} onValueChange={setFilterCategory}>
          <SelectTrigger className="h-7 w-[130px] text-[10px]"><SelectValue placeholder="Category" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Category</SelectItem>
            <SelectItem value="evaluation">Evaluation</SelectItem>
            <SelectItem value="safety_review">Safety Review</SelectItem>
            <SelectItem value="implementation">Implementation</SelectItem>
            <SelectItem value="research">Research</SelectItem>
            <SelectItem value="security">Security</SelectItem>
            <SelectItem value="governance">Governance</SelectItem>
            <SelectItem value="general">General</SelectItem>
          </SelectContent>
        </Select>
        {(filterStatus !== 'all' || filterPriority !== 'all' || filterCategory !== 'all') && (
          <Button variant="ghost" size="sm" className="h-7 text-[10px] text-muted-foreground" onClick={() => { setFilterStatus('all'); setFilterPriority('all'); setFilterCategory('all') }}>
            Clear
          </Button>
        )}
        <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">{tasks.length} task{tasks.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Empty State */}
      {tasks.length === 0 && (
        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
          <CardContent className="relative p-8 text-center">
            <FileText className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
            <h3 className="text-sm font-semibold mb-1">No tasks yet</h3>
            <p className="text-xs text-muted-foreground mb-4">Auto-generate tasks based on your system state, or create one manually.</p>
            <div className="flex items-center justify-center gap-2">
              <Button
                className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white gap-1.5"
                size="sm"
                onClick={handleAutoGenerate}
                disabled={generating}
              >
                {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                Auto-Generate Tasks
              </Button>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setNewTaskOpen(true)}>
                <Plus className="h-3.5 w-3.5" /> Create Task
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Task List */}
      {tasks.length > 0 && (
        <div className="space-y-2 max-h-[calc(100vh-380px)] overflow-y-auto custom-scrollbar pr-1">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onView={(t) => { setSelectedTask(t); setDetailOpen(true) }}
              onStatusChange={handleStatusChange}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Info Footer */}
      <div className="flex items-center justify-center gap-4 text-[10px] text-muted-foreground/50 pt-2">
        <span>Completion proof required</span><span>·</span>
        <span>Priority-sorted queue</span><span>·</span>
        <span>Auto-generation from system state</span><span>·</span>
        <span>Full audit trail</span><span>·</span>
        <span suppressHydrationWarning>Auto-refresh 30s</span>
      </div>

      {/* Task Detail Dialog */}
      <TaskDetailDialog
        task={selectedTask}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        onStatusChange={handleStatusChange}
        onDelete={handleDelete}
      />

      {/* New Task Dialog */}
      <NewTaskDialog
        open={newTaskOpen}
        onOpenChange={setNewTaskOpen}
        onCreate={handleCreate}
      />
    </div>
  )
}
