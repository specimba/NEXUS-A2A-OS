import { NextResponse } from 'next/server'

const PROVIDERS = [
  { id: 'z-ai', name: 'z-ai SDK', status: 'healthy', tier: 'free', models: 1, latencyMs: 12, successRate: 99.8, quotaUsed: 34, quotaLimit: 40, authType: 'bearer' },
  { id: 'openrouter', name: 'OpenRouter Free', status: 'healthy', tier: 'free', models: 6, latencyMs: 180, successRate: 97.2, quotaUsed: 62, quotaLimit: 100, authType: 'bearer' },
  { id: 'cerebras', name: 'Cerebras Free', status: 'healthy', tier: 'free', models: 2, latencyMs: 45, successRate: 98.5, quotaUsed: 28, quotaLimit: 30, authType: 'bearer' },
  { id: 'groq', name: 'Groq Free (LPU)', status: 'healthy', tier: 'free', models: 3, latencyMs: 38, successRate: 96.1, quotaUsed: 55, quotaLimit: 30, authType: 'bearer' },
  { id: 'mistral', name: 'Mistral AI', status: 'degraded', tier: 'freemium', models: 2, latencyMs: 320, successRate: 89.3, quotaUsed: 45, quotaLimit: 50, authType: 'bearer' },
  { id: 'codestral', name: 'Codestral', status: 'unknown', tier: 'free', models: 1, latencyMs: 0, successRate: 0, quotaUsed: 0, quotaLimit: 30, authType: 'bearer' },
  { id: 'fireworks', name: 'Fireworks AI', status: 'healthy', tier: 'freemium', models: 2, latencyMs: 95, successRate: 95.4, quotaUsed: 20, quotaLimit: 10, authType: 'bearer' },
  { id: 'scaleway', name: 'Scaleway AI', status: 'unknown', tier: 'free', models: 1, latencyMs: 0, successRate: 0, quotaUsed: 0, quotaLimit: 10, authType: 'bearer' },
  { id: 'dashscope', name: 'Alibaba Cloud Free', status: 'unknown', tier: 'free', models: 8, latencyMs: 0, successRate: 0, quotaUsed: 0, quotaLimit: 10, authType: 'bearer' },
  { id: 'bitdeer', name: 'BitDeer AI', status: 'degraded', tier: 'freemium', models: 1, latencyMs: 410, successRate: 87.6, quotaUsed: 12, quotaLimit: 8, authType: 'bearer' },
  { id: 'nvidia', name: 'NVIDIA NIM Free', status: 'unknown', tier: 'free', models: 1, latencyMs: 0, successRate: 0, quotaUsed: 0, quotaLimit: 10, authType: 'bearer' },
  { id: 'sambanova', name: 'SambaNova Free', status: 'unknown', tier: 'free', models: 1, latencyMs: 0, successRate: 0, quotaUsed: 0, quotaLimit: 10, authType: 'bearer' },
  { id: 'siliconflow', name: 'SiliconFlow Free', status: 'degraded', tier: 'free', models: 1, latencyMs: 0, successRate: 72.1, quotaUsed: 5, quotaLimit: 10, authType: 'bearer' },
  { id: 'opencode', name: 'OpenCode', status: 'unknown', tier: 'free', models: 1, latencyMs: 0, successRate: 0, quotaUsed: 0, quotaLimit: 10, authType: 'bearer' },
]

export async function GET() {
  return NextResponse.json({
    providers: PROVIDERS,
    status: {
      total: PROVIDERS.length,
      healthy: PROVIDERS.filter(p => p.status === 'healthy').length,
      degraded: PROVIDERS.filter(p => p.status === 'degraded').length,
      unknown: PROVIDERS.filter(p => p.status === 'unknown').length,
      totalModels: PROVIDERS.reduce((sum, p) => sum + p.models, 0),
    },
  })
}
