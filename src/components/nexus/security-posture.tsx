'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Key,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Scan,
  FileCheck,
  Clock,
  Eye,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'

// ─── Types ───

interface VulnerabilityItem {
  id: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  component: string
  description: string
  status: 'Open' | 'Fixed' | 'Mitigated'
  discovered: string
}

interface ComplianceItem {
  name: string
  passed: boolean
  details: string
}

type ThreatLevel = 'MINIMAL' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'

// ─── Data ───

const vulnerabilities: VulnerabilityItem[] = [
  { id: 'VULN-0042', severity: 'CRITICAL', component: 'Agent Bridge', description: 'Unauthenticated agent registration endpoint', status: 'Open', discovered: '2h ago' },
  { id: 'VULN-0041', severity: 'HIGH', component: 'Token Router', description: 'Rate limit bypass via concurrent requests', status: 'Mitigated', discovered: '6h ago' },
  { id: 'VULN-0040', severity: 'MEDIUM', component: 'Vault Chain', description: 'Hash collision risk in legacy entries', status: 'Fixed', discovered: '1d ago' },
  { id: 'VULN-0039', severity: 'HIGH', component: 'Governor API', description: 'Trust threshold modification without audit log', status: 'Open', discovered: '2d ago' },
  { id: 'VULN-0038', severity: 'LOW', component: 'Research Queue', description: 'Paper metadata not sanitized on import', status: 'Fixed', discovered: '3d ago' },
]

const complianceItems: ComplianceItem[] = [
  { name: 'Constitution Rules', passed: true, details: 'All 8 rules active and enforced' },
  { name: 'Agent Isolation', passed: true, details: 'Process sandbox verified for all agents' },
  { name: 'Token Limits', passed: true, details: 'Session budget within 80% threshold' },
  { name: 'Trust Thresholds', passed: false, details: 'Agent worker-2 below minimum trust score' },
  { name: 'Audit Logging', passed: true, details: 'All write operations logged with HMAC' },
  { name: 'Encryption', passed: true, details: 'TLS 1.3 + AES-256 active on all channels' },
]

const threatLevelConfig: Record<ThreatLevel, { color: string; bgColor: string; textColor: string; pulseColor: string }> = {
  MINIMAL: { color: '#10b981', bgColor: 'bg-emerald-600/15', textColor: 'text-emerald-600 dark:text-emerald-400', pulseColor: 'bg-emerald-400' },
  LOW: { color: '#22c55e', bgColor: 'bg-green-600/15', textColor: 'text-green-600 dark:text-green-400', pulseColor: 'bg-green-400' },
  MODERATE: { color: '#eab308', bgColor: 'bg-yellow-600/15', textColor: 'text-yellow-600 dark:text-yellow-400', pulseColor: 'bg-yellow-400' },
  HIGH: { color: '#f97316', bgColor: 'bg-orange-600/15', textColor: 'text-orange-600 dark:text-orange-400', pulseColor: 'bg-orange-400' },
  CRITICAL: { color: '#ef4444', bgColor: 'bg-red-600/15', textColor: 'text-red-600 dark:text-red-400', pulseColor: 'bg-red-400' },
}

const severityConfig: Record<string, { bgColor: string; textColor: string }> = {
  CRITICAL: { bgColor: 'bg-red-600/15', textColor: 'text-red-600 dark:text-red-400' },
  HIGH: { bgColor: 'bg-orange-600/15', textColor: 'text-orange-600 dark:text-orange-400' },
  MEDIUM: { bgColor: 'bg-yellow-600/15', textColor: 'text-yellow-600 dark:text-yellow-400' },
  LOW: { bgColor: 'bg-blue-600/15', textColor: 'text-blue-600 dark:text-blue-400' },
}

const statusConfig: Record<string, { bgColor: string; textColor: string }> = {
  Open: { bgColor: 'bg-red-600/15', textColor: 'text-red-600 dark:text-red-400' },
  Mitigated: { bgColor: 'bg-yellow-600/15', textColor: 'text-yellow-600 dark:text-yellow-400' },
  Fixed: { bgColor: 'bg-emerald-600/15', textColor: 'text-emerald-600 dark:text-emerald-400' },
}

// ─── SVG Security Gauge ───

function SecurityGauge({ score }: { score: number }) {
  const [animatedScore, setAnimatedScore] = useState(0)
  const radius = 70
  const strokeWidth = 10
  const circumference = 2 * Math.PI * radius

  useEffect(() => {
    let frame: number
    const start = animatedScore
    const duration = 1500
    const startTime = performance.now()

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setAnimatedScore(Math.round(start + (score - start) * eased))
      if (progress < 1) {
        frame = requestAnimationFrame(animate)
      }
    }

    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [score, animatedScore])

  const offset = circumference - (animatedScore / 100) * circumference

  const getScoreColor = (s: number) => {
    if (s >= 90) return '#3b82f6'
    if (s >= 70) return '#10b981'
    if (s >= 40) return '#eab308'
    return '#ef4444'
  }

  const getScoreLabel = (s: number) => {
    if (s >= 90) return 'Excellent'
    if (s >= 70) return 'Good'
    if (s >= 40) return 'Warning'
    return 'Critical'
  }

  const color = getScoreColor(animatedScore)

  return (
    <div className="relative flex flex-col items-center">
      <svg width="180" height="180" viewBox="0 0 180 180">
        {/* Background ring */}
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-muted/20"
        />
        {/* Score ring */}
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 90 90)"
          style={{ transition: 'stroke 0.3s ease' }}
        />
        {/* Center text */}
        <text
          x="90"
          y="82"
          textAnchor="middle"
          className="fill-foreground"
          fontSize="36"
          fontWeight="bold"
          fontFamily="var(--font-mono), monospace"
        >
          {animatedScore}
        </text>
        <text
          x="90"
          y="105"
          textAnchor="middle"
          className="fill-muted-foreground"
          fontSize="12"
          fontFamily="var(--font-sans), sans-serif"
        >
          {getScoreLabel(animatedScore)}
        </text>
      </svg>
    </div>
  )
}

// ─── Main Component ───

export function SecurityPosture() {
  const [scanRunning, setScanRunning] = useState(false)
  const [securityScore] = useState(78)
  const [threatLevel] = useState<ThreatLevel>('LOW')
  const [selectedVuln, setSelectedVuln] = useState<string | null>(null)

  const threatConfig = threatLevelConfig[threatLevel]
  const passedCount = complianceItems.filter((c) => c.passed).length
  const compliancePct = Math.round((passedCount / complianceItems.length) * 100)

  const openVulns = useMemo(() => vulnerabilities.filter((v) => v.status === 'Open').length, [])

  const handleRunScan = () => {
    setScanRunning(true)
    toast.info('Security scan initiated', { description: 'Scanning all NEXUS OS modules...' })
    setTimeout(() => {
      setScanRunning(false)
      toast.success('Security scan complete', { description: `${openVulns} open vulnerabilities found` })
    }, 3000)
  }

  const handleVulnClick = (vuln: VulnerabilityItem) => {
    setSelectedVuln(vuln.id)
    toast.info(`Vulnerability ${vuln.id}`, {
      description: `${vuln.severity}: ${vuln.description} — Status: ${vuln.status}`,
      duration: 5000,
    })
    setTimeout(() => setSelectedVuln(null), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Security Score + Threat Level */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Security Score Gauge */}
        <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-blue-600/5" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Security Posture Score
            </CardTitle>
          </CardHeader>
          <CardContent className="relative flex flex-col items-center py-4">
            <SecurityGauge score={securityScore} />
            <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-blue-500" />
                <span>Excellent (90+)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span>Good (70-89)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-yellow-500" />
                <span>Warning (40-69)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-red-500" />
                <span>Critical (&lt;40)</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Threat Level + Encryption */}
        <div className="space-y-4">
          {/* Threat Level */}
          <Card className="relative overflow-hidden border-yellow-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-yellow-600/5 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                  <span className="text-sm font-medium">Threat Level</span>
                </div>
                <Badge className={`border-0 text-[10px] gap-1 ${threatConfig.bgColor} ${threatConfig.textColor}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${threatConfig.pulseColor} animate-pulse`} />
                  {threatLevel}
                </Badge>
              </div>
              <div className="flex gap-1 mt-2">
                {(['MINIMAL', 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'] as ThreatLevel[]).map((level) => (
                  <div
                    key={level}
                    className={`h-2 flex-1 rounded-full transition-colors ${
                      threatLevel === level
                        ? threatConfig.bgColor
                        : 'bg-muted/30'
                    }`}
                    style={threatLevel === level ? { backgroundColor: threatLevelConfig[level].color + '30' } : {}}
                  />
                ))}
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground">
                <Clock className="h-3 w-3 inline mr-1" />
                Last assessed: 5 minutes ago
              </p>
            </CardContent>
          </Card>

          {/* Encryption Status */}
          <Card className="relative overflow-hidden border-blue-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              <div className="flex items-center gap-2 mb-3">
                <Lock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-medium">Encryption Status</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Transport</span>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                    <span className="font-mono text-[10px]">TLS 1.3</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Vault</span>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                    <span className="font-mono text-[10px]">AES-256</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Key Rotation</span>
                  <div className="flex items-center gap-1.5">
                    <Key className="h-3 w-3 text-blue-500" />
                    <span className="font-mono text-[10px]">12h ago</span>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Cert Expiry</span>
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-3 w-3 text-yellow-500" />
                    <span className="font-mono text-[10px]">89 days</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Vulnerability Scan + Compliance */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Vulnerability Scan Results */}
        <Card className="relative overflow-hidden border-red-600/15 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <Scan className="h-4 w-4 text-red-600 dark:text-red-400" />
                Vulnerability Scan
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-[10px] gap-1"
                onClick={handleRunScan}
                disabled={scanRunning}
              >
                {scanRunning ? (
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  >
                    <Scan className="h-3 w-3" />
                  </motion.span>
                ) : (
                  <Scan className="h-3 w-3" />
                )}
                {scanRunning ? 'Scanning...' : 'Run Scan'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            <div className="max-h-64 overflow-y-auto custom-scrollbar space-y-1.5">
              {vulnerabilities.map((vuln) => {
                const sev = severityConfig[vuln.severity] ?? severityConfig.LOW
                const stat = statusConfig[vuln.status] ?? statusConfig.Open
                const isSelected = selectedVuln === vuln.id

                return (
                  <motion.div
                    key={vuln.id}
                    initial={false}
                    animate={{ backgroundColor: isSelected ? 'rgba(16, 185, 129, 0.05)' : 'transparent' }}
                    className="flex items-center gap-2 p-2 rounded-md hover:bg-accent/50 cursor-pointer transition-colors"
                    onClick={() => handleVulnClick(vuln)}
                  >
                    <Badge className={`text-[8px] border-0 ${sev.bgColor} ${sev.textColor}`}>
                      {vuln.severity}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono text-muted-foreground">{vuln.id}</span>
                        <span className="text-xs font-medium truncate">{vuln.component}</span>
                      </div>
                    </div>
                    <Badge className={`text-[8px] border-0 ${stat.bgColor} ${stat.textColor}`}>
                      {vuln.status}
                    </Badge>
                    <Eye className="h-3 w-3 text-muted-foreground shrink-0" />
                  </motion.div>
                )
              })}
            </div>
            <div className="mt-3 flex items-center gap-3 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                {openVulns} open
              </span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-yellow-500" />
                {vulnerabilities.filter((v) => v.status === 'Mitigated').length} mitigated
              </span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {vulnerabilities.filter((v) => v.status === 'Fixed').length} fixed
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Compliance Checklist */}
        <Card className="relative overflow-hidden border-emerald-600/15 hover-lift">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/3 via-transparent to-transparent" />
          <CardHeader className="relative pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Compliance Checklist
            </CardTitle>
          </CardHeader>
          <CardContent className="relative p-4 pt-0">
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Overall Compliance</span>
                <span className="text-xs font-bold tabular-nums">{compliancePct}%</span>
              </div>
              <Progress value={compliancePct} className="h-2" />
            </div>
            <div className="space-y-2">
              {complianceItems.map((item) => (
                <div
                  key={item.name}
                  className="flex items-start gap-2 p-2 rounded-md hover:bg-accent/30 transition-colors"
                >
                  {item.passed ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium">{item.name}</span>
                      <Badge
                        className={`text-[8px] border-0 ${
                          item.passed
                            ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                            : 'bg-red-600/15 text-red-600 dark:text-red-400'
                        }`}
                      >
                        {item.passed ? 'PASS' : 'FAIL'}
                      </Badge>
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{item.details}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
