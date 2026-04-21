'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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

const pillars = [
  { name: 'Bridge', icon: Zap, health: 100, color: '#34d399', angle: 0 },
  { name: 'Engine', icon: Router, health: 98, color: '#60a5fa', angle: 45 },
  { name: 'Governor', icon: Shield, health: 95, color: '#f87171', angle: 90 },
  { name: 'Vault', icon: Database, health: 100, color: '#a78bfa', angle: 135 },
  { name: 'GMR', icon: FlaskConical, health: 92, color: '#fb923c', angle: 180 },
  { name: 'Swarm', icon: Bug, health: 88, color: '#facc15', angle: 225 },
  { name: 'Monitor', icon: Activity, health: 96, color: '#f472b6', angle: 270 },
  { name: 'Config', icon: Settings, health: 100, color: '#34d399', angle: 315 },
]

export function SystemArchitecture() {
  // Calculate positions in a circle
  const centerX = 200
  const centerY = 200
  const radius = 140

  const nodePositions = pillars.map((p) => {
    const rad = ((p.angle - 90) * Math.PI) / 180
    return {
      ...p,
      x: centerX + radius * Math.cos(rad),
      y: centerY + radius * Math.sin(rad),
    }
  })

  return (
    <Card className="relative overflow-hidden border-emerald-600/20">
      <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
      <CardHeader className="relative pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Hexagon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> System Architecture
          </CardTitle>
          <Badge variant="outline" className="text-[9px]">8 Pillars</Badge>
        </div>
      </CardHeader>
      <CardContent className="relative p-4 pt-0">
        <div className="flex flex-col items-center">
          <svg
            viewBox="0 0 400 400"
            className="w-full max-w-[400px] h-auto"
            xmlns="http://www.w3.org/2000/svg"
          >
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
                  stroke="hsl(var(--border))"
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
              fill="hsl(var(--card))"
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
            <text
              x={centerX}
              y={centerY - 6}
              textAnchor="middle"
              fill="hsl(var(--foreground))"
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
              const Icon = node.icon
              return (
                <g key={`node-${node.name}`}>
                  {/* Node circle */}
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="24"
                    fill="hsl(var(--card))"
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
                    fill={node.health >= 95 ? '#34d399' : node.health >= 85 ? '#facc15' : '#f87171'}
                  />
                  <circle
                    cx={node.x + 18}
                    cy={node.y - 18}
                    r="4"
                    fill={node.health >= 95 ? '#34d399' : node.health >= 85 ? '#facc15' : '#f87171'}
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
                    fill="hsl(var(--muted-foreground))"
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

          {/* Legend */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3 text-[10px]">
            {pillars.map((p) => (
              <div key={p.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
                <span className="text-muted-foreground">{p.name}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
