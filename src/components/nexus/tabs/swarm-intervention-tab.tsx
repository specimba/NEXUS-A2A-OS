'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Swords,
  Pause,
  Play,
  XCircle,
  RefreshCw,
  Send,
  AlertTriangle,
  Loader2,
} from 'lucide-react'
import { toast } from 'sonner'


interface Intervention {
  id: string
  type: 'pause' | 'resume' | 'terminate' | 'redirect'
  target: string
  status: 'pending' | 'executed' | 'failed'
  timestamp: string
}


export function SwarmInterventionTab() {
  const [intervention, setIntervention] = useState('')
  const [targetAgent, setTargetAgent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [recentInterventions] = useState<Intervention[]>([])

  const handleSubmit = async () => {
    if (!intervention.trim() || !targetAgent.trim()) {
      toast.error('Missing fields', { description: 'Both intervention and target are required.' })
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/nexusclaw/intervene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intervention: intervention.trim(), target: targetAgent.trim() }),
      })
      if (res.ok) {
        toast.success('Intervention submitted', { description: 'Swarm coordinator notified.' })
        setIntervention('')
        setTargetAgent('')
      } else {
        toast.error('Intervention failed', { description: (await res.json()).error })
      }
    } catch {
      toast.error('Network error', { description: 'Could not reach intervention API.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-red-600 to-orange-600">
          <Swords className="h-5 w-5 text-white" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Swarm Intervention Panel</h2>
          <p className="text-sm text-muted-foreground">Operator intervention in live swarms</p>
        </div>
      </div>

      {/* Intervention Form */}
      <Card className="border-red-600/20">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            Submit Intervention
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label className="text-xs font-medium">Target Agent ID</Label>
            <input
              type="text"
              placeholder="agent-123abc..."
              value={targetAgent}
              onChange={(e) => setTargetAgent(e.target.value)}
              className="w-full px-3 py-2 text-sm border rounded-md bg-background"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium">Intervention Command</Label>
            <Textarea
              placeholder="e.g. PAUSE, RESUME, TERMINATE, REDIRECT operations"
              value={intervention}
              onChange={(e) => setIntervention(e.target.value)}
              rows={3}
              className="text-xs resize-none"
            />
          </div>

          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-red-600/30 text-red-600"
              onClick={() => setIntervention('PAUSE')}
            >
              <Pause className="h-3.5 w-3.5" />
              Pause
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-emerald-600/30 text-emerald-600"
              onClick={() => setIntervention('RESUME')}
            >
              <Play className="h-3.5 w-3.5" />
              Resume
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-red-600/30 text-red-600"
              onClick={() => setIntervention('TERMINATE')}
            >
              <XCircle className="h-3.5 w-3.5" />
              Terminate
            </Button>
          </div>

          <Button
            size="sm"
            className="w-full gap-1.5 bg-gradient-to-r from-red-600 to-orange-600 text-white"
            onClick={handleSubmit}
            disabled={submitting || !intervention.trim() || !targetAgent.trim()}
          >
            {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            Submit Intervention
          </Button>
        </CardContent>
      </Card>

      {/* Recent Interventions */}
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
            Recent Interventions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recentInterventions.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">No recent interventions</p>
          ) : (
            <div className="space-y-2">
              {recentInterventions.map((int) => (
                <div key={int.id} className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/30 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Badge className="text-[9px]">
                      {int.type.toUpperCase()}
                    </Badge>
                    <span className="text-xs font-mono">{int.target}</span>
                  </div>
                  <Badge className={cn(
                    'text-[9px]',
                    int.status === 'executed' ? 'bg-emerald-600/15 text-emerald-600' :
                    int.status === 'pending' ? 'bg-yellow-600/15 text-yellow-600' :
                    'bg-red-600/15 text-red-600',
                  )}>
                    {int.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

import { cn } from '@/lib/utils'