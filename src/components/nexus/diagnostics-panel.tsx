'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Wrench,
  CheckCircle2,
  XCircle,
  Loader2,
  Database,
  Globe,
  Brain,
  Users,
  Wallet,
  Shield,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from 'lucide-react'
import { useState, useCallback, useEffect } from 'react'
import { toast } from 'sonner'
import { motion, AnimatePresence } from 'framer-motion'

// ── Diagnostic Step Types ──────────────────────────────────────
interface DiagnosticStep {
  id: string
  name: string
  description: string
  icon: React.ElementType
  status: 'pending' | 'running' | 'success' | 'error' | 'warning'
  latencyMs: number | null
  details: string | null
  apiEndpoint: string | null
}

const diagnosticSteps: DiagnosticStep[] = [
  { id: 'database', name: 'Database Connectivity', description: 'SQLite connection and schema integrity', icon: Database, status: 'pending', latencyMs: null, details: null, apiEndpoint: '/api/system' },
  { id: 'api', name: 'API Health', description: 'REST API endpoints responsiveness', icon: Globe, status: 'pending', latencyMs: null, details: null, apiEndpoint: '/api/models' },
  { id: 'models', name: 'Model Availability', description: 'AI model registry and pool status', icon: Brain, status: 'pending', latencyMs: null, details: null, apiEndpoint: '/api/models' },
  { id: 'agents', name: 'Agent Status', description: 'Agent pool health and trust scores', icon: Users, status: 'pending', latencyMs: null, details: null, apiEndpoint: '/api/agents' },
  { id: 'tokens', name: 'Token Budget', description: 'Budget utilization and limits check', icon: Wallet, status: 'pending', latencyMs: null, details: null, apiEndpoint: '/api/tokens' },
]

interface DiagnosticsPanelProps {
  open: boolean
  onClose: () => void
}

export function DiagnosticsPanel({ open, onClose }: DiagnosticsPanelProps) {
  const [steps, setSteps] = useState<DiagnosticStep[]>(diagnosticSteps)
  const [running, setRunning] = useState(false)
  const [overallScore, setOverallScore] = useState<number | null>(null)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)

  const runDiagnostics = useCallback(async () => {
    setSteps(diagnosticSteps.map(s => ({ ...s, status: 'pending', latencyMs: null, details: null })))
    setRunning(true)
    setOverallScore(null)

    const results: DiagnosticStep[] = []

    for (let i = 0; i < diagnosticSteps.length; i++) {
      const step = diagnosticSteps[i]
      const startTime = Date.now()

      // Mark current step as running
      setSteps(prev => prev.map((s, idx) =>
        idx === i ? { ...s, status: 'running' } : s
      ))

      // Simulate staggered delay
      await new Promise(r => setTimeout(r, 300 + Math.random() * 400))

      try {
        if (step.apiEndpoint) {
          const res = await globalThis.fetch(step.apiEndpoint)
          const elapsed = Date.now() - startTime

          if (!res.ok) {
            const result: DiagnosticStep = {
              ...step,
              status: 'error',
              latencyMs: elapsed,
              details: `HTTP ${res.status}: ${res.statusText}`,
            }
            results.push(result)
            setSteps(prev => prev.map((s, idx) =>
              idx === i ? result : s
            ))
            continue
          }

          const data = await res.json()
          const elapsed2 = Date.now() - startTime

          // Determine status based on endpoint
          let status: 'success' | 'warning' = 'success'
          let details = ''

          if (step.id === 'database') {
            const agentCount = (data.agents ?? []).length
            details = `Connected. ${agentCount} agents, schema valid.`
          } else if (step.id === 'api') {
            const modelCount = (data.models ?? []).length
            details = `All endpoints responsive. ${modelCount} models registered.`
          } else if (step.id === 'models') {
            const models = data.models ?? []
            const activeCount = models.filter((m: any) => m.isActive).length
            const inactiveCount = models.length - activeCount
            if (inactiveCount > 0) {
              status = 'warning'
              details = `${activeCount}/${models.length} models active. ${inactiveCount} inactive.`
            } else {
              details = `All ${models.length} models active and healthy.`
            }
          } else if (step.id === 'agents') {
            const agents = data.agents ?? []
            const lowTrust = agents.filter((a: any) => a.trustScore < 0.7)
            if (lowTrust.length > 0) {
              status = 'warning'
              details = `${agents.length} agents. ${lowTrust.length} below trust threshold (0.7).`
            } else {
              details = `${agents.length} agents, all above trust threshold.`
            }
          } else if (step.id === 'tokens') {
            const budget = data.budget
            const remaining = budget?.tokensRemaining ?? 0
            const max = budget?.tokensMax ?? 100000
            const utilization = Math.round((1 - remaining / max) * 100)
            if (utilization > 80) {
              status = 'warning'
              details = `Budget ${utilization}% utilized. ${remaining.toLocaleString()} tokens remaining.`
            } else {
              details = `Budget ${utilization}% utilized. ${remaining.toLocaleString()} tokens remaining.`
            }
          }

          const result: DiagnosticStep = {
            ...step,
            status,
            latencyMs: elapsed2,
            details,
          }
          results.push(result)
          setSteps(prev => prev.map((s, idx) =>
            idx === i ? result : s
          ))
        }
      } catch {
        const elapsed = Date.now() - startTime
        const result: DiagnosticStep = {
          ...step,
          status: 'error',
          latencyMs: elapsed,
          details: 'Connection failed — endpoint unreachable',
        }
        results.push(result)
        setSteps(prev => prev.map((s, idx) =>
          idx === i ? result : s
        ))
      }
    }

    // Calculate overall health score
    const successCount = results.filter(r => r.status === 'success').length
    const warningCount = results.filter(r => r.status === 'warning').length
    const errorCount = results.filter(r => r.status === 'error').length
    const score = Math.round(((successCount * 100 + warningCount * 60 + errorCount * 0) / results.length))
    setOverallScore(score)
    setRunning(false)

    if (score >= 80) {
      toast.success('Diagnostics complete', { description: `System health: ${score}%` })
    } else if (score >= 50) {
      toast.warning('Diagnostics complete', { description: `System health: ${score}% — some issues detected` })
    } else {
      toast.error('Diagnostics complete', { description: `System health: ${score}% — critical issues found` })
    }
  }, [])

  // Auto-run on open
  useEffect(() => {
    if (open && steps.every(s => s.status === 'pending')) {
      runDiagnostics()
    }
  }, [open])

  const scoreColor = overallScore !== null
    ? overallScore >= 80 ? 'text-emerald-600 dark:text-emerald-400'
    : overallScore >= 50 ? 'text-yellow-600 dark:text-yellow-400'
    : 'text-red-600 dark:text-red-400'
    : ''

  const scoreBg = overallScore !== null
    ? overallScore >= 80 ? 'border-emerald-600/20 bg-emerald-600/5'
    : overallScore >= 50 ? 'border-yellow-600/20 bg-yellow-600/5'
    : 'border-red-600/20 bg-red-600/5'
    : 'border-border'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="space-y-4"
    >
      {/* Header with Overall Score */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/15 shadow-lg shadow-emerald-600/10">
            <Wrench className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">System Diagnostics</h3>
            <p className="text-[10px] text-muted-foreground">Step-by-step health verification</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {running && (
            <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px] gap-1 animate-pulse">
              <Loader2 className="h-3 w-3 animate-spin" /> Running
            </Badge>
          )}
          {overallScore !== null && !running && (
            <Badge className={`border-0 text-[9px] font-bold ${
              overallScore >= 80 ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400' :
              overallScore >= 50 ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400' :
              'bg-red-600/15 text-red-600 dark:text-red-400'
            }`}>
              Score: {overallScore}%
            </Badge>
          )}
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-[10px] gap-1"
            onClick={runDiagnostics}
            disabled={running}
          >
            {running ? <Loader2 className="h-3 w-3 animate-spin" /> : <Wrench className="h-3 w-3" />}
            {running ? 'Running...' : 'Re-run'}
          </Button>
        </div>
      </div>

      {/* Overall Score Card */}
      {overallScore !== null && !running && (
        <Card className={`relative overflow-hidden ${scoreBg}`}>
          <CardContent className="relative p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Overall Health Score</p>
                <p className={`text-4xl font-bold tabular-nums ${scoreColor}`}>
                  {overallScore}%
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <div className="flex items-center gap-2 text-[10px]">
                  <span className="flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" /> {steps.filter(s => s.status === 'success').length} passed</span>
                  <span className="flex items-center gap-1"><AlertTriangle className="h-3 w-3 text-yellow-600 dark:text-yellow-400" /> {steps.filter(s => s.status === 'warning').length} warnings</span>
                  <span className="flex items-center gap-1"><XCircle className="h-3 w-3 text-red-600 dark:text-red-400" /> {steps.filter(s => s.status === 'error').length} errors</span>
                </div>
                <Progress
                  value={overallScore}
                  className={`h-2 w-40 ${
                    overallScore >= 80 ? '[&>div]:bg-emerald-600 dark:[&>div]:bg-emerald-400' :
                    overallScore >= 50 ? '[&>div]:bg-yellow-600 dark:[&>div]:bg-yellow-400' :
                    '[&>div]:bg-red-600 dark:[&>div]:bg-red-400'
                  }`}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Diagnostic Steps */}
      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {steps.map((step, idx) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="group"
            >
              <Card className={`relative overflow-hidden transition-all duration-200 cursor-pointer ${
                step.status === 'success' ? 'border-emerald-600/15' :
                step.status === 'warning' ? 'border-yellow-600/15' :
                step.status === 'error' ? 'border-red-600/15' :
                step.status === 'running' ? 'border-emerald-600/30 animate-pulse-subtle' :
                'border-border'
              }`}
                onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
              >
                <CardContent className="relative p-3">
                  <div className="flex items-center gap-3">
                    {/* Status Icon */}
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                      step.status === 'success' ? 'bg-emerald-600/10' :
                      step.status === 'warning' ? 'bg-yellow-600/10' :
                      step.status === 'error' ? 'bg-red-600/10' :
                      step.status === 'running' ? 'bg-emerald-600/10' :
                      'bg-muted/30'
                    }`}>
                      {step.status === 'running' ? (
                        <Loader2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 animate-spin" />
                      ) : step.status === 'success' ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      ) : step.status === 'warning' ? (
                        <Shield className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                      ) : step.status === 'error' ? (
                        <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                      ) : (
                        <step.icon className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>

                    {/* Step Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">{step.name}</span>
                        {step.status !== 'pending' && step.status !== 'running' && (
                          <Badge variant="outline" className={`text-[8px] h-4 px-1.5 ${
                            step.status === 'success' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' :
                            step.status === 'warning' ? 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400' :
                            'border-red-600/30 text-red-600 dark:text-red-400'
                          }`}>
                            {step.status === 'success' ? '✅ PASS' : step.status === 'warning' ? '⚠️ WARN' : '❌ FAIL'}
                          </Badge>
                        )}
                      </div>
                      <p className="text-[10px] text-muted-foreground">{step.description}</p>
                    </div>

                    {/* Timing */}
                    {step.latencyMs !== null && (
                      <span className="text-[10px] text-muted-foreground tabular-nums shrink-0">{step.latencyMs}ms</span>
                    )}

                    {/* Expand chevron */}
                    {step.details && (
                      expandedStep === step.id
                        ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                        : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    )}
                  </div>

                  {/* Expanded Details */}
                  <AnimatePresence>
                    {expandedStep === step.id && step.details && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="mt-2 rounded-md bg-accent/30 px-3 py-2 text-[11px] text-muted-foreground">
                          {step.details}
                        </div>
                        {step.apiEndpoint && (
                          <p className="mt-1 text-[9px] text-muted-foreground/50">
                            Endpoint: {step.apiEndpoint}
                          </p>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
