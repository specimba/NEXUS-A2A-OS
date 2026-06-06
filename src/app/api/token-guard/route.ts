import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

// ─── TokenGuard API ───
// Token budget management and model pool allocation from
// hermes-agent/mimo25-nexus experimental lanes.
//
// Implements 3 pool tiers (ECO/FAST/PREMIUM) with realistic model lists,
// per-agent budget tracking, and trust-score-weighted token consumption.
//
// GET  → Token budget and model pool status
// POST → check_and_consume — Check token availability and consume if allowed

// ─── Model Pool Definitions ───

interface ModelPool {
  tier: 'ECO' | 'FAST' | 'PREMIUM'
  models: string[]
  totalBudget: number
  usedBudget: number
  available: boolean
  rateLimitRemaining: number
}

const MODEL_POOLS: Record<string, ModelPool> = {
  eco: {
    tier: 'ECO',
    models: ['twave-local', 'bonsai-1bit', 'ollama-tiny'],
    totalBudget: 500000,
    usedBudget: 125000,
    available: true,
    rateLimitRemaining: 950,
  },
  fast: {
    tier: 'FAST',
    models: ['groq-llama3', 'gemini-flash-lite'],
    totalBudget: 1000000,
    usedBudget: 450000,
    available: true,
    rateLimitRemaining: 780,
  },
  premium: {
    tier: 'PREMIUM',
    models: ['gemini-2.5-pro', 'claude-4.6'],
    totalBudget: 2000000,
    usedBudget: 890000,
    available: true,
    rateLimitRemaining: 420,
  },
}

// ─── Agent Budget Tracking (in-memory for mock, DB-backed for real agents) ───

interface AgentBudget {
  agentId: string
  tier: 'ECO' | 'FAST' | 'PREMIUM'
  totalBudget: number
  usedTokens: number
  remainingTokens: number
  usagePct: number
  resetsIn: string
}

const MOCK_AGENT_BUDGETS: AgentBudget[] = [
  { agentId: 'agent-001', tier: 'PREMIUM', totalBudget: 200000, usedTokens: 45000, remainingTokens: 155000, usagePct: 22.5, resetsIn: '0:34:12' },
  { agentId: 'agent-002', tier: 'ECO',     totalBudget: 10000,  usedTokens: 8200,  remainingTokens: 1800,   usagePct: 82.0, resetsIn: '0:12:45' },
  { agentId: 'agent-003', tier: 'ECO',     totalBudget: 10000,  usedTokens: 9500,  remainingTokens: 500,    usagePct: 95.0, resetsIn: '0:08:22' },
  { agentId: 'agent-004', tier: 'FAST',    totalBudget: 50000,  usedTokens: 28000, remainingTokens: 22000,  usagePct: 56.0, resetsIn: '0:28:05' },
  { agentId: 'agent-005', tier: 'FAST',    totalBudget: 50000,  usedTokens: 15000, remainingTokens: 35000,  usagePct: 30.0, resetsIn: '0:30:18' },
  { agentId: 'agent-006', tier: 'ECO',     totalBudget: 10000,  usedTokens: 7800,  remainingTokens: 2200,   usagePct: 78.0, resetsIn: '0:15:33' },
  { agentId: 'agent-007', tier: 'PREMIUM', totalBudget: 200000, usedTokens: 67000, remainingTokens: 133000, usagePct: 33.5, resetsIn: '0:32:47' },
]

// ─── Trust score to tier mapping ───

function trustScoreToTier(trustScore: number): 'ECO' | 'FAST' | 'PREMIUM' {
  if (trustScore >= 0.80) return 'PREMIUM'
  if (trustScore >= 0.55) return 'FAST'
  return 'ECO'
}

// ─── Budget allocation per tier ───

function tierToBudget(tier: 'ECO' | 'FAST' | 'PREMIUM'): number {
  switch (tier) {
    case 'PREMIUM': return 200000
    case 'FAST': return 50000
    case 'ECO': return 10000
  }
}

// ─── Format remaining time ───

function formatResetsIn(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = Math.floor(minutes % 60)
  const s = Math.floor((minutes * 60) % 60)
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// ─── In-memory budget state for mock agents ───
// (Allows POST /check_and_consume to actually modify state within a session)

const budgetState = new Map<string, { usedTokens: number; lastUpdated: number }>()

function getOrCreateBudgetState(agentId: string, initialUsed: number): { usedTokens: number; lastUpdated: number } {
  if (!budgetState.has(agentId)) {
    budgetState.set(agentId, { usedTokens: initialUsed, lastUpdated: Date.now() })
  }
  return budgetState.get(agentId)!
}

// ─── GET: Token Budget & Model Pool Status ───

export async function GET() {
  try {
    // Try to build agent budgets from DB agents
    const dbAgents = await db.agent.findMany({
      select: { id: true, name: true, trustScore: true, totalTokens: true },
    })

    let agentBudgets: AgentBudget[]

    if (dbAgents.length > 0) {
      // Build budgets from real DB data
      agentBudgets = dbAgents.map((agent) => {
        const tier = trustScoreToTier(agent.trustScore)
        const totalBudget = tierToBudget(tier)
        const state = getOrCreateBudgetState(agent.id, agent.totalTokens)
        const usedTokens = state.usedTokens
        const remainingTokens = Math.max(0, totalBudget - usedTokens)
        const usagePct = totalBudget > 0 ? Math.round((usedTokens / totalBudget) * 1000) / 10 : 0
        const minutesUntilReset = Math.max(1, Math.floor((3600000 - (Date.now() - state.lastUpdated)) / 60000))

        return {
          agentId: agent.name ?? agent.id,
          tier,
          totalBudget,
          usedTokens,
          remainingTokens,
          usagePct,
          resetsIn: formatResetsIn(minutesUntilReset),
        }
      })
    } else {
      // Use mock data
      agentBudgets = MOCK_AGENT_BUDGETS.map((b) => {
        const state = getOrCreateBudgetState(b.agentId, b.usedTokens)
        return {
          ...b,
          usedTokens: state.usedTokens,
          remainingTokens: Math.max(0, b.totalBudget - state.usedTokens),
          usagePct: b.totalBudget > 0 ? Math.round((state.usedTokens / b.totalBudget) * 1000) / 10 : 0,
        }
      })
    }

    // Aggregate token stats
    const totalTokensConsumed = agentBudgets.reduce((s, b) => s + b.usedTokens, 0)
    const totalTokensRemaining = agentBudgets.reduce((s, b) => s + b.remainingTokens, 0)

    // Update pool usage from session budget if available
    let pools = { ...MODEL_POOLS }
    try {
      const activeBudget = await db.sessionBudget.findFirst({ where: { isActive: true } })
      if (activeBudget) {
        pools = {
          eco: { ...MODEL_POOLS.eco, usedBudget: Math.floor(activeBudget.usedBudget * 0.15) },
          fast: { ...MODEL_POOLS.fast, usedBudget: Math.floor(activeBudget.usedBudget * 0.35) },
          premium: { ...MODEL_POOLS.premium, usedBudget: Math.floor(activeBudget.usedBudget * 0.50) },
        }
      }
    } catch {
      // Keep default pool data
    }

    return NextResponse.json({
      agentBudgets,
      modelPools: pools,
      totalTokensConsumed,
      totalTokensRemaining,
    })
  } catch (error) {
    // Fallback to mock data if DB fails
    const agentBudgets = MOCK_AGENT_BUDGETS.map((b) => {
      const state = getOrCreateBudgetState(b.agentId, b.usedTokens)
      return {
        ...b,
        usedTokens: state.usedTokens,
        remainingTokens: Math.max(0, b.totalBudget - state.usedTokens),
        usagePct: b.totalBudget > 0 ? Math.round((state.usedTokens / b.totalBudget) * 1000) / 10 : 0,
      }
    })

    return NextResponse.json({
      agentBudgets,
      modelPools: MODEL_POOLS,
      totalTokensConsumed: agentBudgets.reduce((s, b) => s + b.usedTokens, 0),
      totalTokensRemaining: agentBudgets.reduce((s, b) => s + b.remainingTokens, 0),
      _fallback: true,
      _error: String(error),
    })
  }
}

// ─── POST: Check and Consume Tokens ───

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action === 'check_and_consume') {
      const { agentId, tokens, trustScore } = body

      if (!agentId || !tokens || typeof tokens !== 'number') {
        return NextResponse.json(
          { error: 'Missing required fields: agentId, tokens (number)' },
          { status: 400 }
        )
      }

      if (tokens <= 0) {
        return NextResponse.json(
          { error: 'Token amount must be positive' },
          { status: 400 }
        )
      }

      // Determine tier from trust score (provided or looked up)
      const effectiveTrustScore = typeof trustScore === 'number' ? trustScore : 0.5
      const tier = trustScoreToTier(effectiveTrustScore)
      const totalBudget = tierToBudget(tier)
      const pool = MODEL_POOLS[tier.toLowerCase()]

      // Check agent budget
      const state = getOrCreateBudgetState(agentId, 0)
      const currentUsed = state.usedTokens
      const remainingBudget = Math.max(0, totalBudget - currentUsed)
      const hasBudget = tokens <= remainingBudget

      // Check pool availability
      const poolRemaining = pool.totalBudget - pool.usedBudget
      const poolAvailable = pool.available && tokens <= poolRemaining && pool.rateLimitRemaining > 0

      // Trust-score weighted token cost (higher trust = more efficient usage)
      const trustMultiplier = 1 - (effectiveTrustScore * 0.3) // Premium agents use 30% fewer tokens
      const effectiveTokens = Math.ceil(tokens * trustMultiplier)

      const approved = hasBudget && poolAvailable && effectiveTrustScore >= (tier === 'PREMIUM' ? 0.80 : tier === 'FAST' ? 0.55 : 0.0)

      if (approved) {
        // Consume tokens
        state.usedTokens = currentUsed + effectiveTokens
        state.lastUpdated = Date.now()

        // Update pool usage
        pool.usedBudget += effectiveTokens
        pool.rateLimitRemaining = Math.max(0, pool.rateLimitRemaining - 1)
      }

      // Log token usage to DB (best-effort)
      if (approved) {
        try {
          await db.tokenUsageLog.create({
            data: {
              agentId: null, // Mock agent IDs don't map to DB
              model: pool.models[0] ?? 'unknown',
              promptTokens: Math.floor(effectiveTokens * 0.6),
              completionTokens: Math.floor(effectiveTokens * 0.4),
              totalTokens: effectiveTokens,
              cost: (effectiveTokens / 1000) * (tier === 'PREMIUM' ? 0.03 : tier === 'FAST' ? 0.01 : 0.001),
              apiEndpoint: `/api/token-guard`,
            },
          })
        } catch {
          // DB log is best-effort
        }
      }

      return NextResponse.json({
        agentId,
        requestedTokens: tokens,
        effectiveTokens,
        trustMultiplier: Math.round(trustMultiplier * 1000) / 1000,
        tier,
        budgetBefore: { used: currentUsed, remaining: remainingBudget, total: totalBudget },
        budgetAfter: approved
          ? { used: state.usedTokens, remaining: Math.max(0, totalBudget - state.usedTokens), total: totalBudget }
          : { used: currentUsed, remaining: remainingBudget, total: totalBudget },
        poolStatus: {
          tier: pool.tier,
          available: poolAvailable,
          remaining: poolRemaining,
          rateLimitRemaining: pool.rateLimitRemaining,
        },
        approved,
        reason: approved
          ? `Token consumption approved: ${effectiveTokens} tokens (${trustMultiplier.toFixed(2)}x trust multiplier)`
          : !hasBudget
            ? `Insufficient budget: requested ${tokens}, remaining ${remainingBudget}`
            : !poolAvailable
              ? `Pool ${tier} unavailable or insufficient: pool remaining ${poolRemaining}, rate limit ${pool.rateLimitRemaining}`
              : `Trust score ${effectiveTrustScore} below threshold for ${tier} tier`,
      }, { status: approved ? 200 : 403 })
    }

    return NextResponse.json(
      { error: `Unknown action: ${action}. Valid action: check_and_consume` },
      { status: 400 }
    )
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
