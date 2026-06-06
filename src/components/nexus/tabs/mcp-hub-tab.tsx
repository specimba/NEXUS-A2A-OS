'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Plug, Radio, BarChart3, Settings2, Network } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import useSWR from 'swr'
import { ConnectionsPanel } from '../mcp/connections-panel'
import { EventStreamPanel } from '../mcp/event-stream-panel'
import { AnalyticsPanel } from '../mcp/analytics-panel'
import { SettingsPanel } from '../mcp/settings-panel'

interface ConnectionLite {
  id: string
  status: string
}

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function McpHubTab() {
  const [view, setView] = useState('connections')
  // Header-level live count — drives the connected badge and pulse dot.
  const { data: connections = [] } = useSWR<ConnectionLite[]>('/api/mcp/connections', fetcher, {
    refreshInterval: 5000,
  })
  const liveCount = connections.filter((c) => c.status === 'connected').length

  return (
    <div className="p-6 space-y-5 grid-pattern-animated">
      <motion.header
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-start justify-between flex-wrap gap-3"
      >
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-600/20">
            <Network className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">MCP Hub</h1>
            <p className="text-sm text-muted-foreground">
              Aggregate real-time Model Context Protocol streams and surface UI/UX insights via PostHog.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="gap-1.5 font-mono text-[11px] border-emerald-500/40 bg-emerald-500/5 text-emerald-500"
          >
            <span className="relative flex h-2 w-2">
              {liveCount > 0 && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              )}
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            {liveCount} live / {connections.length} total
          </Badge>
        </div>
      </motion.header>

      <Tabs value={view} onValueChange={setView}>
        <TabsList className="grid w-full grid-cols-2 md:w-auto md:inline-grid md:grid-cols-4">
          <TabsTrigger value="connections" className="gap-1.5">
            <Plug className="h-3.5 w-3.5" /> Connections
          </TabsTrigger>
          <TabsTrigger value="stream" className="gap-1.5">
            <Radio className="h-3.5 w-3.5" /> Live Events
          </TabsTrigger>
          <TabsTrigger value="analytics" className="gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" /> Analytics
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-1.5">
            <Settings2 className="h-3.5 w-3.5" /> Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="connections" className="mt-4">
          <ConnectionsPanel />
        </TabsContent>
        <TabsContent value="stream" className="mt-4">
          <EventStreamPanel />
        </TabsContent>
        <TabsContent value="analytics" className="mt-4">
          <AnalyticsPanel />
        </TabsContent>
        <TabsContent value="settings" className="mt-4">
          <SettingsPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
