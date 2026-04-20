'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { BookOpen, ExternalLink, Flame, Target, Beaker, Search, X, Copy, CheckCircle2, ArrowUpRight } from 'lucide-react'
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

const allPapers = [...p0Items, ...p1Items, ...p2Items]

function getArxivUrl(id: string): string | null {
  // Match arXiv paper ID pattern like 2603.23509, 2405.20947 etc.
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

export function ResearchTab() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPaper, setSelectedPaper] = useState<PaperItem | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [copied, setCopied] = useState(false)

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

  const filteredP0 = filterPapers(p0Items)
  const filteredP1 = filterPapers(p1Items)
  const filteredP2 = filterPapers(p2Items)

  const totalFiltered = filteredP0.length + filteredP1.length + filteredP2.length
  const totalAll = allPapers.length

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

  return (
    <div className="space-y-6 p-6">
      {/* Search Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search papers by title, ID, or task..."
            className="h-9 pl-8 pr-8 text-xs rounded-lg"
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
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-red-600/20 bg-red-600/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-red-400" />
              <p className="text-xs text-muted-foreground">P0 — Implement Now</p>
            </div>
            <p className="text-2xl font-bold text-red-400">{filteredP0.length}</p>
          </CardContent>
        </Card>
        <Card className="border-orange-600/20 bg-orange-600/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-orange-400" />
              <p className="text-xs text-muted-foreground">P1 — Next Sprint</p>
            </div>
            <p className="text-2xl font-bold text-orange-400">{filteredP1.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">P2 — Research</p>
            </div>
            <p className="text-2xl font-bold">{filteredP2.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Vetted</p>
            <p className="text-2xl font-bold">{totalFiltered}</p>
            <p className="text-[10px] text-muted-foreground">papers + repos</p>
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
                    className="hover:border-red-600/20 transition-colors cursor-pointer"
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
                          </div>
                          <p className="mt-1 text-sm font-medium">{item.title}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                          {item.deliverable && (
                            <div className="mt-2 flex items-center gap-2">
                              <code className="text-[10px] rounded bg-accent px-1.5 py-0.5">{item.deliverable}</code>
                            </div>
                          )}
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
                  className="hover:border-orange-600/20 transition-colors cursor-pointer"
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
                  className="hover:border-emerald-600/20 transition-colors cursor-pointer"
                  onClick={() => openPaperDialog(item)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                        <Beaker className="h-4 w-4 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                          <Badge variant="outline" className="text-[9px]">
                            {(item.relevance * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <p className="mt-1 text-sm font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
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

        {/* Daily Practice */}
        <TabsContent value="practice">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <BookOpen className="h-4 w-4" /> Daily Research Practice Template
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0 space-y-4">
              <div className="grid gap-3 md:grid-cols-5">
                {[
                  { step: '1', name: 'INTAKE', desc: 'Collect up to 20 links, deduplicate, prioritize by NEXUS relevance', time: '5 min' },
                  { step: '2', name: 'VETTING', desc: 'Extract abstract, conclusion, score relevance 0-1, map to modules', time: '15 min' },
                  { step: '3', name: 'MANIFEST', desc: 'Output papers_manifest with all structured fields', time: '5 min' },
                  { step: '4', name: 'PRIORITY', desc: 'Sort by relevance, tier into P0/P1/P2 with concrete tasks', time: '5 min' },
                  { step: '5', name: 'DELIVER', desc: 'Save manifest + queue, provide download, log to VAP chain', time: '2 min' },
                ].map((s) => (
                  <div key={s.step} className="rounded-md border border-border p-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-600/15 text-xs font-bold text-emerald-400">{s.step}</span>
                      <span className="text-xs font-semibold">{s.name}</span>
                    </div>
                    <p className="mt-1.5 text-[11px] text-muted-foreground">{s.desc}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground/60">~{s.time}</p>
                  </div>
                ))}
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
