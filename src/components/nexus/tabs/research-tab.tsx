'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Slider } from '@/components/ui/slider'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { BookOpen, ExternalLink, Flame, Target, Beaker, Search, X, Copy, CheckCircle2, ArrowUpRight, Plus, Play, Library, Loader2, ChevronRight, BarChart3, Zap, Timer, Pause, RotateCcw, Clock, CircleDot, AlertCircle, CalendarDays } from 'lucide-react'
import { MiniAreaChart } from '@/components/nexus/charts'
import { toast } from 'sonner'
import { useApiData } from '@/hooks/use-api-data'

interface PaperItem {
  id: string
  title: string
  relevance: number
  task: string
  deliverable?: string
  status?: string
  priority: 'P0' | 'P1' | 'P2'
  arxivId?: string
  domain?: string
}

interface ResearchApiResponse {
  papers: {
    id: string
    externalId: string | null
    type: string
    title: string
    relevanceScore: number
    priorityTier: string
    implementationTask: string | null
    deliverable: string | null
    isVetted: boolean
  }[]
  p0: {
    id: string
    externalId: string | null
    type: string
    title: string
    relevanceScore: number
    priorityTier: string
    implementationTask: string | null
    deliverable: string | null
    isVetted: boolean
  }[]
  p1: {
    id: string
    externalId: string | null
    type: string
    title: string
    relevanceScore: number
    priorityTier: string
    implementationTask: string | null
    deliverable: string | null
    isVetted: boolean
  }[]
  p2: {
    id: string
    externalId: string | null
    type: string
    title: string
    relevanceScore: number
    priorityTier: string
    implementationTask: string | null
    deliverable: string | null
    isVetted: boolean
  }[]
  total: number
}

function mapApiPaperToItem(p: ResearchApiResponse['p0'][number]): PaperItem {
  const task = p.implementationTask || 'No task assigned'
  const status = task === 'In progress' ? 'in_progress' : task === 'No task assigned' ? undefined : 'pending'
  return {
    id: p.externalId || p.id,
    title: p.title,
    relevance: p.relevanceScore,
    task,
    deliverable: p.deliverable || undefined,
    status,
    priority: p.priorityTier as 'P0' | 'P1' | 'P2',
  }
}

function getArxivUrl(id: string): string | null {
  const match = id.match(/(\d{4}\.\d{4,5})/)
  if (match) {
    return `https://arxiv.org/abs/${match[1]}`
  }
  return null
}

function getPriorityConfig(priority: PaperItem['priority']) {
  switch (priority) {
    case 'P0':
      return {
        icon: Flame,
        label: 'P0 — Implement Now',
        color: 'red',
        bgColor: 'bg-red-600/15',
        textColor: 'text-red-600 dark:text-red-400',
        borderColor: 'border-red-600/20',
        gradientFrom: 'from-red-600/10',
        gradientTo: 'to-red-600/5',
        explanation: 'P0: Critical implementation items. Must be completed in the current sprint. Directly impacts system safety or core functionality.',
      }
    case 'P1':
      return {
        icon: Target,
        label: 'P1 — Next Sprint',
        color: 'orange',
        bgColor: 'bg-orange-600/15',
        textColor: 'text-orange-600 dark:text-orange-400',
        borderColor: 'border-orange-600/20',
        gradientFrom: 'from-orange-600/10',
        gradientTo: 'to-orange-600/5',
        explanation: 'P1: High-priority items for the next sprint. Strong relevance to NEXUS architecture with clear integration paths.',
      }
    case 'P2':
      return {
        icon: Beaker,
        label: 'P2 — Research',
        color: 'emerald',
        bgColor: 'bg-emerald-600/15',
        textColor: 'text-emerald-600 dark:text-emerald-400',
        borderColor: 'border-emerald-600/20',
        gradientFrom: 'from-emerald-600/10',
        gradientTo: 'to-emerald-600/5',
        explanation: 'P2: Research-grade items. Valuable insights for future development but no immediate implementation requirement.',
      }
  }
}

const practiceSteps = [
  { step: '1', name: 'INTAKE', desc: 'Collect up to 20 links, deduplicate, prioritize by NEXUS relevance', time: '5 min' },
  { step: '2', name: 'VETTING', desc: 'Extract abstract, conclusion, score relevance 0-1, map to modules', time: '15 min' },
  { step: '3', name: 'MANIFEST', desc: 'Output papers_manifest with all structured fields', time: '5 min' },
  { step: '4', name: 'PRIORITY', desc: 'Sort by relevance, tier into P0/P1/P2 with concrete tasks', time: '5 min' },
  { step: '5', name: 'DELIVER', desc: 'Save manifest + queue, provide download, log to VAP chain', time: '2 min' },
]

const domainOptions = [
  { value: 'ai-ml', label: 'AI / Machine Learning' },
  { value: 'safety', label: 'Safety & Alignment' },
  { value: 'systems', label: 'Systems & Infrastructure' },
  { value: 'architecture', label: 'Architecture & Design' },
  { value: 'security', label: 'Security & Cryptography' },
  { value: 'nlp', label: 'NLP & Language Models' },
  { value: 'other', label: 'Other' },
]

function AddToQueueDialog({ open, onOpenChange, onAdd }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (paper: PaperItem) => void
}) {
  const [title, setTitle] = useState('')
  const [paperId, setPaperId] = useState('')
  const [arxivId, setArxivId] = useState('')
  const [taskDesc, setTaskDesc] = useState('')
  const [priority, setPriority] = useState('')
  const [domain, setDomain] = useState('')
  const [relevance, setRelevance] = useState([75])

  const handleAdd = () => {
    if (!title || !paperId || !taskDesc || !priority) {
      toast.error('Please fill in all required fields')
      return
    }
    onAdd({
      id: paperId,
      title,
      relevance: relevance[0] / 100,
      task: taskDesc,
      priority: priority as 'P0' | 'P1' | 'P2',
      status: 'pending',
      arxivId: arxivId || undefined,
      domain: domain || undefined,
    })
    setTitle('')
    setPaperId('')
    setArxivId('')
    setTaskDesc('')
    setPriority('')
    setDomain('')
    setRelevance([75])
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Add Paper to Queue
          </DialogTitle>
          <DialogDescription>Add a new research paper or repo to the NEXUS priority queue</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <label className="text-xs font-medium">Paper Title *</label>
            <Input
              placeholder="e.g. Safety Alignment in LLMs"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="h-9 text-xs"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium">Paper ID *</label>
            <Input
              placeholder="e.g. arxiv-2605.12345 or repo-name"
              value={paperId}
              onChange={(e) => setPaperId(e.target.value)}
              className="h-9 text-xs font-mono"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium">arXiv ID</label>
            <Input
              placeholder="e.g. 2605.12345"
              value={arxivId}
              onChange={(e) => setArxivId(e.target.value)}
              className="h-9 text-xs font-mono"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium">Domain</label>
            <Select value={domain} onValueChange={setDomain}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Select domain..." />
              </SelectTrigger>
              <SelectContent>
                {domainOptions.map((d) => (
                  <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium">Task Description *</label>
            <Textarea
              placeholder="Describe the integration task for NEXUS..."
              value={taskDesc}
              onChange={(e) => setTaskDesc(e.target.value)}
              className="min-h-[80px] text-xs"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium">Priority Tier *</label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder="Select priority..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="P0">
                  <span className="flex items-center gap-1.5">
                    <Flame className="h-3 w-3 text-red-600 dark:text-red-400" /> P0 — Implement Now
                  </span>
                </SelectItem>
                <SelectItem value="P1">
                  <span className="flex items-center gap-1.5">
                    <Target className="h-3 w-3 text-orange-600 dark:text-orange-400" /> P1 — Next Sprint
                  </span>
                </SelectItem>
                <SelectItem value="P2">
                  <span className="flex items-center gap-1.5">
                    <Beaker className="h-3 w-3 text-emerald-600 dark:text-emerald-400" /> P2 — Research
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium">Relevance Score</label>
              <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">{relevance[0]}%</span>
            </div>
            <Slider
              value={relevance}
              onValueChange={setRelevance}
              min={0}
              max={100}
              step={1}
              className="[&_[data-slot=slider-range]]:bg-emerald-500 [&_[data-slot=slider-thumb]]:border-emerald-500"
            />
            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" size="sm" className="h-8" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            size="sm"
            className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5"
            onClick={handleAdd}
            disabled={!title || !paperId || !taskDesc || !priority}
          >
            <Plus className="h-3 w-3" />
            Add Paper
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DailyPracticeTimerCard() {
  const TOTAL_SECONDS = 32 * 60 // 32 min total practice session
  const [elapsed, setElapsed] = useState(0)
  const [isRunning, setIsRunning] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const remaining = Math.max(TOTAL_SECONDS - elapsed, 0)
  const progressPct = Math.min((elapsed / TOTAL_SECONDS) * 100, 100)
  const isLowTime = remaining < 5 * 60 && remaining > 0

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const handleStart = useCallback(() => {
    setIsRunning(true)
  }, [])

  const handlePause = useCallback(() => {
    setIsRunning(false)
  }, [])

  const handleReset = useCallback(() => {
    setIsRunning(false)
    setElapsed(0)
  }, [])

  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => {
          if (prev >= TOTAL_SECONDS) {
            setIsRunning(false)
            toast.success('Practice session complete!', {
              description: '32 minutes elapsed — great work!',
            })
            return TOTAL_SECONDS
          }
          return prev + 1
        })
      }, 1000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isRunning])

  return (
    <Card className={`relative overflow-hidden shadow-lg hover-lift transition-colors ${isLowTime ? 'border-red-500/40 shadow-red-500/10' : 'border-emerald-600/20 shadow-emerald-600/5'}`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${isLowTime ? 'from-red-600/10 via-transparent to-red-600/5' : 'from-emerald-600/5 via-transparent to-transparent'}`} />
      <CardHeader className="relative pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Timer className={`h-4 w-4 ${isLowTime ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`} /> Daily Practice Timer
        </CardTitle>
      </CardHeader>
      <CardContent className="relative p-4 pt-0 space-y-4">
        {/* Timer Display */}
        <div className="flex items-center justify-center gap-6">
          <div className="text-center">
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Elapsed</p>
            <p className="text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{formatTime(elapsed)}</p>
          </div>
          <div className="flex flex-col items-center gap-1">
            <div className={`flex h-16 w-16 items-center justify-center rounded-full border-2 ${isLowTime ? 'border-red-500/40 bg-red-500/10' : 'border-emerald-600/30 bg-emerald-600/10'}`}>
              <Clock className={`h-7 w-7 ${isLowTime ? 'text-red-500 animate-pulse' : 'text-emerald-600 dark:text-emerald-400'}`} />
            </div>
          </div>
          <div className="text-center">
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Remaining</p>
            <p className={`text-2xl font-bold tabular-nums ${isLowTime ? 'text-red-600 dark:text-red-400' : remaining === 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-foreground'}`}>{formatTime(remaining)}</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
            <span>0:00</span>
            <span>32:00</span>
          </div>
          <div className="h-2.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-1000 ${isLowTime ? 'bg-red-500' : 'bg-emerald-500'}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-2">
          {!isRunning ? (
            <Button
              size="sm"
              className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={handleStart}
              disabled={remaining === 0}
            >
              <Play className="h-3.5 w-3.5" />
              {elapsed === 0 ? 'Start' : 'Resume'}
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5 text-xs"
              onClick={handlePause}
            >
              <Pause className="h-3.5 w-3.5" />
              Pause
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="h-8 gap-1.5 text-xs"
            onClick={handleReset}
            disabled={elapsed === 0 && !isRunning}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </Button>
        </div>

        {/* Low time warning */}
        {isLowTime && isRunning && (
          <div className="flex items-center gap-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2">
            <AlertCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0" />
            <span className="text-xs text-red-600 dark:text-red-400">Less than 5 minutes remaining!</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function ResearchTab() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPaper, setSelectedPaper] = useState<PaperItem | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [addToQueueOpen, setAddToQueueOpen] = useState(false)
  const [practiceSessionActive, setPracticeSessionActive] = useState(false)
  const [practiceStep, setPracticeStep] = useState(0)
  const [localPapers, setLocalPapers] = useState<PaperItem[]>([])

  const { data: apiData, loading, error: apiError, refetch } = useApiData<ResearchApiResponse>('/api/research', 30000)

  // Map API data to PaperItems
  const apiP0: PaperItem[] = (apiData?.p0 || []).map(mapApiPaperToItem)
  const apiP1: PaperItem[] = (apiData?.p1 || []).map(mapApiPaperToItem)
  const apiP2: PaperItem[] = (apiData?.p2 || []).map(mapApiPaperToItem)

  // Merge local papers (from "Add to Queue") with API papers
  const allP0 = [...apiP0, ...localPapers.filter(p => p.priority === 'P0')]
  const allP1 = [...apiP1, ...localPapers.filter(p => p.priority === 'P1')]
  const allP2 = [...apiP2, ...localPapers.filter(p => p.priority === 'P2')]

  const isSearchActive = searchQuery !== ''

  const filterPapers = (papers: PaperItem[]) => {
    if (!searchQuery) return papers
    const q = searchQuery.toLowerCase()
    return papers.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        p.task.toLowerCase().includes(q)
    )
  }

  const filteredP0 = filterPapers(allP0)
  const filteredP1 = filterPapers(allP1)
  const filteredP2 = filterPapers(allP2)

  const totalFiltered = filteredP0.length + filteredP1.length + filteredP2.length
  const totalAll = allP0.length + allP1.length + allP2.length

  const openPaperDialog = (paper: PaperItem) => {
    setSelectedPaper(paper)
    setDialogOpen(true)
    setCopied(false)
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('Copied to clipboard', { description: text })
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error('Failed to copy')
    }
  }

  const handleMarkInProgress = async () => {
    if (!selectedPaper) return
    try {
      const res = await fetch('/api/research', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paperId: selectedPaper.id,
          updates: { implementationTask: 'In progress' },
        }),
      })
      if (res.ok) {
        toast.success('Status updated', {
          description: `"${selectedPaper.title}" marked as In Progress`,
        })
        refetch()
      } else {
        const err = await res.json()
        toast.error('Failed to update status', { description: err.error || 'Unknown error' })
      }
    } catch {
      toast.error('Failed to update status', { description: 'Network error' })
    }
  }

  const handlePriorityChange = async (paperId: string, newTier: 'P0' | 'P1' | 'P2') => {
    try {
      const res = await fetch('/api/research', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paperId,
          updates: { priorityTier: newTier },
        }),
      })
      if (res.ok) {
        toast.success('Priority updated', {
          description: `Paper moved to ${newTier} queue`,
        })
        refetch()
      } else {
        const err = await res.json()
        toast.error('Failed to update priority', { description: err.error || 'Unknown error' })
      }
    } catch {
      toast.error('Failed to update priority', { description: 'Network error' })
    }
  }

  const handleAddPaper = (paper: PaperItem) => {
    setLocalPapers((prev) => [...prev, paper])
    toast.success('Paper added to queue', {
      description: `"${paper.title}" → ${paper.priority} queue`,
    })
  }

  const handleStartPracticeSession = () => {
    setPracticeSessionActive(true)
    setPracticeStep(0)
    toast.success('Practice session started', {
      description: 'INTAKE phase — collecting links...',
      duration: 3000,
    })
    // Simulate progression through steps
    const stepDurations = [5000, 15000, 5000, 5000, 2000]
    let elapsed = 0
    stepDurations.forEach((dur, i) => {
      elapsed += dur
      setTimeout(() => {
        if (i < 4) {
          setPracticeStep(i + 1)
          const stepNames = ['INTAKE', 'VETTING', 'MANIFEST', 'PRIORITY', 'DELIVER']
          toast.info(`${stepNames[i + 1]} phase started`, { duration: 2000 })
        } else {
          setPracticeSessionActive(false)
          toast.success('Practice session complete', {
            description: 'Manifest saved to VAP chain',
          })
        }
      }, elapsed)
    })
  }

  return (
    <div className="space-y-6 p-6 grid-pattern-animated animate-fade-in">
      {/* Loading state with shimmer skeletons */}
      {loading && !apiData && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 animate-spin" />
            <span className="text-sm text-muted-foreground">Loading research data...</span>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="relative overflow-hidden">
                <CardContent className="relative p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="h-3 w-20 shimmer-skeleton" />
                      <div className="mt-2 h-8 w-16 shimmer-skeleton" />
                      <div className="mt-1 h-3 w-24 shimmer-skeleton" />
                    </div>
                    <div className="h-11 w-11 shimmer-skeleton rounded-xl" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="relative overflow-hidden">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="h-8 w-8 shimmer-skeleton rounded-md" />
                    <div className="flex-1">
                      <div className="h-3 w-48 shimmer-skeleton" />
                      <div className="mt-2 h-4 w-72 shimmer-skeleton" />
                      <div className="mt-2 h-2 w-full shimmer-skeleton" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Search Bar + Add Button */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search papers by title, ID, or task..."
            className="h-9 pl-8 pr-8 text-xs rounded-lg transition-colors hover:border-emerald-600/30 focus:border-emerald-600/50 focus-ring-enhanced"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {isSearchActive && (
          <span className="text-xs text-muted-foreground whitespace-nowrap">
            {totalFiltered} of {totalAll} results found
          </span>
        )}
        <Button
          size="sm"
          className="h-9 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white ml-auto btn-press focus-ring-enhanced"
          onClick={() => setAddToQueueOpen(true)}
        >
          <Plus className="h-3.5 w-3.5" />
          Add to Queue
        </Button>
      </div>

      {/* Stats — Gradient Cards with Icon Badges + Hover Lift + Glow */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden border-red-600/20 hover-lift priority-p0-glow">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">P0 — Implement Now</p>
                <p className="mt-1 text-3xl font-bold text-red-600 dark:text-red-400 tabular-nums animate-count-up">{filteredP0.length}</p>
                <p className="text-[10px] text-muted-foreground">critical items</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10 status-glow-red">
                <Flame className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-orange-600/20 hover-lift priority-p1-glow">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">P1 — Next Sprint</p>
                <p className="mt-1 text-3xl font-bold text-orange-600 dark:text-orange-400 tabular-nums animate-count-up">{filteredP1.length}</p>
                <p className="text-[10px] text-muted-foreground">high priority</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10 status-glow-orange">
                <Target className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">P2 — Research</p>
                <p className="mt-1 text-3xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums animate-count-up">{filteredP2.length}</p>
                <p className="text-[10px] text-muted-foreground">research grade</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10 status-glow-green">
                <Beaker className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Vetted</p>
                <p className="mt-1 text-3xl font-bold tabular-nums animate-count-up">{totalFiltered}</p>
                <p className="text-[10px] text-muted-foreground">papers + repos</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10 status-glow-blue">
                <Library className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Progress Indicator */}
      <div className="relative overflow-hidden rounded-xl">
        <div className="absolute inset-0 rounded-xl p-[1.5px]" style={{ background: 'linear-gradient(90deg, #34d399, #60a5fa, #a78bfa, #fb923c, #34d399)', backgroundSize: '300% 100%', animation: 'gradientBorder 4s linear infinite' }}>
          <div className="h-full w-full rounded-xl bg-card" />
        </div>
      <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5 hover-lift">
        <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
        <CardHeader className="relative pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Research Pipeline
          </CardTitle>
        </CardHeader>
        <CardContent className="relative p-4 pt-0">
          <div className="flex items-center gap-1">
            {[
              { label: 'Intake', count: Math.min(totalAll + 4, 24), color: 'emerald', icon: BookOpen },
              { label: 'Vetting', count: Math.max(totalAll - 2, 3), color: 'blue', icon: Search, vetting: true },
              { label: 'Manifest', count: totalAll, color: 'purple', icon: Library },
              { label: 'Priority', count: totalAll, color: 'orange', icon: Target },
              { label: 'Delivered', count: filteredP0.length + filteredP1.filter(p => p.status === 'in_progress').length, color: 'emerald', icon: CheckCircle2 },
            ].map((step, i) => (
              <div key={step.label} className="flex items-center flex-1 pipeline-step-animate" style={{ animationDelay: `${i * 100}ms` }}>
                <div className="flex-1">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <step.icon className={`h-3 w-3 ${
                      step.color === 'emerald' ? 'text-emerald-600 dark:text-emerald-400' :
                      step.color === 'blue' ? 'text-blue-600 dark:text-blue-400' :
                      step.color === 'purple' ? 'text-purple-600 dark:text-purple-400' :
                      'text-orange-600 dark:text-orange-400'
                    } ${'vetting' in step && step.vetting ? 'vetting-indicator' : ''}`} />
                    <span className="text-[10px] font-medium">{step.label}</span>
                    {'vetting' in step && step.vetting && (
                      <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
                    )}
                    <span className="text-[9px] text-muted-foreground tabular-nums ml-auto">{step.count}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full relevance-bar-animate ${
                        step.color === 'emerald' ? 'bg-emerald-500' :
                        step.color === 'blue' ? 'bg-blue-500' :
                        step.color === 'purple' ? 'bg-purple-500' :
                        'bg-orange-500'
                      }`}
                      style={{ width: `${Math.min((step.count / (totalAll || 1)) * 100, 100)}%` }}
                    />
                  </div>
                </div>
                {i < 4 && (
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50 mx-1 shrink-0" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      </div>

      {/* Research Progress Dashboard */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Research Progress Dashboard
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0 space-y-4">
            {(() => {
              const allPapers = [...allP0, ...allP1, ...allP2]
              const notStarted = allPapers.filter(p => !p.status || p.status === 'pending').length
              const inProgress = allPapers.filter(p => p.status === 'in_progress').length
              const completed = allPapers.filter(p => p.status === 'completed').length
              const blocked = allPapers.filter(p => p.status === 'blocked').length
              const total = allPapers.length || 1
              const completionPct = Math.round((completed / total) * 100)

              // Summary stats row
              const summaryStats = [
                { label: 'Total', count: allPapers.length, color: 'text-foreground' },
                { label: 'Completed', count: completed, color: 'text-emerald-600 dark:text-emerald-400' },
                { label: 'In Progress', count: inProgress, color: 'text-blue-600 dark:text-blue-400' },
                { label: 'Queued', count: notStarted, color: 'text-yellow-600 dark:text-yellow-400' },
              ]

              const statuses = [
                { label: 'Not Started', count: notStarted, color: 'bg-zinc-400', textColor: 'text-zinc-500 dark:text-zinc-400', pct: Math.round((notStarted / total) * 100) },
                { label: 'In Progress', count: inProgress, color: 'bg-blue-500', textColor: 'text-blue-600 dark:text-blue-400', pct: Math.round((inProgress / total) * 100) },
                { label: 'Completed', count: completed, color: 'bg-emerald-500', textColor: 'text-emerald-600 dark:text-emerald-400', pct: Math.round((completed / total) * 100) },
                { label: 'Blocked', count: blocked, color: 'bg-red-500', textColor: 'text-red-600 dark:text-red-400', pct: Math.round((blocked / total) * 100) },
              ]

              return (
                <>
                  {/* Summary stats */}
                  <div className="grid grid-cols-4 gap-2">
                    {summaryStats.map((s) => (
                      <div key={s.label} className="rounded-lg bg-accent/30 p-2 text-center">
                        <p className={`text-xl font-bold tabular-nums ${s.color}`}>{s.count}</p>
                        <p className="text-[9px] text-muted-foreground">{s.label}</p>
                      </div>
                    ))}
                  </div>
                  {/* Circular progress indicator */}
                  <div className="flex items-center gap-4">
                    <div className="relative flex h-20 w-20 shrink-0 items-center justify-center">
                      <svg className="h-20 w-20 -rotate-90" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="34" fill="none" stroke="hsl(var(--muted))" strokeWidth="6" />
                        <circle cx="40" cy="40" r="34" fill="none" stroke="#34d399" strokeWidth="6" strokeLinecap="round" strokeDasharray={`${completionPct * 2.136} ${213.6 - completionPct * 2.136}`} className="transition-all duration-700" />
                      </svg>
                      <span className="absolute text-lg font-bold tabular-nums text-emerald-600 dark:text-emerald-400">{completionPct}%</span>
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs text-muted-foreground">Est. completion</span>
                      </div>
                      <p className="text-sm font-medium">~2 weeks at current pace</p>
                      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                        <div className="h-full rounded-full bg-emerald-500 transition-all duration-700" style={{ width: `${completionPct}%` }} />
                      </div>
                    </div>
                  </div>
                  {/* Status breakdown bars */}
                  {statuses.map((s) => (
                    <div key={s.label} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`h-2 w-2 rounded-full ${s.color}`} />
                          <span className="text-xs font-medium">{s.label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold tabular-nums">{s.count}</span>
                          <span className={`text-[10px] tabular-nums ${s.textColor}`}>({s.pct}%)</span>
                        </div>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${s.color}`}
                          style={{ width: `${s.pct}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </>
              )
            })()}
          </CardContent>
        </Card>

        <DailyPracticeTimerCard />
      </div>

      <Tabs defaultValue="p0" className="space-y-4">
        <TabsList>
          <TabsTrigger value="p0">P0 — Now</TabsTrigger>
          <TabsTrigger value="p1">P1 — Next</TabsTrigger>
          <TabsTrigger value="p2">P2 — Research</TabsTrigger>
          <TabsTrigger value="practice">Daily Practice</TabsTrigger>
        </TabsList>

        {/* P0 */}
        <TabsContent value="p0">
          <div className="space-y-3">
            {filteredP0.length > 0 ? (
              filteredP0.map((item) => {
                const config = getPriorityConfig(item.priority)
                return (
                  <Card
                    key={item.id}
                    className="hover:border-red-600/30 transition-all cursor-pointer hover-lift border-l-4 border-l-red-500/60 btn-press shadow-sm shadow-red-600/5"
                    onClick={() => openPaperDialog(item)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-600/15 status-glow-red priority-p0-glow">
                          <Flame className="h-4 w-4 text-red-600 dark:text-red-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                            <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px] badge-glow-red">
                              Relevance: {(item.relevance * 100).toFixed(0)}%
                            </Badge>
                            {item.status === 'in_progress' && (
                              <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">IN PROGRESS</Badge>
                            )}
                            {item.status === 'pending' && (
                              <Badge className="bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px] animate-pulse">NEW</Badge>
                            )}
                          </div>
                          <p className="mt-1 text-sm font-medium">{item.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                          {item.deliverable && (
                            <div className="mt-2 flex items-center gap-2">
                              <code className="text-[10px] rounded bg-accent px-1.5 py-0.5">{item.deliverable}</code>
                            </div>
                          )}
                          {/* Relevance Score Visual Bar with color coding */}
                          <div className="mt-2 flex items-center gap-2">
                            <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                              <div
                                className={`h-full rounded-full relevance-bar-animate ${
                                  item.relevance >= 0.8 ? 'bg-red-500' :
                                  item.relevance >= 0.6 ? 'bg-orange-500' :
                                  'bg-emerald-500'
                                }`}
                                style={{ width: `${item.relevance * 100}%` }}
                              />
                            </div>
                            <span className="text-[9px] text-muted-foreground tabular-nums">{(item.relevance * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })
            ) : (
              <Card>
                <CardContent className="p-8 text-center text-sm text-muted-foreground">
                  {loading ? 'Loading P0 papers...' : 'No P0 papers match your search'}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* P1 */}
        <TabsContent value="p1">
          <div className="space-y-3">
            {filteredP1.length > 0 ? (
              filteredP1.map((item) => (
                <Card
                  key={item.id}
                  className="hover:border-orange-600/30 transition-all cursor-pointer hover-lift border-l-4 border-l-orange-500/60 btn-press shadow-sm shadow-orange-600/5"
                  onClick={() => openPaperDialog(item)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-orange-600/15 status-glow-orange priority-p1-glow">
                        <Target className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                          <Badge className="bg-orange-600/15 text-orange-600 dark:text-orange-400 border-0 text-[9px] status-glow-orange">
                            Relevance: {(item.relevance * 100).toFixed(0)}%
                          </Badge>
                          {item.status === 'in_progress' && (
                            <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">IN PROGRESS</Badge>
                          )}
                        </div>
                        <p className="mt-1 text-sm font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                        {/* Relevance Score Visual Bar with color coding */}
                        <div className="mt-2 flex items-center gap-2">
                          <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                            <div
                              className={`h-full rounded-full relevance-bar-animate ${
                                item.relevance >= 0.8 ? 'bg-orange-500' :
                                item.relevance >= 0.6 ? 'bg-yellow-500' :
                                'bg-emerald-500'
                              }`}
                              style={{ width: `${item.relevance * 100}%` }}
                            />
                          </div>
                          <span className="text-[9px] text-muted-foreground tabular-nums">{(item.relevance * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card>
                <CardContent className="p-8 text-center text-sm text-muted-foreground">
                  {loading ? 'Loading P1 papers...' : 'No P1 papers match your search'}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* P2 */}
        <TabsContent value="p2">
          <div className="space-y-3">
            {filteredP2.length > 0 ? (
              filteredP2.map((item) => (
                <Card
                  key={item.id}
                  className="hover:border-emerald-600/30 transition-all cursor-pointer hover-lift border-l-4 border-l-emerald-500/60 btn-press shadow-sm shadow-emerald-600/5"
                  onClick={() => openPaperDialog(item)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-600/15 status-glow-green">
                        <Beaker className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                          <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px] badge-glow-emerald">
                            Relevance: {(item.relevance * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="mt-1 text-sm font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                        {/* Relevance Score Visual Bar with color coding */}
                        <div className="mt-2 flex items-center gap-2">
                          <div className="h-1.5 flex-1 rounded-full bg-muted overflow-hidden">
                            <div
                              className="h-full rounded-full relevance-bar-animate bg-emerald-500"
                              style={{ width: `${item.relevance * 100}%` }}
                            />
                          </div>
                          <span className="text-[9px] text-muted-foreground tabular-nums">{(item.relevance * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card>
                <CardContent className="p-8 text-center text-sm text-muted-foreground">
                  {loading ? 'Loading P2 papers...' : 'No P2 papers match your search'}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Daily Practice — Enhanced */}
        <TabsContent value="practice">
          <Card className="relative overflow-hidden border-emerald-600/20 nexus-gradient-border">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> Daily Research Practice Template
              </CardTitle>
            </CardHeader>
            <CardContent className="relative p-4 pt-0 space-y-4">
              {/* Steps with progression lines and gradient colors */}
              <div className="relative">
                {/* Connector line behind steps */}
                <div className="absolute top-5 left-5 right-5 h-0.5 bg-gradient-to-r from-emerald-300/30 via-emerald-500/40 to-emerald-700/50 hidden md:block" />

                <div className="grid gap-3 md:grid-cols-5 relative">
                  {practiceSteps.map((s, i) => {
                    const emeraldLevels = [
                      'bg-emerald-300/20 text-emerald-600 dark:text-emerald-300 border-emerald-300/30',
                      'bg-emerald-400/20 text-emerald-600 dark:text-emerald-400 border-emerald-400/30',
                      'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
                      'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-emerald-600/30',
                      'bg-emerald-700/20 text-emerald-600 dark:text-emerald-400 border-emerald-700/30',
                    ]
                    const stepBadgeBg = [
                      'bg-emerald-300/20 text-emerald-600 dark:text-emerald-300',
                      'bg-emerald-400/20 text-emerald-600 dark:text-emerald-400',
                      'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400',
                      'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400',
                      'bg-emerald-700/20 text-emerald-600 dark:text-emerald-400',
                    ]
                    const isActive = practiceSessionActive && i === practiceStep
                    return (
                      <div
                        key={s.step}
                        className={`rounded-lg border p-3 transition-all duration-200 hover:shadow-md hover:scale-[1.02] hover-pulse ${emeraldLevels[i]} ${isActive ? 'ring-2 ring-emerald-400 shadow-lg shadow-emerald-400/20' : ''}`}
                      >
                        <div className="flex items-center gap-2">
                          <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${stepBadgeBg[i]}`}>
                            {s.step}
                          </span>
                          <span className="text-xs font-semibold">{s.name}</span>
                        </div>
                        <p className="mt-1.5 text-[11px] text-muted-foreground">{s.desc}</p>
                        <p className="mt-1 text-[10px] text-muted-foreground/60">~{s.time}</p>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Start Practice Session Button */}
              <div className="flex justify-center pt-2">
                <Button
                  className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-600/20 btn-press focus-ring-enhanced"
                  onClick={handleStartPracticeSession}
                  disabled={practiceSessionActive}
                >
                  <Zap className="h-4 w-4" />
                  {practiceSessionActive ? `Running: ${practiceSteps[practiceStep]?.name}...` : 'Start Practice Session'}
                </Button>
              </div>

              <div className="rounded-md border border-border/50 bg-accent/30 p-3">
                <p className="text-xs font-medium">Quality Gates</p>
                <ul className="mt-1 space-y-1 text-[11px] text-muted-foreground">
                  <li>• No dumping: every entry must have abstract + conclusion vetted</li>
                  <li>• No hallucination: cite source lines for key numbers</li>
                  <li>• Max 20 items per run to maintain depth</li>
                  <li>• Run 1-2x daily as requested</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add to Queue Dialog */}
      <AddToQueueDialog
        open={addToQueueOpen}
        onOpenChange={setAddToQueueOpen}
        onAdd={handleAddPaper}
      />

      {/* Paper Detail Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        {selectedPaper && (() => {
          const config = getPriorityConfig(selectedPaper.priority)
          const arxivUrl = getArxivUrl(selectedPaper.id)
          const PriorityIcon = config.icon

          return (
            <DialogContent className="max-w-lg p-0 overflow-hidden animate-scale-in">
              {/* Gradient header matching priority color */}
              <div className={`bg-gradient-to-r ${config.gradientFrom} ${config.gradientTo} p-6 border-b`}>
                <DialogHeader>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={`${config.bgColor} ${config.textColor} border-0 text-[10px]`}>
                      <PriorityIcon className="h-3 w-3 mr-1" />
                      {config.label}
                    </Badge>
                    {selectedPaper.status === 'in_progress' && (
                      <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[10px]">
                        IN PROGRESS
                      </Badge>
                    )}
                    {selectedPaper.status === 'pending' && (
                      <Badge variant="outline" className="text-[10px]">
                        PENDING
                      </Badge>
                    )}
                  </div>
                  <DialogTitle className="text-base leading-snug">
                    {selectedPaper.title}
                  </DialogTitle>
                  <DialogDescription className="text-xs font-mono mt-1">
                    {selectedPaper.id}
                  </DialogDescription>
                </DialogHeader>
              </div>

              <div className="p-6 space-y-5">
                {/* Relevance Score with Visual Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">Relevance Score</span>
                    <span className={`text-sm font-bold ${config.textColor}`}>
                      {(selectedPaper.relevance * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full relevance-bar-animate ${
                        selectedPaper.priority === 'P0' ? 'bg-red-500' :
                        selectedPaper.priority === 'P1' ? 'bg-orange-500' :
                        'bg-emerald-500'
                      }`}
                      style={{ width: `${selectedPaper.relevance * 100}%` }}
                    />
                  </div>
                </div>

                {/* Task Description */}
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-muted-foreground">Task Description</span>
                  <p className="text-sm leading-relaxed">{selectedPaper.task}</p>
                </div>

                {/* Deliverable Path */}
                {selectedPaper.deliverable && (
                  <div className="space-y-1.5">
                    <span className="text-xs font-medium text-muted-foreground">Deliverable Path</span>
                    <div className="flex items-center gap-2 rounded-md bg-accent/50 border border-border px-3 py-2">
                      <code className="text-xs font-mono flex-1 break-all">{selectedPaper.deliverable}</code>
                      <button
                        onClick={() => copyToClipboard(selectedPaper.deliverable!)}
                        className="shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1 rounded hover:bg-accent"
                      >
                        {copied ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Priority Tier Explanation + Priority Change */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">Priority Tier</span>
                    <Select
                      value={selectedPaper.priority}
                      onValueChange={(val) => handlePriorityChange(selectedPaper.id, val as 'P0' | 'P1' | 'P2')}
                    >
                      <SelectTrigger className="h-7 w-24 text-[10px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="P0">P0 — Now</SelectItem>
                        <SelectItem value="P1">P1 — Next</SelectItem>
                        <SelectItem value="P2">P2 — Research</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="rounded-md border border-border bg-accent/20 px-3 py-2">
                    <p className="text-xs text-muted-foreground">{config.explanation}</p>
                  </div>
                </div>

                {/* Action Buttons */}
                <DialogFooter className="gap-2 sm:gap-2 pt-2">
                  {arxivUrl && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1.5 text-xs"
                      onClick={() => window.open(arxivUrl, '_blank', 'noopener,noreferrer')}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      View on arXiv
                    </Button>
                  )}
                  <Button
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={handleMarkInProgress}
                    disabled={selectedPaper.status === 'in_progress'}
                  >
                    <ArrowUpRight className="h-3.5 w-3.5" />
                    {selectedPaper.status === 'in_progress' ? 'Already In Progress' : 'Mark as In Progress'}
                  </Button>
                </DialogFooter>
              </div>
            </DialogContent>
          )
        })()}
      </Dialog>
    </div>
  )
}
