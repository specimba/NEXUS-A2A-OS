'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
import {
  Star,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Loader2,
  MessageSquare,
  BarChart3,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from 'recharts'
import { useApiData } from '@/hooks/use-api-data'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { toast } from 'sonner'

// ─── Types ─────────────────────────────────────────────────────────────────────

interface AgentStat {
  agentId: string
  agentName: string
  agentType: string
  agentDomain: string | null
  agentStatus: string
  avgRating: number
  totalFeedback: number
  trend: 'improving' | 'declining' | 'stable'
  storedTrend: string
  categoryBreakdown: Record<string, { avg: number; count: number }>
  recommendation: string
}

interface AlignmentAlert {
  agentId: string
  agentName: string
  avgRating: number
  recommendation: string
}

interface FeedbackData {
  feedback: {
    id: string
    agentId: string
    rating: number
    category: string
    comment: string | null
    trend: string
    createdAt: string
    agent: { id: string; name: string; type: string; domain: string | null; status: string }
  }[]
  agentStats: AgentStat[]
  globalAvg: number
  categoryRadar: { category: string; avgRating: number; count: number }[]
  alignmentAlerts: AlignmentAlert[]
  totalFeedback: number
}

const FEEDBACK_CATEGORIES = ['quality', 'speed', 'alignment', 'reliability'] as const

// ─── Star Rating Display ──────────────────────────────────────────────────────

function StarRating({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClass = size === 'lg' ? 'h-5 w-5' : size === 'md' ? 'h-4 w-4' : 'h-3.5 w-3.5'
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={`${sizeClass} ${
            star <= Math.round(rating)
              ? 'text-amber-400 fill-amber-400'
              : 'text-muted-foreground/30'
          }`}
        />
      ))}
    </div>
  )
}

// ─── Interactive Star Picker ───────────────────────────────────────────────────

function StarPicker({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hovered, setHovered] = useState(0)
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          className="transition-transform hover:scale-110"
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          onClick={() => onChange(star)}
        >
          <Star
            className={`h-7 w-7 ${
              star <= (hovered || value)
                ? 'text-amber-400 fill-amber-400'
                : 'text-muted-foreground/30'
            } transition-colors`}
          />
        </button>
      ))}
    </div>
  )
}

// ─── Trend Badge ───────────────────────────────────────────────────────────────

function TrendBadge({ trend }: { trend: string }) {
  switch (trend) {
    case 'improving':
      return (
        <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px] gap-0.5">
          <TrendingUp className="h-3 w-3" />
          Improving
        </Badge>
      )
    case 'declining':
      return (
        <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px] gap-0.5">
          <TrendingDown className="h-3 w-3" />
          Declining
        </Badge>
      )
    default:
      return (
        <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px] gap-0.5">
          <Minus className="h-3 w-3" />
          Stable
        </Badge>
      )
  }
}

// ─── Submit Feedback Dialog ────────────────────────────────────────────────────

function SubmitFeedbackDialog({
  open,
  onOpenChange,
  agents,
  onSubmitted,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  agents: { id: string; name: string; type: string; status: string }[]
  onSubmitted: () => void
}) {
  const [agentId, setAgentId] = useState('')
  const [rating, setRating] = useState(0)
  const [category, setCategory] = useState('')
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!agentId || rating === 0 || !category) {
      toast.error('Missing fields', { description: 'Agent, rating, and category are required.' })
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentId, rating, category, comment: comment.trim() || undefined }),
      })
      const data = await res.json()
      if (res.ok) {
        toast.success('Feedback submitted', {
          description: `Rated ${data.feedback?.agent?.name || 'agent'} — trend: ${data.computedTrend}`,
          icon: <Star className="h-4 w-4 fill-amber-400 text-amber-400" />,
        })
        onSubmitted()
        onOpenChange(false)
        setAgentId('')
        setRating(0)
        setCategory('')
        setComment('')
      } else {
        toast.error('Submission failed', { description: data.error || 'Unknown error' })
      }
    } catch {
      toast.error('Network error', { description: 'Could not reach feedback API.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border/60">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-600/20">
              <Star className="h-5 w-5 text-white fill-white" />
            </div>
            <div>
              <DialogTitle className="text-base">Submit Feedback</DialogTitle>
              <DialogDescription className="text-xs">
                Rate an agent&apos;s performance
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          <div className="h-px bg-gradient-to-r from-transparent via-amber-600/40 to-transparent" />

          <div className="space-y-2">
            <Label className="text-xs font-medium">Agent</Label>
            <Select value={agentId} onValueChange={setAgentId}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Select agent..." />
              </SelectTrigger>
              <SelectContent>
                {agents.map((a) => (
                  <SelectItem key={a.id} value={a.id} className="text-sm">
                    {a.name} ({a.type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium">Rating</Label>
            <div className="flex items-center gap-3">
              <StarPicker value={rating} onChange={setRating} />
              {rating > 0 && (
                <span className="text-sm font-bold text-amber-400 tabular-nums">{rating}/5</span>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium">Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="text-sm">
                <SelectValue placeholder="Select category..." />
              </SelectTrigger>
              <SelectContent>
                {FEEDBACK_CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c} className="text-sm">
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium">Comment (optional)</Label>
            <Textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a note about this agent's performance..."
              rows={2}
              className="text-xs resize-none"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="gap-1.5 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white border-0"
            onClick={handleSubmit}
            disabled={submitting || !agentId || rating === 0 || !category}
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Star className="h-3.5 w-3.5" />}
            {submitting ? 'Submitting...' : 'Submit'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main AgentFeedbackPanel ──────────────────────────────────────────────────

export function AgentFeedbackPanel() {
  const { data, loading, refetch } = useApiData<FeedbackData>('/api/feedback', 30000)
  const [submitDialogOpen, setSubmitDialogOpen] = useState(false)

  const agentStats = data?.agentStats ?? []
  const categoryRadar = data?.categoryRadar ?? []
  const alignmentAlerts = data?.alignmentAlerts ?? []
  const globalAvg = data?.globalAvg ?? 0
  const totalFeedback = data?.totalFeedback ?? 0
  const recentFeedback = data?.feedback?.slice(0, 8) ?? []

  // Agents for the submit dialog
  const agents = useMemo(() => {
    return agentStats.map((a) => ({
      id: a.agentId,
      name: a.agentName,
      type: a.agentType,
      status: a.agentStatus,
    }))
  }, [agentStats])

  // Radar chart data
  const radarData = useMemo(() => {
    if (categoryRadar.length === 0) {
      return FEEDBACK_CATEGORIES.map((cat) => ({
        category: cat.charAt(0).toUpperCase() + cat.slice(1),
        rating: 0,
        fullMark: 5,
      }))
    }
    return FEEDBACK_CATEGORIES.map((cat) => {
      const found = categoryRadar.find((c) => c.category === cat)
      return {
        category: cat.charAt(0).toUpperCase() + cat.slice(1),
        rating: found ? Math.round(found.avgRating * 100) / 100 : 0,
        fullMark: 5,
      }
    })
  }, [categoryRadar])

  const tooltipContentStyle: React.CSSProperties = {
    backgroundColor: 'var(--card)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    fontSize: '11px',
    color: 'var(--foreground)',
  }

  return (
    <>
      <Card className="relative overflow-hidden border-amber-600/15">
        <div className="absolute inset-0 bg-gradient-to-br from-amber-600/5 via-transparent to-orange-600/3" />
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-amber-600/40 to-transparent" />
        <CardHeader className="relative pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Star className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              Feedback Engine
              <DataSourceBadge source="api" />
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 gap-1 text-[9px] text-muted-foreground hover:text-foreground"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-3 w-3" />
                Refresh
              </Button>
              <Button
                size="sm"
                className="gap-1.5 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white border-0 h-7 text-[10px]"
                onClick={() => setSubmitDialogOpen(true)}
              >
                <Star className="h-3 w-3" />
                Rate Agent
              </Button>
              <Badge className="border-0 text-[9px] px-2 bg-amber-600/15 text-amber-600 dark:text-amber-400">
                {totalFeedback} entries
              </Badge>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground mt-1">
            Hermes-inspired agent performance ratings, trend analysis, and alignment recommendations
          </p>
        </CardHeader>
        <CardContent className="relative p-4 pt-0">
          {loading && !data ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 text-amber-600 dark:text-amber-400 animate-spin" />
              <span className="ml-2 text-xs text-muted-foreground">Loading feedback...</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Global Stats Row */}
              <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
                <div className="rounded-lg border border-border/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Global Avg</p>
                  <div className="mt-1 flex items-center justify-center gap-1.5">
                    <span className="text-lg font-bold text-amber-600 dark:text-amber-400 tabular-nums">{globalAvg.toFixed(1)}</span>
                    <Star className="h-4 w-4 text-amber-400 fill-amber-400" />
                  </div>
                </div>
                <div className="rounded-lg border border-border/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Agents Rated</p>
                  <p className="mt-1 text-lg font-bold tabular-nums">{agentStats.length}</p>
                </div>
                <div className="rounded-lg border border-border/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Improving</p>
                  <p className="mt-1 text-lg font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                    {agentStats.filter((a) => a.trend === 'improving').length}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 p-3 text-center">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Declining</p>
                  <p className="mt-1 text-lg font-bold text-red-600 dark:text-red-400 tabular-nums">
                    {agentStats.filter((a) => a.trend === 'declining').length}
                  </p>
                </div>
              </div>

              {/* Main Grid: Agent Rating Cards + Category Radar */}
              <div className="grid gap-4 lg:grid-cols-3">
                {/* Agent Rating Cards */}
                <div className="lg:col-span-2 space-y-2 max-h-96 overflow-y-auto custom-scrollbar pr-1">
                  {agentStats.length > 0 ? (
                    agentStats.map((agent) => (
                      <div
                        key={agent.agentId}
                        className={`rounded-lg border p-3 transition-all hover-lift ${
                          agent.trend === 'declining'
                            ? 'border-red-600/20 bg-gradient-to-r from-red-600/5 via-transparent to-transparent'
                            : agent.trend === 'improving'
                              ? 'border-emerald-600/20 bg-gradient-to-r from-emerald-600/5 via-transparent to-transparent'
                              : 'border-border/50 bg-gradient-to-r from-muted/10 via-transparent to-transparent'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                              agent.trend === 'declining'
                                ? 'bg-red-600/15'
                                : agent.trend === 'improving'
                                  ? 'bg-emerald-600/15'
                                  : 'bg-amber-600/15'
                            }`}>
                              <span className="text-xs font-bold text-muted-foreground">
                                {agent.agentName.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">{agent.agentName}</span>
                                <TrendBadge trend={agent.trend} />
                              </div>
                              <div className="flex items-center gap-2 mt-0.5">
                                <StarRating rating={agent.avgRating} />
                                <span className="text-[10px] text-muted-foreground tabular-nums">
                                  {agent.avgRating.toFixed(1)} ({agent.totalFeedback})
                                </span>
                                {agent.agentDomain && (
                                  <Badge variant="outline" className="text-[8px] px-1 py-0">{agent.agentDomain}</Badge>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Category mini-bars */}
                        {Object.keys(agent.categoryBreakdown).length > 0 && (
                          <div className="mt-2 flex items-center gap-2">
                            {Object.entries(agent.categoryBreakdown).map(([cat, data]) => (
                              <div key={cat} className="flex-1">
                                <div className="flex items-center justify-between text-[9px] text-muted-foreground mb-0.5">
                                  <span>{cat.slice(0, 3)}</span>
                                  <span className="tabular-nums">{data.avg.toFixed(1)}</span>
                                </div>
                                <div className="h-1 rounded-full bg-muted overflow-hidden">
                                  <div
                                    className={`h-full rounded-full transition-all ${
                                      data.avg >= 4 ? 'bg-emerald-500' :
                                      data.avg >= 3 ? 'bg-amber-500' :
                                      'bg-red-500'
                                    }`}
                                    style={{ width: `${(data.avg / 5) * 100}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Recommendation for declining agents */}
                        {agent.trend === 'declining' && (
                          <div className="mt-2 rounded-md border border-red-600/15 bg-red-600/5 px-2.5 py-1.5">
                            <div className="flex items-start gap-1.5">
                              <AlertTriangle className="h-3 w-3 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                              <p className="text-[10px] text-red-600/80 dark:text-red-400/80 leading-relaxed">
                                {agent.recommendation}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-lg border border-dashed border-border/50 p-6 text-center">
                      <Star className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                      <p className="text-xs text-muted-foreground">No feedback data yet. Rate an agent to get started.</p>
                    </div>
                  )}
                </div>

                {/* Category Radar Chart */}
                <div className="space-y-3">
                  <Card className="border-border/50">
                    <CardHeader className="pb-1 pt-3 px-3">
                      <CardTitle className="text-xs flex items-center gap-1.5">
                        <BarChart3 className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                        Category Radar
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-2 pb-2">
                      <ResponsiveContainer width="100%" height={180}>
                        <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                          <PolarGrid stroke="var(--border)" />
                          <PolarAngleAxis
                            dataKey="category"
                            tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }}
                          />
                          <PolarRadiusAxis
                            angle={90}
                            domain={[0, 5]}
                            tick={{ fontSize: 8, fill: 'var(--muted-foreground)' }}
                            tickCount={4}
                          />
                          <Radar
                            name="Avg Rating"
                            dataKey="rating"
                            stroke="#f59e0b"
                            fill="#f59e0b"
                            fillOpacity={0.2}
                            strokeWidth={1.5}
                          />
                          <RechartsTooltip contentStyle={tooltipContentStyle} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>

                  {/* Recent Feedback */}
                  <Card className="border-border/50">
                    <CardHeader className="pb-1 pt-3 px-3">
                      <CardTitle className="text-xs flex items-center gap-1.5">
                        <MessageSquare className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                        Recent Feedback
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="px-3 pb-3">
                      <div className="space-y-1.5 max-h-36 overflow-y-auto custom-scrollbar">
                        {recentFeedback.length > 0 ? (
                          recentFeedback.map((fb) => (
                            <div key={fb.id} className="flex items-center gap-2 text-[10px]">
                              <StarRating rating={fb.rating} />
                              <span className="font-medium truncate max-w-[80px]">{fb.agent.name}</span>
                              <Badge variant="outline" className="text-[7px] px-1 py-0">{fb.category}</Badge>
                              <span className="text-muted-foreground ml-auto tabular-nums">
                                {new Date(fb.createdAt).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                              </span>
                            </div>
                          ))
                        ) : (
                          <p className="text-[10px] text-muted-foreground text-center py-2">No entries yet</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>

              {/* Alignment Alerts */}
              {alignmentAlerts.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400" />
                    <span className="text-xs font-medium text-red-600 dark:text-red-400 uppercase tracking-wider">
                      Alignment Alerts
                    </span>
                    <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">
                      {alignmentAlerts.length}
                    </Badge>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {alignmentAlerts.map((alert) => (
                      <div
                        key={alert.agentId}
                        className="rounded-lg border border-red-600/20 bg-gradient-to-r from-red-600/5 via-transparent to-transparent p-3"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <AlertTriangle className="h-3.5 w-3.5 text-red-600 dark:text-red-400" />
                          <span className="text-sm font-medium">{alert.agentName}</span>
                          <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">
                            Avg: {alert.avgRating.toFixed(1)}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-muted-foreground leading-relaxed">
                          {alert.recommendation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <SubmitFeedbackDialog
        open={submitDialogOpen}
        onOpenChange={setSubmitDialogOpen}
        agents={agents}
        onSubmitted={refetch}
      />
    </>
  )
}
