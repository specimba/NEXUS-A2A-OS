'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
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
} from 'lucide-react'
import { cn } from '@/lib/utils'

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

// ─── Sub-components ─────────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: typeof BookOpen; color: string }) {
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
  const chatEndRef = useRef<HTMLDivElement>(null)

  // ─── Computed Values ───────────────────────────────────────────────────
  const displayedPapers = showSearchResults && searchResults
    ? searchResults.papers
    : papers.filter(p => selectedCategory === 'All' || p.category === selectedCategory)

  const stats = {
    vetted: papers.filter(p => p.status === 'vetted').length,
    vetting: papers.filter(p => p.status === 'vetting').length,
    queued: papers.filter(p => p.status === 'queued').length,
    avgRelevance: papers.length > 0
      ? Math.round(papers.reduce((sum, p) => sum + p.relevance, 0) / papers.length)
      : 0,
  }

  // ─── Auto-scroll chat ──────────────────────────────────────────────────
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatMessages])

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
          category: selectedCategory !== 'All' ? selectedCategory : undefined,
          maxResults: 10,
        }),
      })

      if (!response.ok) throw new Error('Search failed')

      const data: SearchResult = await response.json()
      setSearchResults(data)

      if (data.papers.length > 0) {
        setPapers(prev => {
          const existingIds = new Set(prev.map(p => p.id))
          const newPapers = data.papers.filter(p => !existingIds.has(p.id))
          return [...prev, ...newPapers]
        })
      }
    } catch {
      // Graceful degradation: show message but keep existing data
      setSearchResults({
        papers: papers.filter(p =>
          p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          p.abstract.toLowerCase().includes(searchQuery.toLowerCase())
        ),
        aiSuggestions: [],
        query: searchQuery.trim(),
        totalFound: 0,
        sources: { database: 0, arxiv: 0, aiSuggestions: 0 },
      })
    } finally {
      setIsSearching(false)
    }
  }, [searchQuery, selectedCategory, papers])

  // ─── AI Analysis Handler ───────────────────────────────────────────────
  const handleAnalyze = useCallback(async (paper: Paper) => {
    setAnalyzingPaper(paper)
    setAnalyzingPaperId(paper.id)
    setAnalysisOpen(true)
    setAnalysisResult(null)
    setIsAnalyzing(true)

    try {
      const response = await fetch('/api/research/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paperId: paper.id }),
      })

      if (!response.ok) throw new Error('Analysis failed')

      const data = await response.json()

      // Extract analysis from response
      if (data.results && data.results.length > 0) {
        const result = data.results[0]
        if (result.success && result.analysis) {
          setAnalysisResult({
            summary: result.analysis.abstractSummary || paper.abstract,
            critique: `Novelty: ${result.analysis.noveltyScore || paper.novelty}/2, Evidence Quality: ${result.analysis.evidenceQuality || 'N/A'}/5`,
            relevance: `Research Role: ${result.analysis.researchRole || paper.researchRole || 'N/A'}, Project Fit: ${result.analysis.projectFit || paper.projectFit || 'N/A'}`,
            concepts: result.analysis.conceptIds || [],
            implementationTask: result.analysis.implementationTask || 'Pending review',
            priorityTier: result.analysis.priorityTier || paper.priority,
          })
        } else if (result.error) {
          setAnalysisResult({
            summary: paper.abstract || 'No abstract available.',
            critique: `Analysis error: ${result.error}. Displaying basic paper info.`,
            relevance: `Priority: ${paper.priority}, Category: ${paper.category}`,
            concepts: [],
            implementationTask: 'Analysis unavailable — try again later',
            priorityTier: paper.priority,
          })
        }
      } else {
        // Fallback to basic analysis
        setAnalysisResult({
          summary: paper.abstract || 'No abstract available.',
          critique: 'Full AI analysis unavailable. The analysis engine may be processing. Try again in a moment.',
          relevance: `Relevance Score: ${paper.relevance}%, DG Score: ${paper.dgScore || 'N/A'}, Category: ${paper.category}`,
          concepts: [],
          implementationTask: 'Pending AI analysis',
          priorityTier: paper.priority,
        })
      }
    } catch {
      // Graceful degradation
      setAnalysisResult({
        summary: paper.abstract || 'No abstract available.',
        critique: 'AI analysis service is currently unavailable. This could be due to rate limits or the analysis engine being offline.',
        relevance: `Based on static data: Relevance ${paper.relevance}%, Novelty ${paper.novelty}%, ${paper.citations} citations`,
        concepts: [],
        implementationTask: 'Pending — AI analysis unavailable',
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

    try {
      // Build context from current papers
      const paperContext = displayedPapers.slice(0, 5).map(p =>
        `- ${p.title} (${p.category}, ${p.priority}, Relevance: ${p.relevance}%)`
      ).join('\n')

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            {
              role: 'user',
              content: `Research context - Current papers in pipeline:\n${paperContext}\n\nUser question: ${userMessage.content}`,
            },
          ],
        }),
      })

      if (!response.ok) throw new Error('Chat failed')

      const data = await response.json()
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response || 'No response received.',
        timestamp: Date.now(),
      }

      setChatMessages(prev => [...prev, assistantMessage])
    } catch {
      // Graceful degradation
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: '⚠ Research AI is currently unavailable. Please try again in a moment.',
        timestamp: Date.now(),
      }
      setChatMessages(prev => [...prev, errorMessage])
    } finally {
      setIsChatLoading(false)
    }
  }, [chatInput, isChatLoading, displayedPapers])

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

      {/* Stats */}
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

      {/* Paper Queue */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Star className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            {showSearchResults ? 'Search Results' : 'Paper Queue'}
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
          <div className="max-h-64 overflow-y-auto custom-scrollbar space-y-3 mb-3">
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
            {isChatLoading && (
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
            <div ref={chatEndRef} />
          </div>

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
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
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
                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                    <Sparkles className="h-3.5 w-3.5" />
                    Concepts
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {analysisResult.concepts.map((concept) => (
                      <Badge key={concept} variant="outline" className="text-xs border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
                        {concept.replace(/_/g, ' ')}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Implementation Task */}
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                  <ChevronRight className="h-3.5 w-3.5" />
                  Implementation Task
                </div>
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-sm leading-relaxed">
                  {analysisResult.implementationTask}
                </div>
              </div>

              {/* Priority */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Priority:</span>
                <Badge className={cn('text-xs border', priorityColors[analysisResult.priorityTier] || priorityColors.P3)}>
                  {analysisResult.priorityTier}
                </Badge>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground text-sm">
              No analysis available
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
