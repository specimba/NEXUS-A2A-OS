'use client'

import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts'
import {
  BookOpen,
  FileSearch,
  CheckCircle2,
  Clock,
  Star,
  ExternalLink,
  Filter,
  TrendingUp,
  Search,
  Loader2,
  Sparkles,
  Bot,
  Send,
  X,
  Brain,
  Shield,
  Cpu,
  Database,
  MessageSquare,
  ChevronRight,
  Quote,
  Eye,
  Zap,
  BarChart3,
  Activity,
  AlertTriangle,
  ChevronDown,
  Calendar,
  Hash,
  XCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'

// ─── Types ─────────────────────────────────────────────────────────────────

interface Paper {
  id: string
  title: string
  authors: string[]
  abstract: string
  category: string
  priority: string
  relevance: number
  novelty: number
  status: 'vetted' | 'vetting' | 'queued'
  year: number | null
  citations: number
  pdfUrl?: string
  source?: string
  researchRole?: string
  projectFit?: string
  dgScore?: number
}

interface AISuggestion {
  title: string
  relevanceReason: string
  suggestedCategory: string
  relevanceScore: number
}

interface SearchResult {
  papers: Paper[]
  aiSuggestions: AISuggestion[]
  query: string
  totalFound: number
  sources: { database: number; arxiv: number; aiSuggestions: number }
}

interface AnalysisResult {
  summary: string
  critique: string
  relevance: string
  concepts: string[]
  implementationTask: string
  priorityTier: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

// ─── Enhanced Mock Data (fallback when API is unavailable) ─────────────────

const mockPapers: Paper[] = [
  {
    id: 'mock-1',
    title: 'OR-Bench: Over-Refusal Benchmark for LLM Safety Evaluation',
    authors: ['Cui et al.'],
    abstract: 'We propose OR-Bench, a comprehensive benchmark for evaluating over-refusal behavior in large language models. Our benchmark includes 1,000+ test cases across multiple safety categories, measuring both under-refusal and over-refusal rates.',
    category: 'Safety',
    priority: 'P1',
    relevance: 95,
    novelty: 88,
    status: 'vetted',
    year: 2024,
    citations: 47,
    pdfUrl: 'https://arxiv.org/abs/2401.12345',
    researchRole: 'safety',
    dgScore: 12,
  },
  {
    id: 'mock-2',
    title: 'Chain-of-Thought Hub: Reasoning Evaluation Framework',
    authors: ['Li et al.'],
    abstract: 'Chain-of-Thought Hub provides a systematic framework for evaluating the reasoning capabilities of large language models. We benchmark 20+ models across mathematical, logical, and commonsense reasoning tasks.',
    category: 'Evaluation',
    priority: 'P1',
    relevance: 92,
    novelty: 76,
    status: 'vetted',
    year: 2024,
    citations: 83,
    pdfUrl: 'https://arxiv.org/abs/2401.12346',
    researchRole: 'evaluation',
    dgScore: 11,
  },
  {
    id: 'mock-3',
    title: 'AgentBench: Multi-dimensional LLM Agent Evaluation',
    authors: ['Liu et al.'],
    abstract: 'AgentBench evaluates LLM-based agents across 8 distinct environments including coding, web browsing, and database management. Our results reveal significant gaps between model capabilities and real-world agent performance.',
    category: 'Agents',
    priority: 'P2',
    relevance: 87,
    novelty: 82,
    status: 'vetting',
    year: 2024,
    citations: 124,
    pdfUrl: 'https://arxiv.org/abs/2401.12347',
    researchRole: 'benchmark',
    dgScore: 9,
  },
  {
    id: 'mock-4',
    title: 'Self-RAG: Learning to Retrieve and Generate Through Self-Reflection',
    authors: ['Asai et al.'],
    abstract: 'Self-RAG introduces a framework where language models learn to retrieve, generate, and critique through self-reflection. Our approach achieves state-of-the-art results on multiple QA and reasoning benchmarks.',
    category: 'RAG',
    priority: 'P2',
    relevance: 84,
    novelty: 90,
    status: 'vetting',
    year: 2024,
    citations: 215,
    pdfUrl: 'https://arxiv.org/abs/2401.12348',
    researchRole: 'memory',
    dgScore: 10,
  },
  {
    id: 'mock-5',
    title: 'Mixture-of-Agents Enhances Large Language Model Performance',
    authors: ['Wang et al.'],
    abstract: 'We propose Mixture-of-Agents (MoA), a novel architecture that leverages multiple LLM agents collaboratively to achieve superior performance. MoA outperforms single-model approaches on 6 benchmarks.',
    category: 'Architecture',
    priority: 'P2',
    relevance: 81,
    novelty: 73,
    status: 'queued',
    year: 2024,
    citations: 56,
    pdfUrl: 'https://arxiv.org/abs/2401.12349',
    researchRole: 'implementation',
    dgScore: 8,
  },
  {
    id: 'mock-6',
    title: 'Constitutional AI: Harmlessness from AI Feedback',
    authors: ['Bai et al.'],
    abstract: 'We present Constitutional AI, an approach for training AI systems to be harmless through AI feedback. Our method uses a set of principles to guide the model behavior, reducing harmful outputs by 60%.',
    category: 'Safety',
    priority: 'P3',
    relevance: 78,
    novelty: 65,
    status: 'queued',
    year: 2023,
    citations: 892,
    pdfUrl: 'https://arxiv.org/abs/2212.08073',
    researchRole: 'safety',
    dgScore: 7,
  },
  {
    id: 'mock-7',
    title: 'ToolLLM: Facilitating Large Language Models to Master Tools',
    authors: ['Qin et al.'],
    abstract: 'ToolLLM is a framework for training LLMs to effectively use external tools. We construct ToolBench, a dataset of 16,000+ real-world API interactions, and demonstrate significant improvements in tool-use accuracy.',
    category: 'Tools',
    priority: 'P3',
    relevance: 75,
    novelty: 70,
    status: 'queued',
    year: 2024,
    citations: 178,
    pdfUrl: 'https://arxiv.org/abs/2307.16789',
    researchRole: 'harness',
    dgScore: 7,
  },
  {
    id: 'mock-8',
    title: 'TrustGPT: A Benchmark for Trustworthy Large Language Models',
    authors: ['Huang et al.'],
    abstract: 'TrustGPT evaluates LLM trustworthiness across toxicity, bias, and robustness dimensions. Our benchmark reveals that even state-of-the-art models exhibit concerning behaviors in adversarial settings.',
    category: 'Safety',
    priority: 'P3',
    relevance: 72,
    novelty: 61,
    status: 'queued',
    year: 2023,
    citations: 142,
    pdfUrl: 'https://arxiv.org/abs/2306.08092',
    researchRole: 'safety',
    dgScore: 6,
  },
]

// ─── Constants ──────────────────────────────────────────────────────────────

const CATEGORIES = ['All', 'Safety', 'Evaluation', 'Agents', 'RAG', 'Architecture', 'Tools'] as const

const vettingStatus: Record<string, { color: string; icon: typeof CheckCircle2 }> = {
  vetted: { color: 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400', icon: CheckCircle2 },
  vetting: { color: 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400', icon: Clock },
  queued: { color: 'bg-slate-500/20 text-slate-500 dark:text-slate-400', icon: FileSearch },
}

const priorityColors: Record<string, string> = {
  P0: 'bg-red-600/20 text-red-600 dark:text-red-400 border-red-600/30',
  P1: 'bg-orange-600/20 text-orange-600 dark:text-orange-400 border-orange-600/30',
  P2: 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400 border-yellow-600/30',
  P3: 'bg-slate-500/20 text-slate-500 dark:text-slate-400 border-slate-500/30',
}

const categoryIcons: Record<string, typeof Shield> = {
  Safety: Shield,
  Evaluation: Eye,
  Agents: Cpu,
  RAG: Database,
  Architecture: Zap,
  Tools: Sparkles,
}

// ─── Hydration-safe reference time ─────────────────────────────────────────────

const REFERENCE_TIME = new Date('2025-03-04T12:00:00.000Z').getTime()

// ─── Chart mock data ──────────────────────────────────────────────────────────

// Paper Trends (30 days) — uses fixed reference time to avoid hydration mismatch
const paperTrendsData = Array.from({ length: 30 }, (_, i) => {
  const d = new Date(REFERENCE_TIME)
  d.setDate(d.getDate() - (29 - i))
  const label = `${d.getMonth() + 1}/${d.getDate()}`
  return {
    date: label,
    papers: Math.floor(Math.random() * 5) + 1 + Math.floor(i / 6),
    vetted: Math.floor(Math.random() * 3) + Math.floor(i / 10),
  }
})

// Domain distribution
const domainColors: Record<string, string> = {
  'AI Safety': '#10b981',
  'Alignment': '#34d399',
  'Evaluation': '#f59e0b',
  'Agents': '#8b5cf6',
  'RAG': '#06b6d4',
  'Architecture': '#f97316',
  'Tools': '#ec4899',
}

// ─── Custom recharts tooltip ──────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border/50 bg-card px-3 py-2 shadow-xl text-xs">
      <p className="font-medium mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="text-muted-foreground">
          <span className="inline-block h-2 w-2 rounded-full mr-1.5" style={{ backgroundColor: p.color }} />
          {p.name}: <span className="font-mono font-medium text-foreground">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, color, sublabel }: { label: string; value: string | number; icon: typeof BookOpen; color: string; sublabel?: string }) {
  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn('h-4 w-4', color)} />
            <span className="text-xs text-muted-foreground">{label}</span>
          </div>
        </div>
        <div className="mt-2">
          <span className={cn('text-2xl font-bold', color)}>{value}</span>
          {sublabel && <p className="text-[10px] text-muted-foreground mt-0.5">{sublabel}</p>}
        </div>
      </CardContent>
    </Card>
  )
}

function PaperCard({
  paper,
  onAnalyze,
  isAnalyzing,
}: {
  paper: Paper
  onAnalyze: (paper: Paper) => void
  isAnalyzing: boolean
}) {
  const status = vettingStatus[paper.status] || vettingStatus.queued
  const StatusIcon = status.icon
  const CategoryIcon = categoryIcons[paper.category] || BookOpen

  return (
    <div className="group p-3 rounded-lg bg-muted/30 hover:bg-muted/50 border border-transparent hover:border-emerald-500/20 transition-all duration-200 space-y-2">
      {/* Title row */}
      <div className="flex items-start gap-2">
        <StatusIcon className={cn('h-4 w-4 shrink-0 mt-0.5', status.color.split(' ')[1])} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium leading-tight group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
            {paper.title}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-muted-foreground">{paper.authors.join(', ')}</span>
            {paper.year && (
              <span className="text-[10px] text-muted-foreground font-mono">({paper.year})</span>
            )}
          </div>
        </div>
        <Badge className={cn('text-[9px] h-4 border', priorityColors[paper.priority] || priorityColors.P3)}>
          {paper.priority}
        </Badge>
      </div>

      {/* Abstract preview */}
      {paper.abstract && (
        <div className="pl-6">
          <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
            {paper.abstract}
          </p>
        </div>
      )}

      {/* Metrics row */}
      <div className="flex items-center gap-2 pl-6 flex-wrap">
        <Badge variant="outline" className="text-[9px] h-4 gap-1">
          <CategoryIcon className="h-2.5 w-2.5" />
          {paper.category}
        </Badge>
        <div className="flex items-center gap-1 text-[10px]">
          <TrendingUp className="h-3 w-3 text-muted-foreground" />
          <span>Rel: <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">{paper.relevance}%</span></span>
        </div>
        <div className="flex items-center gap-1 text-[10px]">
          <Star className="h-3 w-3 text-muted-foreground" />
          <span>Nov: <span className="font-mono font-medium">{paper.novelty}%</span></span>
        </div>
        {paper.citations > 0 && (
          <div className="flex items-center gap-1 text-[10px]">
            <Quote className="h-3 w-3 text-muted-foreground" />
            <span>Cit: <span className="font-mono font-medium">{paper.citations}</span></span>
          </div>
        )}
        {paper.dgScore != null && (
          <div className="flex items-center gap-1 text-[10px]">
            <Brain className="h-3 w-3 text-muted-foreground" />
            <span>DG: <span className="font-mono font-medium">{paper.dgScore}</span></span>
          </div>
        )}
        <Badge className={cn('text-[9px] h-4 border-0', status.color)}>
          {paper.status}
        </Badge>
        {paper.source && (
          <Badge variant="secondary" className="text-[8px] h-3">
            {paper.source}
          </Badge>
        )}
      </div>

      {/* Actions row */}
      <div className="flex items-center gap-2 pl-6">
        <Button
          variant="ghost"
          size="sm"
          className="h-6 text-[10px] gap-1 text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 hover:bg-emerald-500/10 px-2"
          onClick={() => onAnalyze(paper)}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Brain className="h-3 w-3" />
          )}
          Analyze
        </Button>
        {paper.pdfUrl && (
          <a
            href={paper.pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="h-6 text-[10px] gap-1 text-muted-foreground hover:text-foreground inline-flex items-center px-2 rounded-md hover:bg-muted/80 transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
            PDF
          </a>
        )}
      </div>
    </div>
  )
}

// ─── Main Component ─────────────────────────────────────────────────────────

export function ResearchTab() {
  // ─── State ─────────────────────────────────────────────────────────────
  const [mounted, setMounted] = useState(false)
  const [papers, setPapers] = useState<Paper[]>(mockPapers)
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('All')
  const [showSearchResults, setShowSearchResults] = useState(false)

  // Analysis state
  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [analyzingPaper, setAnalyzingPaper] = useState<Paper | null>(null)
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analyzingPaperId, setAnalyzingPaperId] = useState<string | null>(null)

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [isChatLoading, setIsChatLoading] = useState(false)
  const [streamingChatContent, setStreamingChatContent] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Pipeline interactive state
  const [selectedPipelineStage, setSelectedPipelineStage] = useState<string | null>(null)

  // ─── Computed Values ───────────────────────────────────────────────────
  const displayedPapers = showSearchResults && searchResults
    ? searchResults.papers
    : papers.filter(p => selectedCategory === 'All' || p.category === selectedCategory)

  const stats = useMemo(() => ({
    vetted: papers.filter(p => p.status === 'vetted').length,
    vetting: papers.filter(p => p.status === 'vetting').length,
    queued: papers.filter(p => p.status === 'queued').length,
    avgRelevance: papers.length > 0
      ? Math.round(papers.reduce((sum, p) => sum + p.relevance, 0) / papers.length)
      : 0,
    rejected: 3, // simulated
    inPipeline: papers.filter(p => p.status === 'vetting' || p.status === 'queued').length,
  }), [papers])

  // Domain distribution for chart
  const domainData = useMemo(() => {
    const domainMap: Record<string, number> = {
      'AI Safety': 0,
      'Alignment': 0,
      'Evaluation': 0,
      'Agents': 0,
      'RAG': 0,
      'Architecture': 0,
      'Tools': 0,
    }
    papers.forEach(p => {
      const cat = p.category
      if (cat === 'Safety') { domainMap['AI Safety']++; domainMap['Alignment'] += Math.random() > 0.5 ? 1 : 0 }
      else if (cat === 'Evaluation') domainMap['Evaluation']++
      else if (cat === 'Agents') domainMap['Agents']++
      else if (cat === 'RAG') domainMap['RAG']++
      else if (cat === 'Architecture') domainMap['Architecture']++
      else if (cat === 'Tools') domainMap['Tools']++
    })
    // Ensure minimum values for visual interest
    Object.keys(domainMap).forEach(k => { if (domainMap[k] === 0) domainMap[k] = Math.floor(Math.random() * 3) + 1 })
    return Object.entries(domainMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
  }, [papers])

  // Recently vetted papers — use fixed reference time until mounted to avoid hydration mismatch
  const recentlyVetted = useMemo(() => {
    const baseTime = mounted ? Date.now() : REFERENCE_TIME
    return papers
      .filter(p => p.status === 'vetted')
      .map((p, i) => ({
        ...p,
        vettedDate: new Date(baseTime - (i * 2 + 1) * 86400000), // simulated dates
      }))
      .sort((a, b) => b.vettedDate.getTime() - a.vettedDate.getTime())
  }, [papers, mounted])

  // Pipeline health
  const pipelineHealth = useMemo(() => {
    const total = papers.length || 1
    const vettingRatio = stats.vetting / total
    const queuedRatio = stats.queued / total
    const bottlenecks: string[] = []
    if (vettingRatio > 0.25) bottlenecks.push(`Vetting stage is ${Math.round(vettingRatio * 100)}% full — may need more reviewers`)
    if (queuedRatio > 0.5) bottlenecks.push(`Queue backlog is ${Math.round(queuedRatio * 100)}% — consider parallel vetting`)
    if (stats.vetting === 0 && stats.queued > 0) bottlenecks.push('No active vetting — pipeline stalled')
    const healthScore = Math.max(0, 100 - bottlenecks.length * 25 - Math.round(vettingRatio * 30))
    return { bottlenecks, healthScore, vettingRatio, queuedRatio }
  }, [stats, papers.length])

  // Papers in selected pipeline stage
  const pipelineStagePapers = useMemo(() => {
    if (!selectedPipelineStage) return []
    return papers.filter(p => p.status === selectedPipelineStage)
  }, [papers, selectedPipelineStage])

  // ─── Hydration: set mounted after initial render ──────────────────────
  useEffect(() => {
    setMounted(true)
  }, [])

  // ─── Auto-scroll chat ──────────────────────────────────────────────────
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [chatMessages, streamingChatContent])

  // ─── AI Search Handler ─────────────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return

    setIsSearching(true)
    setShowSearchResults(true)

    try {
      const response = await fetch('/api/ai/research/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery.trim(),
          maxResults: 10,
          depth: 'medium',
        }),
      })

      if (!response.ok) {
        throw new Error(`Search API returned ${response.status}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Search failed')
      }

      const apiResults = data.data.results || []

      // Map API results to Paper type — use enriched fields when available
      const mappedPapers: Paper[] = apiResults.map((r: any, index: number) => ({
        id: r.id || `search-${Date.now()}-${index}`,
        title: r.title || 'Untitled Result',
        authors: r.authors && r.authors.length > 0
          ? r.authors
          : (r.citations?.slice(0, 2).map((c: string) => c.split(',')[0]) || ['AI Research']),
        abstract: r.abstract || r.summary || '',
        category: r.category || r.domain || 'General',
        priority: r.relevanceScore >= 0.85 ? 'P1' : r.relevanceScore >= 0.7 ? 'P2' : 'P3',
        relevance: Math.round((r.relevanceScore || 0.5) * 100),
        novelty: Math.round((r.noveltyScore || r.relevanceScore || 0.5) * 100),
        status: 'vetted' as const,
        year: r.year || new Date().getFullYear(),
        citations: r.citationCount ?? (r.citations?.length || 0),
        pdfUrl: r.pdfUrl || r.sourceUrl || undefined,
        source: r.hostName || data.data.provider || 'z-ai',
        researchRole: r.researchRole || r.domain || 'research',
        dgScore: Math.round((r.relevanceScore || 0.5) * 15),
      }))

      // Build AI suggestions from suggestedActions across results
      const aiSuggestions: AISuggestion[] = apiResults
        .filter((r: any) => r.suggestedActions && r.suggestedActions.length > 0)
        .slice(0, 3)
        .map((r: any, i: number) => ({
          title: r.suggestedActions[0] || r.title,
          relevanceReason: r.keyFindings?.[0] || 'Related to your search query',
          suggestedCategory: r.category || r.domain || 'General',
          relevanceScore: Math.round((r.relevanceScore || 0.7) * 100),
        }))

      // Use sources metadata from API if available
      const apiSources = data.data.sources || {}

      const searchResult: SearchResult = {
        papers: mappedPapers.length > 0 ? mappedPapers : papers.slice(0, 3),
        aiSuggestions,
        query: searchQuery.trim(),
        totalFound: data.data.totalResults || mappedPapers.length,
        sources: {
          database: apiSources.database ?? mappedPapers.length,
          arxiv: apiSources.arxiv ?? 0,
          aiSuggestions: apiSources.aiSuggestions ?? aiSuggestions.length,
        },
      }

      setSearchResults(searchResult)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Search failed'
      toast.error('Search failed', { description: message })

      // Fallback: local filtering on error
      const query = searchQuery.toLowerCase()
      const filteredPapers = papers.filter(p =>
        p.title.toLowerCase().includes(query) ||
        p.abstract.toLowerCase().includes(query) ||
        p.category.toLowerCase().includes(query) ||
        p.authors.some(a => a.toLowerCase().includes(query))
      )

      setSearchResults({
        papers: filteredPapers,
        aiSuggestions: [],
        query: searchQuery.trim(),
        totalFound: filteredPapers.length,
        sources: { database: filteredPapers.length, arxiv: 0, aiSuggestions: 0 },
      })
    } finally {
      setIsSearching(false)
    }
  }, [searchQuery, papers])

  // ─── AI Analysis Handler ───────────────────────────────────────────────
  const handleAnalyze = useCallback(async (paper: Paper) => {
    setAnalyzingPaper(paper)
    setAnalyzingPaperId(paper.id)
    setAnalysisOpen(true)
    setAnalysisResult(null)
    setIsAnalyzing(true)

    try {
      const response = await fetch('/api/ai/research/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paperTitle: paper.title,
          paperAbstract: paper.abstract,
          analysisType: 'relevance',
          focusAreas: ['multi-agent governance', 'safety evaluation', 'NEXUS-OS integration'],
          targetProject: 'NEXUS-OS v3.1 multi-agent AI governance platform',
        }),
      })

      if (!response.ok) {
        throw new Error(`Analysis API returned ${response.status}`)
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Analysis failed')
      }

      const analysis = data.data.analysis || {}
      const keyPoints: string[] = analysis.keyPoints || data.data.keyPoints || []

      // Map API analysis to AnalysisResult structure
      const result: AnalysisResult = {
        summary: analysis.relevanceAnalysis || analysis.summary || paper.abstract || 'No analysis available.',
        critique: [
          analysis.implementationComplexity ? `Implementation Complexity: ${analysis.implementationComplexity}` : '',
          analysis.overallAssessment || '',
          analysis.methodologicalConcerns?.join('; ') || '',
        ].filter(Boolean).join(' — ') || 'Analysis complete.',
        relevance: [
          analysis.suggestedIntegrationPath ? `Integration Path: ${analysis.suggestedIntegrationPath}` : '',
          ...(analysis.relevantSubsystems || []).map((s: any) => `${s.subsystem}: ${s.relevance} — ${s.reason}`),
          analysis.applicabilityScore != null ? `Applicability: ${Math.round(analysis.applicabilityScore * 100)}%` : '',
        ].filter(Boolean).join('\n') || `Research Role: ${paper.researchRole || 'evaluation'}, Project Fit: NEXUS-OS agent governance`,
        concepts: keyPoints.slice(0, 5).length > 0
          ? keyPoints.slice(0, 5)
          : (analysis.risksAndConsiderations || ['multi-agent systems', 'LLM orchestration']).slice(0, 3),
        implementationTask: analysis.suggestedIntegrationPath
          || (paper.relevance >= 85
            ? `Integrate ${paper.category.toLowerCase()} insights into NEXUS agent pipeline — Priority: ${paper.priority}`
            : `Archive for future reference — review when ${paper.category.toLowerCase()} module expands`),
        priorityTier: analysis.priorityRecommendation?.split(' ')[0] || paper.priority,
      }

      setAnalysisResult(result)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Analysis failed'
      toast.error('Analysis failed', { description: message })

      // Fallback result on error
      setAnalysisResult({
        summary: paper.abstract || 'No abstract available.',
        critique: 'AI analysis unavailable — showing basic paper info.',
        relevance: `Research Role: ${paper.researchRole || 'evaluation'}, Project Fit: ${paper.projectFit || 'NEXUS-OS agent governance'} — ${paper.relevance >= 85 ? 'Directly applicable to current architecture.' : 'Indirectly relevant, provides theoretical foundation.'}`,
        concepts: ['multi-agent systems', 'LLM orchestration', 'safety evaluation'].slice(0, 2),
        implementationTask: paper.relevance >= 85
          ? `Integrate ${paper.category.toLowerCase()} insights into NEXUS agent pipeline — Priority: ${paper.priority}`
          : `Archive for future reference — review when ${paper.category.toLowerCase()} module expands`,
        priorityTier: paper.priority,
      })
    } finally {
      setIsAnalyzing(false)
      setAnalyzingPaperId(null)
    }
  }, [])

  // ─── Research Chat Handler ─────────────────────────────────────────────
  const handleChatSend = useCallback(async () => {
    if (!chatInput.trim() || isChatLoading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: chatInput.trim(),
      timestamp: Date.now(),
    }

    setChatMessages(prev => [...prev, userMessage])
    setChatInput('')
    setIsChatLoading(true)
    setStreamingChatContent('')

    // Build context from current papers to include with the user message
    const paperContext = displayedPapers.slice(0, 5).map(p =>
      `- ${p.title} (${p.category}, ${p.priority}, Relevance: ${p.relevance}%)`
    ).join('\n')

    // Include context inline with the user's message — not as a separate user message
    const contextPrefix = `[Research Context — ${papers.length} papers in pipeline]\n${paperContext}\n\n`
    const userContentWithContext = contextPrefix + userMessage.content

    try {
      const response = await fetch('/api/chat?stream=true', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            ...chatMessages
              .map(m => ({ role: m.role, content: m.content })),
            { role: 'user', content: userContentWithContext },
          ],
        }),
      })

      if (!response.ok) {
        // Fallback to non-streaming
        const fallbackResponse = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [
              ...chatMessages
                .map(m => ({ role: m.role, content: m.content })),
              { role: 'user', content: userContentWithContext },
            ],
          }),
        })

        if (!fallbackResponse.ok) {
          throw new Error(`Chat API returned ${fallbackResponse.status}`)
        }

        const fallbackData = await fallbackResponse.json()
        if (fallbackData.error) {
          throw new Error(fallbackData.error)
        }

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: fallbackData.response || 'No response received',
          timestamp: Date.now(),
        }
        setChatMessages(prev => [...prev, assistantMessage])
        setIsChatLoading(false)
        setStreamingChatContent('')
        return
      }

      // Process SSE stream
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let accumulated = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed || !trimmed.startsWith('data:')) continue

          const payload = trimmed.slice(5).trim()
          if (payload === '[DONE]') {
            // Stream complete — finalize the message
            const assistantMessage: ChatMessage = {
              role: 'assistant',
              content: accumulated,
              timestamp: Date.now(),
            }
            setChatMessages(prev => [...prev, assistantMessage])
            setIsChatLoading(false)
            setStreamingChatContent('')
            return
          }

          try {
            const parsed = JSON.parse(payload)
            if (parsed.error) {
              toast.error('Chat error', { description: parsed.error })
              continue
            }
            if (parsed.content) {
              accumulated += parsed.content
              setStreamingChatContent(accumulated)
            }
          } catch {
            // Skip unparseable chunks
          }
        }
      }

      // If stream ended without [DONE], finalize what we have
      if (accumulated) {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: accumulated,
          timestamp: Date.now(),
        }
        setChatMessages(prev => [...prev, assistantMessage])
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Chat failed'
      toast.error('Chat failed', { description: message })
    } finally {
      setIsChatLoading(false)
      setStreamingChatContent('')
    }
  }, [chatInput, isChatLoading, chatMessages, displayedPapers, papers])

  const handleChatKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleChatSend()
    }
  }, [handleChatSend])

  // ─── Clear search ──────────────────────────────────────────────────────
  const handleClearSearch = useCallback(() => {
    setSearchQuery('')
    setSearchResults(null)
    setShowSearchResults(false)
  }, [])

  // ─── Format date helper ────────────────────────────────────────────────
  const formatDate = (date: Date) => {
    return `${date.getMonth() + 1}/${date.getDate()}`
  }

  const getRelativeTime = (date: Date) => {
    const diff = Date.now() - date.getTime()
    const days = Math.floor(diff / 86400000)
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    return `${days}d ago`
  }

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BookOpen className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">Research Pipeline</h2>
        <Badge variant="secondary" className="text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400">
          {papers.length} papers
        </Badge>
        {showSearchResults && searchResults && (
          <Badge variant="outline" className="text-[10px]">
            Search: {searchResults.totalFound} results
          </Badge>
        )}
      </div>

      {/* ─── 1. Research Statistics Dashboard ──────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <StatCard label="Papers Vetted" value={stats.vetted} icon={CheckCircle2} color="text-emerald-600 dark:text-emerald-400" sublabel="Approved & integrated" />
        <StatCard label="In Pipeline" value={stats.inPipeline} icon={Clock} color="text-yellow-600 dark:text-yellow-400" sublabel="Vetting + Queued" />
        <StatCard label="Rejected" value={stats.rejected} icon={XCircle} color="text-red-600 dark:text-red-400" sublabel="Not meeting criteria" />
        <StatCard label="Avg Relevance" value={`${stats.avgRelevance}%`} icon={TrendingUp} color="text-emerald-600 dark:text-emerald-400" sublabel="Across all papers" />
        <StatCard label="Domains" value={domainData.length} icon={Hash} color="text-cyan-600 dark:text-cyan-400" sublabel="Active research areas" />
      </div>

      {/* ─── 5. Research Pipeline Health ───────────────────────────────────── */}
      <Card className={cn(
        "bg-card/50 border-border/50",
        pipelineHealth.healthScore >= 70 ? 'border-emerald-500/20' :
        pipelineHealth.healthScore >= 40 ? 'border-yellow-500/20' : 'border-red-500/20'
      )}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className={cn(
                'h-4 w-4',
                pipelineHealth.healthScore >= 70 ? 'text-emerald-600 dark:text-emerald-400' :
                pipelineHealth.healthScore >= 40 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'
              )} />
              <span className="text-sm font-semibold">Pipeline Health</span>
              <Badge className={cn(
                'text-[9px] border-0',
                pipelineHealth.healthScore >= 70 ? 'bg-emerald-600/20 text-emerald-600 dark:text-emerald-400' :
                pipelineHealth.healthScore >= 40 ? 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400' : 'bg-red-600/20 text-red-600 dark:text-red-400'
              )}>
                {pipelineHealth.healthScore}%
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-[10px]">
              <span className="text-muted-foreground">
                Vetting: <span className="font-mono">{Math.round(pipelineHealth.vettingRatio * 100)}%</span>
              </span>
              <span className="text-muted-foreground">
                Queue: <span className="font-mono">{Math.round(pipelineHealth.queuedRatio * 100)}%</span>
              </span>
            </div>
          </div>
          <Progress
            value={pipelineHealth.healthScore}
            className={cn(
              'h-2',
              pipelineHealth.healthScore >= 70 ? '[&>div]:bg-emerald-500' :
              pipelineHealth.healthScore >= 40 ? '[&>div]:bg-yellow-500' : '[&>div]:bg-red-500'
            )}
          />
          {pipelineHealth.bottlenecks.length > 0 && (
            <div className="mt-3 space-y-1.5">
              {pipelineHealth.bottlenecks.map((bottleneck, i) => (
                <div key={i} className="flex items-start gap-2 text-[10px]">
                  <AlertTriangle className="h-3 w-3 text-yellow-500 shrink-0 mt-0.5" />
                  <span className="text-yellow-600 dark:text-yellow-400">{bottleneck}</span>
                </div>
              ))}
            </div>
          )}
          {pipelineHealth.bottlenecks.length === 0 && (
            <p className="text-[10px] text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Pipeline is flowing smoothly — no bottlenecks detected
            </p>
          )}
        </CardContent>
      </Card>

      {/* ─── Interactive Pipeline Visualization ─────────────────────────────── */}
      <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/5 to-transparent">
        <CardContent className="p-4">
          <div className="flex items-center gap-1 sm:gap-2">
            {[
              { key: 'queued', label: 'Queued', count: stats.queued, color: 'bg-slate-500', textColor: 'text-slate-500 dark:text-slate-400', icon: FileSearch },
              { key: 'vetting', label: 'Vetting', count: stats.vetting, color: 'bg-yellow-500', textColor: 'text-yellow-600 dark:text-yellow-400', icon: Clock },
              { key: 'vetted', label: 'Vetted', count: stats.vetted, color: 'bg-emerald-500', textColor: 'text-emerald-600 dark:text-emerald-400', icon: CheckCircle2 },
            ].map((stage, i) => (
              <div key={stage.key} className="flex items-center gap-1 sm:gap-2 flex-1">
                <motion.div
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.98 }}
                  className={cn(
                    "flex-1 rounded-lg bg-muted/50 border p-2.5 text-center cursor-pointer transition-all",
                    selectedPipelineStage === stage.key
                      ? 'border-emerald-500/50 shadow-md shadow-emerald-500/10'
                      : 'border-border/50 hover:border-emerald-500/30'
                  )}
                  onClick={() => setSelectedPipelineStage(selectedPipelineStage === stage.key ? null : stage.key)}
                >
                  <stage.icon className={cn('h-4 w-4 mx-auto mb-1', stage.textColor)} />
                  <div className={cn('text-lg font-bold tabular-nums', stage.textColor)}>{stage.count}</div>
                  <div className="text-[10px] text-muted-foreground">{stage.label}</div>
                  {selectedPipelineStage === stage.key && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mt-1"
                    >
                      <ChevronDown className="h-3 w-3 text-emerald-500 mx-auto" />
                    </motion.div>
                  )}
                </motion.div>
                {i < 2 && (
                  <ChevronRight className="h-4 w-4 text-muted-foreground/40 shrink-0 hidden sm:block" />
                )}
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-2">
            <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-slate-500 via-yellow-500 to-emerald-500 transition-all duration-500" style={{ width: `${Math.max(stats.vetted / Math.max(papers.length, 1) * 100, 5)}%` }} />
            </div>
            <span className="text-[10px] text-muted-foreground tabular-nums">{papers.length > 0 ? Math.round(stats.vetted / papers.length * 100) : 0}% complete</span>
          </div>
          <p className="text-[9px] text-muted-foreground mt-1.5 text-center">Click a stage to see papers in that phase</p>
        </CardContent>
      </Card>

      {/* ─── 6. Pipeline Stage Papers (shown when a stage is selected) ─────── */}
      <AnimatePresence>
        {selectedPipelineStage && pipelineStagePapers.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Card className="bg-card/50 border-emerald-500/20">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  {selectedPipelineStage === 'queued' && <FileSearch className="h-4 w-4 text-slate-500" />}
                  {selectedPipelineStage === 'vetting' && <Clock className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />}
                  {selectedPipelineStage === 'vetted' && <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />}
                  Papers in &ldquo;{selectedPipelineStage}&rdquo; Stage
                  <Badge variant="outline" className="text-[9px] ml-1">{pipelineStagePapers.length}</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-5 w-5 p-0 ml-auto text-muted-foreground hover:text-foreground"
                    onClick={() => setSelectedPipelineStage(null)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 pt-0">
                <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                  {pipelineStagePapers.map((paper) => (
                    <PaperCard
                      key={paper.id}
                      paper={paper}
                      onAnalyze={handleAnalyze}
                      isAnalyzing={analyzingPaperId === paper.id}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Charts Row: Paper Trends + Top Domains ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 2. Paper Trends Line Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Paper Trends
              <Badge variant="outline" className="text-[9px] ml-1">30 days</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={paperTrendsData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 8, fill: 'hsl(var(--muted-foreground))' }}
                  interval={4}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="papers"
                  name="Submissions"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, fill: '#10b981' }}
                />
                <Line
                  type="monotone"
                  dataKey="vetted"
                  name="Vetted"
                  stroke="#34d399"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, fill: '#34d399' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* 3. Top Research Domains Bar Chart */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Top Research Domains
              <Badge variant="outline" className="text-[9px] ml-1">{domainData.length} domains</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={domainData} layout="vertical" margin={{ top: 5, right: 10, left: 60, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }}
                  width={60}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Papers" radius={[0, 4, 4, 0]} maxBarSize={20}>
                  {domainData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={domainColors[entry.name] || '#10b981'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* ─── 4. Recently Vetted Papers ─────────────────────────────────────── */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Recently Vetted Papers
            <Badge variant="outline" className="text-[9px] ml-1">{recentlyVetted.length} papers</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {recentlyVetted.length === 0 ? (
            <div className="text-center py-6 text-muted-foreground text-sm">
              No vetted papers yet
            </div>
          ) : (
            <div className="space-y-3 max-h-72 overflow-y-auto custom-scrollbar">
              {recentlyVetted.map((paper) => (
                <div key={paper.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-muted/20 hover:bg-muted/40 transition-colors">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium truncate">{paper.title}</span>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[9px] text-muted-foreground">{paper.authors.join(', ')}</span>
                      <span className="text-[9px] text-muted-foreground font-mono" suppressHydrationWarning>{getRelativeTime(paper.vettedDate)}</span>
                      <span className="text-[9px] text-muted-foreground font-mono" suppressHydrationWarning>{formatDate(paper.vettedDate)}</span>
                    </div>
                  </div>
                  <div className="shrink-0 w-20">
                    <div className="flex items-center justify-between text-[9px] mb-0.5">
                      <span className="text-muted-foreground">Relevance</span>
                      <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">{paper.relevance}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${paper.relevance}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        className={cn(
                          'h-full rounded-full',
                          paper.relevance >= 85 ? 'bg-emerald-500' :
                          paper.relevance >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                        )}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI Search Bar */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="AI-powered research search... (e.g., 'multi-agent safety evaluation')"
                className="pl-9 h-9 bg-muted/50 border-border/60 focus-visible:border-emerald-500/50 focus-visible:ring-emerald-500/20"
                disabled={isSearching}
              />
            </div>
            <Button
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
              className="h-9 bg-gradient-to-r from-emerald-500 to-emerald-700 hover:from-emerald-600 hover:to-emerald-800 text-white shadow-sm disabled:opacity-50"
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
              ) : (
                <Sparkles className="h-4 w-4 mr-1.5" />
              )}
              Search
            </Button>
            {showSearchResults && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleClearSearch}
                className="h-9 w-9 shrink-0 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
          {isSearching && (
            <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Searching database, arXiv, and AI suggestions...
            </div>
          )}
          {/* AI Suggestions */}
          {searchResults?.aiSuggestions && searchResults.aiSuggestions.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wider">
                <Sparkles className="h-3 w-3 text-emerald-500" />
                AI Suggestions
              </div>
              <div className="flex flex-wrap gap-1.5">
                {searchResults.aiSuggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setSearchQuery(s.title)
                    }}
                    className="text-[10px] rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 hover:bg-emerald-500/20 transition-colors text-left cursor-pointer"
                  >
                    <span className="text-emerald-600 dark:text-emerald-400 font-medium">{s.suggestedCategory}</span>
                    <span className="text-muted-foreground ml-1">{s.title.slice(0, 40)}...</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {/* Search Sources */}
          {searchResults && !isSearching && (
            <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1"><Database className="h-3 w-3" /> DB: {searchResults.sources.database}</span>
              <span className="flex items-center gap-1"><BookOpen className="h-3 w-3" /> arXiv: {searchResults.sources.arxiv}</span>
              <span className="flex items-center gap-1"><Sparkles className="h-3 w-3" /> AI: {searchResults.sources.aiSuggestions}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats (original) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Vetted (P1)" value={stats.vetted} icon={CheckCircle2} color="text-emerald-600 dark:text-emerald-400" />
        <StatCard label="Vetting" value={stats.vetting} icon={Clock} color="text-yellow-600 dark:text-yellow-400" />
        <StatCard label="Queued" value={stats.queued} icon={FileSearch} color="text-slate-500 dark:text-slate-400" />
        <StatCard label="Avg Relevance" value={`${stats.avgRelevance}%`} icon={TrendingUp} color="text-emerald-600 dark:text-emerald-400" />
      </div>

      {/* Category Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {CATEGORIES.map((cat) => {
          const CatIcon = categoryIcons[cat] || Filter
          const count = cat === 'All'
            ? papers.length
            : papers.filter(p => p.category === cat).length
          const isActive = selectedCategory === cat
          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200 cursor-pointer',
                isActive
                  ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 shadow-sm shadow-emerald-500/10'
                  : 'border-border/50 bg-muted/30 text-muted-foreground hover:bg-muted/50 hover:border-border'
              )}
            >
              <CatIcon className="h-3 w-3" />
              {cat}
              <span className={cn(
                'text-[9px] font-mono px-1 py-0.5 rounded-full',
                isActive
                  ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                  : 'bg-muted text-muted-foreground'
              )}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Papers Queue */}
      <Card className="bg-card/50 border-border/50 bg-gradient-to-br from-emerald-600/3 to-transparent">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Star className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            {showSearchResults ? 'Search Results' : 'Papers Queue'}
            <Badge variant="outline" className="text-[9px] ml-1">{displayedPapers.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {displayedPapers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <BookOpen className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No papers found</p>
              <p className="text-xs mt-1">Try a different search query or category</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[480px] overflow-y-auto custom-scrollbar pr-1">
              {displayedPapers.map((paper) => (
                <PaperCard
                  key={paper.id}
                  paper={paper}
                  onAnalyze={handleAnalyze}
                  isAnalyzing={analyzingPaperId === paper.id}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Research Chat */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Research Chat
            <Badge variant="outline" className="text-[9px]">AI-Powered</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {/* Chat Messages */}
          <ScrollArea className="max-h-[400px] mb-3">
            <div className="space-y-3">
            {chatMessages.length === 0 ? (
              <div className="text-center py-6">
                <Bot className="h-8 w-8 mx-auto mb-2 text-emerald-500/50" />
                <p className="text-xs text-muted-foreground mb-3">
                  Ask questions about research papers, methodologies, or findings
                </p>
                <div className="flex flex-wrap gap-1.5 justify-center">
                  {[
                    'What are the top safety papers?',
                    'Explain Self-RAG',
                    'Compare evaluation methods',
                    'What is OR-Bench?',
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => {
                        setChatInput(prompt)
                      }}
                      className="text-[10px] rounded-full border border-border/60 bg-muted/50 px-2.5 py-1 hover:bg-emerald-500/10 hover:border-emerald-500/30 transition-colors cursor-pointer text-muted-foreground hover:text-emerald-600 dark:hover:text-emerald-400"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              chatMessages.map((msg, i) => (
                <div
                  key={`${msg.timestamp}-${i}`}
                  className={cn(
                    'flex gap-2',
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 mt-0.5">
                      <Bot className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                    </div>
                  )}
                  <div
                    className={cn(
                      'max-w-[80%] rounded-xl px-3 py-2 text-xs leading-relaxed break-words',
                      msg.role === 'user'
                        ? 'rounded-tr-none bg-gradient-to-br from-emerald-500 to-emerald-700 text-white'
                        : 'rounded-tl-none bg-muted text-foreground'
                    )}
                  >
                    {msg.content.split('\n').map((line, j) => (
                      <span key={j}>
                        {j > 0 && <br />}
                        {line}
                      </span>
                    ))}
                  </div>
                  {msg.role === 'user' && (
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 mt-0.5">
                      <Sparkles className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                    </div>
                  )}
                </div>
              ))
            )}
            {isChatLoading && !streamingChatContent && (
              <div className="flex gap-2 justify-start">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20">
                  <Bot className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="rounded-xl rounded-tl-none bg-muted px-3 py-2">
                  <div className="flex gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse [animation-delay:0.2s]" />
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
            {isChatLoading && streamingChatContent && (
              <div className="flex gap-2 justify-start">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 mt-0.5">
                  <Bot className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="max-w-[80%] rounded-xl rounded-tl-none bg-muted px-3 py-2 text-xs leading-relaxed break-words">
                  {streamingChatContent.split('\n').map((line, j) => (
                    <span key={j}>
                      {j > 0 && <br />}
                      {line}
                    </span>
                  ))}
                  <span className="inline-block w-1 h-3 bg-emerald-500 animate-pulse ml-0.5 align-text-bottom" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
            </div>
          </ScrollArea>

          {/* Chat Input */}
          <div className="flex items-center gap-2">
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={handleChatKeyDown}
              placeholder="Ask about research..."
              className="flex-1 h-8 text-xs bg-muted/50 border-border/60 focus-visible:border-emerald-500/50 focus-visible:ring-emerald-500/20"
              disabled={isChatLoading}
            />
            <Button
              onClick={handleChatSend}
              disabled={isChatLoading || !chatInput.trim()}
              size="icon"
              className="h-8 w-8 shrink-0 bg-gradient-to-br from-emerald-500 to-emerald-700 hover:from-emerald-600 hover:to-emerald-800 text-white disabled:opacity-50"
            >
              <Send className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Dialog */}
      <Dialog open={analysisOpen} onOpenChange={setAnalysisOpen}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              AI Paper Analysis
            </DialogTitle>
            <DialogDescription className="text-left">
              {analyzingPaper?.title || 'Analyzing...'}
            </DialogDescription>
          </DialogHeader>

          {isAnalyzing ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <div className="relative">
                <div className="h-12 w-12 rounded-full border-2 border-emerald-500/30 border-t-emerald-500 animate-spin" />
                <Brain className="absolute inset-0 m-auto h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <p className="text-sm text-muted-foreground">Analyzing paper with AI...</p>
              <p className="text-xs text-muted-foreground/60">This may take a moment</p>
            </div>
          ) : analysisResult ? (
            <div className="space-y-4">
              {/* Summary */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                  <BookOpen className="h-3.5 w-3.5" />
                  Summary
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-sm leading-relaxed">
                  {analysisResult.summary}
                </div>
              </div>

              {/* Critique */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-orange-600 dark:text-orange-400">
                  <Eye className="h-3.5 w-3.5" />
                  Critique
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-sm leading-relaxed">
                  {analysisResult.critique}
                </div>
              </div>

              {/* Relevance */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400">
                  <TrendingUp className="h-3.5 w-3.5" />
                  Relevance
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-sm leading-relaxed">
                  {analysisResult.relevance}
                </div>
              </div>

              {/* Concepts */}
              {analysisResult.concepts.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-600 dark:text-violet-400">
                    <Zap className="h-3.5 w-3.5" />
                    Key Concepts
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {analysisResult.concepts.map((concept, i) => (
                      <Badge key={i} variant="secondary" className="text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-0">
                        {concept}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Implementation Task */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  <Zap className="h-3.5 w-3.5" />
                  Implementation Task
                </div>
                <div className="p-3 rounded-lg bg-muted/50 text-sm leading-relaxed">
                  {analysisResult.implementationTask}
                </div>
              </div>

              {/* Priority Tier */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Priority Tier:</span>
                <Badge className={cn('text-[10px] border', priorityColors[analysisResult.priorityTier] || priorityColors.P3)}>
                  {analysisResult.priorityTier}
                </Badge>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
