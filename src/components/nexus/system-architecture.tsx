'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import {
  Zap,
  Router,
  Shield,
  Database,
  FlaskConical,
  Bug,
  Activity,
  Settings,
  Hexagon,
} from 'lucide-react'

const defaultPillars = [
  { name: 'Bridge', icon: Zap, health: 100, color: '#34d399', angle: 0, desc: 'HMAC auth · JSON-RPC' },
  { name: 'Engine', icon: Router, health: 98, color: '#60a5fa', angle: 45, desc: 'Hermes intent routing' },
  { name: 'Governor', icon: Shield, health: 95, color: '#f87171', angle: 90, desc: 'Kaiju + TrustScorer' },
  { name: 'Vault', icon: Database, health: 100, color: '#a78bfa', angle: 135, desc: '5-Track memory' },
  { name: 'GMR', icon: FlaskConical, health: 92, color: '#fb923c', angle: 180, desc: 'Model rotation' },
  { name: 'Swarm', icon: Bug, health: 88, color: '#facc15', angle: 225, desc: 'Worker pool' },
  { name: 'Monitor', icon: Activity, health: 96, color: '#f472b6', angle: 270, desc: 'Token budget + audit' },
  { name: 'Config', icon: Settings, health: 100, color: '#34d399', angle: 315, desc: 'Constitution' },
]

interface PillarData {
  name: string
  health: number
  status?: string
  desc?: string
  uptime?: string
}

interface SystemArchitectureProps {
  pillarsData?: PillarData[]
  onPillarClick?: (pillarName: string) => void
  showDataSource?: boolean
  compact?: boolean
}

export function SystemArchitecture({ pillarsData, onPillarClick, showDataSource = true, compact = false }: SystemArchitectureProps) {
  // Merge API pillar data into the default pillars (preserving icons, colors, angles)
  const pillars = defaultPillars.map(dp => {
    const apiPillar = pillarsData?.find(p => p.name === dp.name)
    if (apiPillar) {
      return { ...dp, health: apiPillar.health }
    }
    return dp
  })
  // Calculate positions in a circle
  const centerX = 200
  const centerY = 200
  const radius = compact ? 120 : 140

  const nodePositions = pillars.map((p) => {
    const rad = ((p.angle - 90) * Math.PI) / 180
    return {
      ...p,
      x: centerX + radius * Math.cos(rad),
      y: centerY + radius * Math.sin(rad),
    }
  })

  const handlePillarClick = (name: string) => {
    if (onPillarClick) onPillarClick(name)
  }

  return (
    <Card className="relative overflow-hidden border-emerald-600/20 shadow-lg shadow-emerald-600/5">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Hexagon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> System Architecture
            {showDataSource && <DataSourceBadge source="api" />}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[9px]">8 Pillars</Badge>
            <Badge variant="outline" className="text-[9px] border-emerald-600/30 text-emerald-600 dark:text-emerald-400">Live Flow</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="flex flex-col items-center">
          <svg
            viewBox="0 0 400 400"
            className={`w-full ${compact ? 'max-w-[320px]' : 'max-w-[400px]'} h-auto`}
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Outer ring glow */}
            <circle
              cx={centerX}
              cy={centerY}
              r={radius + 30}
              fill="none"
              stroke="#34d399"
              strokeWidth="0.5"
              strokeOpacity="0.1"
              strokeDasharray="3 6"
            >
              <animateTransform
                attributeName="transform"
                type="rotate"
                from={`0 ${centerX} ${centerY}`}
                to={`360 ${centerX} ${centerY}`}
                dur="60s"
                repeatCount="indefinite"
              />
            </circle>

            {/* Connection lines from center to each pillar */}
            {nodePositions.map((node, i) => (
              <g key={`line-${node.name}`}>
                <line
                  x1={centerX}
                  y1={centerY}
                  x2={node.x}
                  y2={node.y}
                  stroke={node.color}
                  strokeWidth="1.5"
                  strokeOpacity="0.25"
                />
                {/* Animated data flow dot — deterministic durations to avoid hydration mismatch */}
                <circle r="2.5" fill={node.color} opacity="0.7">
                  <animateMotion
                    dur={`${2 + (i * 0.37) % 2}s`}
                    repeatCount="indefinite"
                    path={`M${centerX},${centerY} L${node.x},${node.y}`}
                  />
                </circle>
                {/* Reverse flow dot */}
                <circle r="2" fill={node.color} opacity="0.4">
                  <animateMotion
                    dur={`${3 + (i * 0.43) % 2}s`}
                    repeatCount="indefinite"
                    path={`M${node.x},${node.y} L${centerX},${centerY}`}
                    begin="1s"
                  />
                </circle>
              </g>
            ))}

            {/* Inter-pillar connections (ring) */}
            {nodePositions.map((node, i) => {
              const next = nodePositions[(i + 1) % nodePositions.length]
              return (
                <line
                  key={`ring-${node.name}`}
                  x1={node.x}
                  y1={node.y}
                  x2={next.x}
                  y2={next.y}
                  stroke="var(--border)"
                  strokeWidth="0.8"
                  strokeOpacity="0.3"
                  strokeDasharray="4 4"
                />
              )
            })}

            {/* Central hub */}
            <circle
              cx={centerX}
              cy={centerY}
              r="36"
              fill="var(--card)"
              stroke="#34d399"
              strokeWidth="2"
              strokeOpacity="0.6"
            />
            <circle
              cx={centerX}
              cy={centerY}
              r="36"
              fill="#34d399"
              fillOpacity="0.08"
            />
            {/* Central hub pulse ring */}
            <circle
              cx={centerX}
              cy={centerY}
              r="36"
              fill="none"
              stroke="#34d399"
              strokeWidth="1"
              strokeOpacity="0.3"
            >
              <animate
                attributeName="r"
                values="36;44;36"
                dur="3s"
                repeatCount="indefinite"
              />
              <animate
                attributeName="strokeOpacity"
                values="0.3;0;0.3"
                dur="3s"
                repeatCount="indefinite"
              />
            </circle>
            <text
              x={centerX}
              y={centerY - 6}
              textAnchor="middle"
              fill="var(--foreground)"
              fontSize="9"
              fontWeight="bold"
            >
              NEXUS
            </text>
            <text
              x={centerX}
              y={centerY + 8}
              textAnchor="middle"
              fill="#34d399"
              fontSize="7"
            >
              Core
            </text>

            {/* Pillar nodes */}
            {nodePositions.map((node) => {
              const healthColor = node.health >= 95 ? '#34d399' : node.health >= 85 ? '#facc15' : '#f87171'
              return (
                <g
                  key={`node-${node.name}`}
                  onClick={() => handlePillarClick(node.name)}
                  style={{ cursor: onPillarClick ? 'pointer' : 'default' }}
                >
                  {/* Hover area (larger invisible circle) */}
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="28"
                    fill="transparent"
                  />
                  {/* Node circle */}
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="24"
                    fill="var(--card)"
                    stroke={node.color}
                    strokeWidth="1.5"
                    strokeOpacity="0.5"
                  />
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="24"
                    fill={node.color}
                    fillOpacity="0.06"
                  />
                  {/* Health indicator dot */}
                  <circle
                    cx={node.x + 18}
                    cy={node.y - 18}
                    r="4"
                    fill={healthColor}
                  />
                  <circle
                    cx={node.x + 18}
                    cy={node.y - 18}
                    r="4"
                    fill={healthColor}
                    opacity="0.4"
                  >
                    <animate
                      attributeName="r"
                      values="4;7;4"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                    <animate
                      attributeName="opacity"
                      values="0.4;0;0.4"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                  </circle>
                  {/* Node name */}
                  <text
                    x={node.x}
                    y={node.y + 34}
                    textAnchor="middle"
                    fill="var(--muted-foreground)"
                    fontSize="8"
                    fontWeight="500"
                  >
                    {node.name}
                  </text>
                  {/* Health percentage */}
                  <text
                    x={node.x}
                    y={node.y + 44}
                    textAnchor="middle"
                    fill={node.color}
                    fontSize="7"
                    fontWeight="bold"
                  >
                    {node.health}%
                  </text>
                </g>
              )
            })}
          </svg>

          {/* Legend with clickable pillars */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3 text-[10px]">
            {pillars.map((p) => (
              <button
                key={p.name}
                onClick={() => handlePillarClick(p.name)}
                className="flex items-center gap-1.5 hover:opacity-80 transition-opacity"
                title={p.desc}
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
                <span className="text-muted-foreground">{p.name}</span>
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
