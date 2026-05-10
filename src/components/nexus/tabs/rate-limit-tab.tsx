'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Gauge,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
  Activity,
} from 'lucide-react'

const providerQuotas = [
  { name: 'OpenRouter', requestsMin: { used: 142, total: 300 }, requestsDay: { used: 4523, total: 10000 }, tokensMin: { used: 12400, total: 30000 }, status: 'ok' },
  { name: 'Google AI', requestsMin: { used: 45, total: 60 }, requestsDay: { used: 2340, total: 5000 }, tokensMin: { used: 8200, total: 10000 }, status: 'caution' },
  { name: 'Groq', requestsMin: { used: 23, total: 30 }, requestsDay: { used: 1890, total: 3000 }, tokensMin: { used: 5400, total: 8000 }, status: 'caution' },
  { name: 'Together AI', requestsMin: { used: 28, total: 30 }, requestsDay: { used: 4210, total: 5000 }, tokensMin: { used: 9100, total: 10000 }, status: 'limited' },
]

const rateLimitLogs = [
  { time: '2m ago', provider: 'Together AI', type: '429 Too Many Requests', resolved: true, retryAfter: '5s' },
  { time: '8m ago', provider: 'Google AI', type: 'Quota Warning (75%)', resolved: true, retryAfter: '-' },
  { time: '15m ago', provider: 'Together AI', type: '429 Too Many Requests', resolved: true, retryAfter: '3s' },
  { time: '22m ago', provider: 'Groq', type: 'Quota Warning (70%)', resolved: true, retryAfter: '-' },
  { time: '45m ago', provider: 'Together AI', type: '429 Too Many Requests', resolved: true, retryAfter: '8s' },
  { time: '1h ago', provider: 'OpenRouter', type: 'Rate limit approaching', resolved: true, retryAfter: '-' },
]

const rateLimitStatus = {
  ok: { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-600/10', label: 'OK' },
  caution: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-600/10', label: 'Caution' },
  limited: { icon: XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-600/10', label: 'Limited' },
}

export function RateLimitTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Gauge className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
        <h2 className="text-lg font-semibold">Rate Limit Control Center</h2>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">1</div>
            <div className="text-xs text-muted-foreground">OK</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">2</div>
            <div className="text-xs text-muted-foreground">Caution</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">1</div>
            <div className="text-xs text-muted-foreground">Limited</div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-border/50">
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">3</div>
            <div className="text-xs text-muted-foreground">429s Today</div>
          </CardContent>
        </Card>
      </div>

      {/* Provider Quotas */}
      <div className="space-y-4">
        {providerQuotas.map((provider) => {
          const status = rateLimitStatus[provider.status as keyof typeof rateLimitStatus]
          const StatusIcon = status.icon
          return (
            <Card key={provider.name} className="bg-card/50 border-border/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <StatusIcon className={`h-4 w-4 ${status.color}`} />
                    <span className="text-sm font-bold">{provider.name}</span>
                  </div>
                  <Badge className={`text-[10px] border-0 ${status.bg} ${status.color}`}>
                    {status.label}
                  </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Requests/min */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground">Requests / min</span>
                      <span className="font-mono">{provider.requestsMin.used} / {provider.requestsMin.total}</span>
                    </div>
                    <Progress
                      value={(provider.requestsMin.used / provider.requestsMin.total) * 100}
                      className={`h-1.5 ${provider.requestsMin.used / provider.requestsMin.total > 0.85 ? '[&>div]:bg-red-500' : provider.requestsMin.used / provider.requestsMin.total > 0.7 ? '[&>div]:bg-yellow-500' : ''}`}
                    />
                  </div>

                  {/* Requests/day */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground">Requests / day</span>
                      <span className="font-mono">{provider.requestsDay.used.toLocaleString()} / {provider.requestsDay.total.toLocaleString()}</span>
                    </div>
                    <Progress
                      value={(provider.requestsDay.used / provider.requestsDay.total) * 100}
                      className={`h-1.5 ${provider.requestsDay.used / provider.requestsDay.total > 0.85 ? '[&>div]:bg-red-500' : provider.requestsDay.used / provider.requestsDay.total > 0.7 ? '[&>div]:bg-yellow-500' : ''}`}
                    />
                  </div>

                  {/* Tokens/min */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-muted-foreground">Tokens / min</span>
                      <span className="font-mono">{provider.tokensMin.used.toLocaleString()} / {provider.tokensMin.total.toLocaleString()}</span>
                    </div>
                    <Progress
                      value={(provider.tokensMin.used / provider.tokensMin.total) * 100}
                      className={`h-1.5 ${provider.tokensMin.used / provider.tokensMin.total > 0.85 ? '[&>div]:bg-red-500' : provider.tokensMin.used / provider.tokensMin.total > 0.7 ? '[&>div]:bg-yellow-500' : ''}`}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Rate Limit Log */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Rate Limit Log
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {rateLimitLogs.map((log, i) => (
              <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-muted/30">
                {log.type.includes('429') ? (
                  <XCircle className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0" />
                ) : (
                  <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                )}
                <span className="text-sm">{log.provider}</span>
                <Badge
                  className={`text-[9px] h-4 border-0 ${
                    log.type.includes('429')
                      ? 'bg-red-600/20 text-red-600 dark:text-red-400'
                      : 'bg-yellow-600/20 text-yellow-600 dark:text-yellow-400'
                  }`}
                >
                  {log.type}
                </Badge>
                {log.resolved ? (
                  <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <XCircle className="h-3 w-3 text-red-600 dark:text-red-400" />
                )}
                <span className="flex-1" />
                {log.retryAfter !== '-' && (
                  <span className="text-[10px] text-muted-foreground">Retry: {log.retryAfter}</span>
                )}
                <span className="text-[10px] text-muted-foreground">{log.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Throttle Config */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Throttle Strategy
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg bg-muted/30 space-y-1">
              <div className="text-xs font-semibold">Backoff Strategy</div>
              <div className="text-sm">Exponential (1s → 2s → 4s → 8s)</div>
            </div>
            <div className="p-3 rounded-lg bg-muted/30 space-y-1">
              <div className="text-xs font-semibold">Max Retries</div>
              <div className="text-sm">3 retries per request</div>
            </div>
            <div className="p-3 rounded-lg bg-muted/30 space-y-1">
              <div className="text-xs font-semibold">Circuit Breaker</div>
              <div className="text-sm">Open after 5 consecutive failures</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
