'use client'

import { useState } from 'react'
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
import { BookOpen, ExternalLink, Flame, Target, Beaker, Search, X, Copy, CheckCircle2, ArrowUpRight, Plus, Play, Library } from 'lucide-react'
import { toast } from 'sonner'

interface PaperItem {
  id: string
  title: string
  relevance: number
  task: string
  deliverable?: string
  status?: string
  priority: 'P0' | 'P1' | 'P2'
}

const p0Items: PaperItem[] = [
  { id: 'isc-bench-2603.23509', title: 'Internal Safety Collapse in Frontier LLMs', relevance: 0.97, task: 'Import 53 TVD scenarios into stresslab/templates/. Create validator that checks if harmful content is structurally required.', deliverable: 'stresslab/isc_runner.py', status: 'in_progress', priority: 'P0' },
  { id: 'or-bench-2405.20947', title: 'OR-Bench: Over-Refusal Benchmark', relevance: 0.95, task: 'Load 1k hard prompts. Measure over-refusal rate per lane. Update trust_scoring.py lane thresholds.', deliverable: 'evals/overrefusal/or_bench_eval.py', status: 'pending', priority: 'P0' },
  { id: 'dual-pool-2502.00409', title: 'Dual-Pool Token-Budget Routing', relevance: 0.93, task: 'Implement bytes-to-token EMA estimator in gmr/scheduler.py. Split GMR pools into short (<4k) and long context.', deliverable: 'gmr/scheduler.py', status: 'pending', priority: 'P0' },
  { id: 'deer-flow', title: 'bytedance/deer-flow', relevance: 0.93, task: 'Port sub-agent harness pattern: lead agent + parallel workers with isolated sandboxes.', deliverable: 'swarm/foreman.py refactor', status: 'pending', priority: 'P0' },
]

const p1Items: PaperItem[] = [
  { id: 'routing-survey-2604.08075', title: 'Doing More with Less', relevance: 0.94, task: 'Implement cost-performance scoring function. Add pre-generation router in GMR.', priority: 'P1' },
  { id: 'dynamic-routing-2603.04445', title: 'Dynamic Model Routing and Cascading', relevance: 0.92, task: 'Build 3-dimension router (when/what/how). Add uncertainty-based fallback.', priority: 'P1' },
  { id: 'tale-2603.08425', title: 'Token-Budget-Aware LLM Reasoning', relevance: 0.92, task: 'Add per-query token budget estimator to TokenGuard. Enforce via check_and_reserve().', priority: 'P1' },
  { id: 'infiagent-2412.18547', title: 'InfiAgent', relevance: 0.92, task: 'Prototype file-centric state in vault/manager.py. Replace prompt-as-memory with snapshot reconstruction.', priority: 'P1' },
  { id: 'rigorllm-2403.13031', title: 'RigorLLM', relevance: 0.87, task: 'Add fusion guardrail (KNN + LLM) to governor/moderation.py for jailbreak resilience.', priority: 'P1' },
  { id: 'shieldgemma-2407.21772', title: 'ShieldGemma', relevance: 0.9, task: 'Integrate ShieldGemma-2B as fast moderation adapter. Benchmark vs current.', priority: 'P1' },
]

const p2Items: PaperItem[] = [
  { id: 'guardt2i-2403.01446', title: 'GuardT2I', relevance: 0.84, task: 'Evaluate generative moderation for multimodal agents', priority: 'P2' },
  { id: 'aegis-2404.05993', title: 'AEGIS', relevance: 0.88, task: 'Study ensemble safety experts for online adaptation', priority: 'P2' },
  { id: 'identity-suppression-2409.13725', title: 'Identity Suppression in AI Moderation', relevance: 0.92, task: 'Audit current moderation for identity bias', priority: 'P2' },
  { id: 'last30days-skill', title: 'last30days-skill', relevance: 0.92, task: 'Integrate as NEXUS world-awareness skill', priority: 'P2' },
  { id: 'superpowers', title: 'superpowers (TDD)', relevance: 0.88, task: 'Adopt TDD workflow for agent-generated code', priority: 'P2' },
  { id: 'ironengine-2601.03204', title: 'IronEngine', relevance: 0.88, task: 'Review three-phase pipeline for planner-reviewer pattern', priority: 'P2' },
]

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
        textColor: 'text-red-400',
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
        textColor: 'text-orange-400',
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
        textColor: 'text-emerald-400',
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

function AddToQueueDialog({ open, onOpenChange, onAdd }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdd: (paper: PaperItem) => void
}) {
  const [title, setTitle] = useState('')
  const [paperId, setPaperId] = useState('')
  const [taskDesc, setTaskDesc] = useState('')
  const [priority, setPriority] = useState('')
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
    })
    setTitle('')
    setPaperId('')
    setTaskDesc('')
    setPriority('')
    setRelevance([75])
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-emerald-400" />
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
                    <Flame className="h-3 w-3 text-red-400" /> P0 — Implement Now
                  </span>
                </SelectItem>
                <SelectItem value="P1">
                  <span className="flex items-center gap-1.5">
                    <Target className="h-3 w-3 text-orange-400" /> P1 — Next Sprint
                  </span>
                </SelectItem>
                <SelectItem value="P2">
                  <span className="flex items-center gap-1.5">
                    <Beaker className="h-3 w-3 text-emerald-400" /> P2 — Research
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium">Relevance Score</label>
              <span className="text-xs font-bold text-emerald-400 tabular-nums">{relevance[0]}%</span>
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

export function ResearchTab() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPaper, setSelectedPaper] = useState<PaperItem | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [addToQueueOpen, setAddToQueueOpen] = useState(false)
  const [localP0, setLocalP0] = useState<PaperItem[]>(p0Items)
  const [localP1, setLocalP1] = useState<PaperItem[]>(p1Items)
  const [localP2, setLocalP2] = useState<PaperItem[]>(p2Items)

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

  const filteredP0 = filterPapers(localP0)
  const filteredP1 = filterPapers(localP1)
  const filteredP2 = filterPapers(localP2)

  const totalFiltered = filteredP0.length + filteredP1.length + filteredP2.length
  const totalAll = localP0.length + localP1.length + localP2.length

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

  const handleMarkInProgress = () => {
    if (!selectedPaper) return
    toast.success('Status updated', {
      description: `"${selectedPaper.title}" marked as In Progress`,
    })
  }

  const handleAddPaper = (paper: PaperItem) => {
    switch (paper.priority) {
      case 'P0':
        setLocalP0((prev) => [...prev, paper])
        break
      case 'P1':
        setLocalP1((prev) => [...prev, paper])
        break
      case 'P2':
        setLocalP2((prev) => [...prev, paper])
        break
    }
    toast.success('Paper added to queue', {
      description: `"${paper.title}" → ${paper.priority} queue`,
    })
  }

  return (
    <div className="space-y-6 p-6 grid-pattern animate-fade-in">
      {/* Search Bar + Add Button */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search papers by title, ID, or task..."
            className="h-9 pl-8 pr-8 text-xs rounded-lg transition-colors hover:border-emerald-600/30 focus:border-emerald-600/50"
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
          className="h-9 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white ml-auto"
          onClick={() => setAddToQueueOpen(true)}
        >
          <Plus className="h-3.5 w-3.5" />
          Add to Queue
        </Button>
      </div>

      {/* Stats — Gradient Cards with Icon Badges */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="relative overflow-hidden border-red-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">P0 — Implement Now</p>
                <p className="mt-1 text-3xl font-bold text-red-400 tabular-nums">{filteredP0.length}</p>
                <p className="text-[10px] text-muted-foreground">critical items</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600/15 shadow-lg shadow-red-600/10">
                <Flame className="h-5 w-5 text-red-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-orange-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">P1 — Next Sprint</p>
                <p className="mt-1 text-3xl font-bold text-orange-400 tabular-nums">{filteredP1.length}</p>
                <p className="text-[10px] text-muted-foreground">high priority</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-600/15 shadow-lg shadow-orange-600/10">
                <Target className="h-5 w-5 text-orange-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden border-emerald-600/20">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">P2 — Research</p>
                <p className="mt-1 text-3xl font-bold text-emerald-400 tabular-nums">{filteredP2.length}</p>
                <p className="text-[10px] text-muted-foreground">research grade</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
                <Beaker className="h-5 w-5 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-blue-600/8 via-transparent to-transparent" />
          <CardContent className="relative p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Total Vetted</p>
                <p className="mt-1 text-3xl font-bold tabular-nums">{totalFiltered}</p>
                <p className="text-[10px] text-muted-foreground">papers + repos</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-600/15 shadow-lg shadow-blue-600/10">
                <Library className="h-5 w-5 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
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
                    className="hover:border-red-600/20 transition-all cursor-pointer hover-lift border-l-4 border-l-red-500/60"
                    onClick={() => openPaperDialog(item)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-600/15">
                          <Flame className="h-4 w-4 text-red-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                            <Badge className="bg-red-600/15 text-red-400 border-0 text-[9px]">
                              Relevance: {(item.relevance * 100).toFixed(0)}%
                            </Badge>
                            {item.status === 'in_progress' && (
                              <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">IN PROGRESS</Badge>
                            )}
                            {item.status === 'pending' && (
                              <Badge className="bg-yellow-500/15 text-yellow-400 border-0 text-[9px] animate-pulse">NEW</Badge>
                            )}
                          </div>
                          <p className="mt-1 text-sm font-medium">{item.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                          {item.deliverable && (
                            <div className="mt-2 flex items-center gap-2">
                              <code className="text-[10px] rounded bg-accent px-1.5 py-0.5">{item.deliverable}</code>
                            </div>
                          )}
                          {/* Relevance Score Progress Bar */}
                          <div className="mt-2 flex items-center gap-2">
                            <Progress value={item.relevance * 100} className="h-1 flex-1" />
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
                  No P0 papers match your search
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
                  className="hover:border-orange-600/20 transition-all cursor-pointer hover-lift border-l-4 border-l-orange-500/60"
                  onClick={() => openPaperDialog(item)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-orange-600/15">
                        <Target className="h-4 w-4 text-orange-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                          <Badge className="bg-orange-600/15 text-orange-400 border-0 text-[9px]">
                            Relevance: {(item.relevance * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="mt-1 text-sm font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                        {/* Relevance Score Progress Bar */}
                        <div className="mt-2 flex items-center gap-2">
                          <Progress value={item.relevance * 100} className="h-1 flex-1" />
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
                  No P1 papers match your search
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
                  className="hover:border-emerald-600/20 transition-all cursor-pointer hover-lift border-l-4 border-l-emerald-500/60"
                  onClick={() => openPaperDialog(item)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-600/15">
                        <Beaker className="h-4 w-4 text-emerald-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                          <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">
                            {(item.relevance * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="mt-1 text-sm font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                        {/* Relevance Score Progress Bar */}
                        <div className="mt-2 flex items-center gap-2">
                          <Progress value={item.relevance * 100} className="h-1 flex-1" />
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
                  No P2 papers match your search
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Daily Practice — Enhanced */}
        <TabsContent value="practice">
          <Card className="relative overflow-hidden border-emerald-600/20">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardHeader className="relative pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-emerald-400" /> Daily Research Practice Template
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
                      'bg-emerald-300/20 text-emerald-300 border-emerald-300/30',
                      'bg-emerald-400/20 text-emerald-400 border-emerald-400/30',
                      'bg-emerald-500/20 text-emerald-500 border-emerald-500/30',
                      'bg-emerald-600/20 text-emerald-500 border-emerald-600/30',
                      'bg-emerald-700/20 text-emerald-400 border-emerald-700/30',
                    ]
                    const stepBadgeBg = [
                      'bg-emerald-300/20 text-emerald-300',
                      'bg-emerald-400/20 text-emerald-400',
                      'bg-emerald-500/20 text-emerald-500',
                      'bg-emerald-600/20 text-emerald-500',
                      'bg-emerald-700/20 text-emerald-400',
                    ]
                    return (
                      <div
                        key={s.step}
                        className={`rounded-lg border p-3 transition-all duration-200 hover:shadow-md hover:scale-[1.02] hover-pulse ${emeraldLevels[i]}`}
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
                  className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg shadow-emerald-600/20"
                  onClick={() => {
                    toast.success('Practice session started', {
                      description: 'INTAKE phase — collecting links...',
                      duration: 3000,
                    })
                  }}
                >
                  <Play className="h-4 w-4" />
                  Start Practice Session
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
            <DialogContent className="max-w-lg p-0 overflow-hidden">
              {/* Gradient header matching priority color */}
              <div className={`bg-gradient-to-r ${config.gradientFrom} ${config.gradientTo} p-6 border-b`}>
                <DialogHeader>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={`${config.bgColor} ${config.textColor} border-0 text-[10px]`}>
                      <PriorityIcon className="h-3 w-3 mr-1" />
                      {config.label}
                    </Badge>
                    {selectedPaper.status === 'in_progress' && (
                      <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[10px]">
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
                {/* Relevance Score with Progress Bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">Relevance Score</span>
                    <span className={`text-sm font-bold ${config.textColor}`}>
                      {(selectedPaper.relevance * 100).toFixed(0)}%
                    </span>
                  </div>
                  <Progress value={selectedPaper.relevance * 100} className="h-2" />
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
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {/* Priority Tier Explanation */}
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-muted-foreground">Priority Tier</span>
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
                  >
                    <ArrowUpRight className="h-3.5 w-3.5" />
                    Mark as In Progress
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
