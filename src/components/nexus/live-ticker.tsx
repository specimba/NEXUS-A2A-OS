'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  CheckCircle2,
  Radio,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Activity,
} from 'lucide-react'
import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const initialActivities = [
  { event: 'Agent worker-3 completed task T-0847', type: 'success' as const },
  { event: 'GMR rotated to trinity-large-preview', type: 'info' as const },
  { event: 'Governor ALLOWED read file (scope: SELF)', type: 'info' as const },
  { event: 'Vault stored TRUST entry for agent-alpha', type: 'success' as const },
  { event: 'StressLab test ISC-023 completed: PASS', type: 'success' as const },
  { event: 'TokenGuard budget check: 73,450 remaining', type: 'info' as const },
  { event: 'Swarm worker-1 status: ERROR → recovering', type: 'warning' as const },
]

const newActivities = [
  { event: 'Model kimi-k2.5 health check: 92%', type: 'info' as const },
  { event: 'Agent worker-3 started task T-0850', type: 'info' as const },
  { event: 'GMR pool FAST: all models healthy', type: 'success' as const },
  { event: 'Vault stored CAP entry: skill.registered', type: 'success' as const },
  { event: 'Governor HELD research-agent: API call (CROSS)', type: 'warning' as const },
  { event: 'TokenTracker: 1,240 tokens consumed by qwen3-coder', type: 'info' as const },
  { event: 'Swarm worker-4 now idle, ready for assignment', type: 'success' as const },
  { event: 'Bridge: new HMAC session established', type: 'info' as const },
  { event: 'OPUSman v6.0 delegation: 847 tokens saved', type: 'success' as const },
  { event: 'Model Arena: deepseek-r1 vs qwen2.5-coder match started', type: 'info' as const },
]

function ActivityIcon({ type }: { type: 'success' | 'info' | 'warning' }) {
  if (type === 'success') return <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-600 dark:text-emerald-400" />
  if (type === 'info') return <Radio className="h-3 w-3 shrink-0 text-blue-600 dark:text-blue-400" />
  return <AlertTriangle className="h-3 w-3 shrink-0 text-orange-600 dark:text-orange-400" />
}

export function LiveTicker() {
  const [activities, setActivities] = useState(initialActivities)
  const [expanded, setExpanded] = useState(false)
  const [newCount, setNewCount] = useState(0)
  const tickRef = useRef(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const interval = setInterval(() => {
      tickRef.current++
      const newItem = newActivities[tickRef.current % newActivities.length]
      setActivities((prev) => [
        { ...newItem, time: Date.now() },
        ...prev.slice(0, 19),
      ])
      setNewCount((prev) => prev + 1)
    }, 3500)
    return () => clearInterval(interval)
  }, [])

  // Auto-scroll ticker for collapsed view
  const [tickerIndex, setTickerIndex] = useState(0)
  useEffect(() => {
    if (expanded) return
    const interval = setInterval(() => {
      setTickerIndex((prev) => (prev + 1) % Math.min(5, activities.length))
    }, 4000)
    return () => clearInterval(interval)
  }, [expanded, activities.length])

  const toggleExpand = () => {
    setExpanded((prev) => !prev)
    setNewCount(0)
  }

  const displayedActivities = activities.slice(0, expanded ? 8 : 1)

  return (
    <div className="relative border-b border-border/40 bg-white/90 dark:bg-card/90 backdrop-blur-md z-10">
      <div className="flex items-center h-9 px-4">
        {/* LIVE indicator */}
        <div className="flex items-center gap-2 mr-4 shrink-0">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
            Live
          </span>
        </div>

        {/* Activity content */}
        <div className="flex-1 min-w-0 overflow-hidden">
          <AnimatePresence mode="wait">
            {!expanded ? (
              <motion.div
                key={tickerIndex}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-2"
              >
                {activities[tickerIndex] && (
                  <>
                    <ActivityIcon type={activities[tickerIndex].type} />
                    <span className="text-xs text-muted-foreground truncate">
                      {activities[tickerIndex].event}
                    </span>
                  </>
                )}
              </motion.div>
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                ref={scrollRef}
                className="max-h-[180px] overflow-y-auto space-y-0.5 custom-scrollbar py-0.5"
              >
                {displayedActivities.map((item, i) => (
                  <div
                    key={`${item.event}-${i}`}
                    className={`flex items-center gap-2 rounded px-2 py-0.5 text-xs transition-colors ${
                      i === 0 ? 'bg-emerald-600/5' : ''
                    }`}
                  >
                    <ActivityIcon type={item.type} />
                    <span className="flex-1 text-muted-foreground truncate">{item.event}</span>
                    <span className="shrink-0 text-[9px] text-muted-foreground/40 tabular-nums">
                      {i === 0 ? 'now' : `${i * 3}s`}
                    </span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right side: count + toggle */}
        <div className="flex items-center gap-2 ml-3 shrink-0">
          {newCount > 0 && !expanded && (
            <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px] px-1.5 py-0 h-5">
              {newCount} new
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
            onClick={toggleExpand}
            aria-label={expanded ? 'Collapse live ticker' : 'Expand live ticker'}
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>
    </div>
  )
}
