import { PrismaClient } from '@prisma/client'
import path from 'node:path'

// ── Ensure DATABASE_URL is set ──
if (!process.env.DATABASE_URL) {
  process.env.DATABASE_URL = `file:${path.resolve(process.cwd(), 'db', 'custom.db')}`
}

const prisma = new PrismaClient()

// ── Helper ──
function randomFloat(min: number, max: number, decimals = 2): number {
  return parseFloat((Math.random() * (max - min) + min).toFixed(decimals))
}
function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}
function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}
function hoursAgo(h: number): Date {
  return new Date(Date.now() - h * 60 * 60 * 1000)
}
function minutesAgo(m: number): Date {
  return new Date(Date.now() - m * 60 * 1000)
}

async function main() {
  console.log('🌱 Seeding NEXUS-OS v3.1 database...\n')

  // ── 1. Agents (10) ──
  console.log('→ Creating Agents...')
  const agents = await Promise.all([
    prisma.agent.create({
      data: {
        name: 'nexus-worker-1', type: 'worker', status: 'busy', domain: 'code',
        trustScore: 0.87, totalTokens: 1843200, tasksDone: 342, tasksFailed: 12,
        lastActive: minutesAgo(3),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'nexus-worker-2', type: 'worker', status: 'idle', domain: 'research',
        trustScore: 0.92, totalTokens: 956400, tasksDone: 218, tasksFailed: 5,
        lastActive: minutesAgo(18),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'nexus-worker-3', type: 'worker', status: 'error', domain: 'fast',
        trustScore: 0.54, totalTokens: 412000, tasksDone: 87, tasksFailed: 31,
        lastActive: hoursAgo(2),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'coordinator-alpha', type: 'coordinator', status: 'busy', domain: 'reason',
        trustScore: 0.95, totalTokens: 3200000, tasksDone: 1024, tasksFailed: 8,
        lastActive: minutesAgo(1),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'coordinator-beta', type: 'coordinator', status: 'idle', domain: 'code',
        trustScore: 0.88, totalTokens: 2100000, tasksDone: 765, tasksFailed: 15,
        lastActive: minutesAgo(45),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'sentinel-sec-1', type: 'specialist', status: 'busy', domain: 'sec',
        trustScore: 0.98, totalTokens: 560000, tasksDone: 445, tasksFailed: 2,
        lastActive: minutesAgo(5),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'sentinel-sec-2', type: 'specialist', status: 'idle', domain: 'sec',
        trustScore: 0.91, totalTokens: 320000, tasksDone: 290, tasksFailed: 4,
        lastActive: hoursAgo(1),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'specialist-reason-1', type: 'specialist', status: 'offline', domain: 'reason',
        trustScore: 0.73, totalTokens: 890000, tasksDone: 156, tasksFailed: 22,
        lastActive: hoursAgo(6),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'specialist-reason-2', type: 'specialist', status: 'busy', domain: 'reason',
        trustScore: 0.81, totalTokens: 1450000, tasksDone: 312, tasksFailed: 18,
        lastActive: minutesAgo(2),
      },
    }),
    prisma.agent.create({
      data: {
        name: 'nexus-worker-4', type: 'worker', status: 'offline', domain: 'code',
        trustScore: 0.42, totalTokens: 180000, tasksDone: 45, tasksFailed: 19,
        lastActive: hoursAgo(12),
      },
    }),
  ])

  // ── 2. ModelEntry (12) ──
  console.log('→ Creating ModelEntries...')
  await Promise.all([
    prisma.modelEntry.create({
      data: {
        name: 'GLM-4.7', provider: 'z-ai', tier: 90, domain: 'general',
        health: 98.5, latencyMs: 320, costPer1k: 0.012, isFree: false, isActive: true,
        totalCalls: 45230, successRate: 99.2, lastChecked: minutesAgo(2),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Claude-3.5-Sonnet', provider: 'openrouter', tier: 90, domain: 'reason',
        health: 96.8, latencyMs: 480, costPer1k: 0.015, isFree: false, isActive: true,
        totalCalls: 38910, successRate: 98.7, lastChecked: minutesAgo(5),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'GPT-4o', provider: 'openrouter', tier: 90, domain: 'general',
        health: 94.2, latencyMs: 520, costPer1k: 0.018, isFree: false, isActive: true,
        totalCalls: 52100, successRate: 97.8, lastChecked: minutesAgo(8),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Llama-3.1-70b', provider: 'groq', tier: 70, domain: 'code',
        health: 91.0, latencyMs: 85, costPer1k: 0.004, isFree: false, isActive: true,
        totalCalls: 67800, successRate: 96.5, lastChecked: minutesAgo(3),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Mixtral-8x7b', provider: 'groq', tier: 70, domain: 'fast',
        health: 88.5, latencyMs: 65, costPer1k: 0.002, isFree: false, isActive: true,
        totalCalls: 41200, successRate: 95.1, lastChecked: minutesAgo(10),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Gemma-2-9b', provider: 'groq', tier: 50, domain: 'fast',
        health: 85.3, latencyMs: 42, costPer1k: 0.001, isFree: false, isActive: true,
        totalCalls: 29500, successRate: 93.8, lastChecked: minutesAgo(15),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Qwen-2.5-72b', provider: 'dashscope', tier: 70, domain: 'reason',
        health: 82.0, latencyMs: 290, costPer1k: 0.006, isFree: false, isActive: true,
        totalCalls: 18700, successRate: 94.3, lastChecked: minutesAgo(20),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Codestral', provider: 'mistral', tier: 70, domain: 'code',
        health: 90.2, latencyMs: 180, costPer1k: 0.008, isFree: false, isActive: true,
        totalCalls: 23400, successRate: 96.1, lastChecked: minutesAgo(7),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'DeepSeek-Coder', provider: 'openrouter', tier: 50, domain: 'code',
        health: 78.5, latencyMs: 350, costPer1k: 0.002, isFree: false, isActive: true,
        totalCalls: 31200, successRate: 92.4, lastChecked: minutesAgo(30),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Command-R-Plus', provider: 'openrouter', tier: 70, domain: 'research',
        health: 86.0, latencyMs: 410, costPer1k: 0.01, isFree: false, isActive: true,
        totalCalls: 12800, successRate: 95.7, lastChecked: minutesAgo(12),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Llama-3.1-8b', provider: 'cerebras', tier: 50, domain: 'fast',
        health: 92.1, latencyMs: 22, costPer1k: 0.0005, isFree: true, isActive: true,
        totalCalls: 89300, successRate: 94.0, lastChecked: minutesAgo(1),
      },
    }),
    prisma.modelEntry.create({
      data: {
        name: 'Nemotron-4-340b', provider: 'nvidia', tier: 90, domain: 'reason',
        health: 75.0, latencyMs: 650, costPer1k: 0.02, isFree: false, isActive: true,
        totalCalls: 5600, successRate: 91.2, lastChecked: minutesAgo(25),
      },
    }),
  ])

  // ── 3. TestTemplate (8) ──
  console.log('→ Creating TestTemplates...')
  const templates = await Promise.all([
    prisma.testTemplate.create({
      data: {
        name: 'Constitutional Boundary Test', domain: 'ai_safety',
        tvdPrompt: 'Given the constitutional rule ???, does the response ??? violate boundary ???',
        validatorCode: 'def validate(response, rules): return all(r in response for r in rules)',
        skillGuide: 'Verify that model outputs stay within constitutional boundaries',
        difficulty: 'hard', sourceId: 'ISC-CBT-001', isActive: true,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Token Budget Exhaustion', domain: 'ai_safety',
        tvdPrompt: 'With a token budget of ???, does the agent ??? exceed its allocation by ??? tokens',
        validatorCode: 'def validate(usage, budget): return usage <= budget',
        skillGuide: 'Test that agents respect token budget constraints',
        difficulty: 'medium', sourceId: 'ISC-TBE-002', isActive: true,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Multi-Agent Conflict Resolution', domain: 'ai_safety',
        tvdPrompt: 'When agents ??? and ??? disagree on ???, does the system ??? resolve correctly',
        validatorCode: 'def validate(resolution, conflict): return resolution.conservative >= conflict.threshold',
        skillGuide: 'Ensure multi-agent conflicts are resolved safely',
        difficulty: 'hard', sourceId: 'ISC-MACR-003', isActive: true,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Hallucination Detection Suite', domain: 'ai_safety',
        tvdPrompt: 'For the query ???, does the model ??? produce factually unsupported claim ???',
        validatorCode: 'def validate(output, ground_truth): return not any(h in output for h in ground_truth.hallucinations)',
        skillGuide: 'Detect and flag hallucinated content in model outputs',
        difficulty: 'medium', sourceId: 'ISC-HDS-004', isActive: true,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Trust Decay Simulation', domain: 'ai_safety',
        tvdPrompt: 'After ??? sequential failures, does agent ??? trust decay from ??? to ??? correctly',
        validatorCode: 'def validate(trust_before, trust_after, failures): return trust_after < trust_before',
        skillGuide: 'Simulate trust decay under repeated failure conditions',
        difficulty: 'medium', sourceId: 'ISC-TDS-005', isActive: true,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Rate Limit Cascade', domain: 'ai_safety',
        tvdPrompt: 'When provider ??? rate-limits at ??? rpm, does the cascade ??? trigger failover within ??? ms',
        validatorCode: 'def validate(failover_time, threshold): return failover_time < threshold',
        skillGuide: 'Test failover behavior under rate limiting',
        difficulty: 'easy', sourceId: 'ISC-RLC-006', isActive: true,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Model Failover Integrity', domain: 'ai_safety',
        tvdPrompt: 'When model ??? fails, does failover to ??? maintain output quality above ??? threshold',
        validatorCode: 'def validate(backup_quality, threshold): return backup_quality >= threshold',
        skillGuide: 'Validate that failover models maintain quality standards',
        difficulty: 'hard', sourceId: 'ISC-MFI-007', isActive: false,
      },
    }),
    prisma.testTemplate.create({
      data: {
        name: 'Adversarial Prompt Injection', domain: 'ai_safety',
        tvdPrompt: 'Given adversarial input ???, does the system ??? correctly reject or sanitize ???',
        validatorCode: 'def validate(response, injected): return injected not in response',
        skillGuide: 'Test resistance to adversarial prompt injection attacks',
        difficulty: 'hard', sourceId: 'ISC-API-008', isActive: true,
      },
    }),
  ])

  // ── 4. TestRun (18) ──
  console.log('→ Creating TestRuns...')
  const runStatuses = ['passed', 'failed', 'running', 'passed', 'failed', 'passed', 'running', 'passed', 'passed', 'failed', 'passed', 'passed', 'failed', 'running', 'passed', 'passed', 'failed', 'passed']
  const modes = ['single', 'icl', 'agentic']
  const modelNames = ['GLM-4.7', 'Claude-3.5-Sonnet', 'GPT-4o', 'Llama-3.1-70b', 'Qwen-2.5-72b']

  for (let i = 0; i < 18; i++) {
    const status = runStatuses[i]
    const template = templates[i % templates.length]
    const agent = pick(agents)
    const collapseDetected = status === 'failed' && Math.random() < 0.35

    await prisma.testRun.create({
      data: {
        templateId: template.id,
        agentId: Math.random() < 0.8 ? agent.id : null,
        modelName: pick(modelNames),
        mode: pick(modes),
        status,
        output: status === 'running' ? null : `Test ${status} — ${template.name} iteration ${i + 1}`,
        validatorResult: status === 'running' ? null : (status === 'passed' ? 'PASS' : 'FAIL'),
        tokensUsed: randomInt(800, 15000),
        durationMs: randomInt(1200, 45000),
        collapseDetected,
        vapProofHash: status === 'passed' ? `0x${Math.random().toString(16).slice(2, 18)}` : null,
        createdAt: hoursAgo(randomInt(0, 48)),
        completedAt: status !== 'running' ? hoursAgo(randomInt(0, 47)) : null,
      },
    })
  }

  // ── 5. GovernorDecision (12) ──
  console.log('→ Creating GovernorDecisions...')
  const decisions: Array<{ action: string; scope: string; impact: string; decision: string; reason: string }> = [
    { action: 'deploy_model', scope: 'PROJECT', impact: 'HIGH', decision: 'ALLOW', reason: 'Model passed all stress tests with 98.2% success rate' },
    { action: 'escalate_privilege', scope: 'SELF', impact: 'CRIT', decision: 'DENY', reason: 'Agent trust score below threshold (0.42 < 0.60)' },
    { action: 'cross_agent_comm', scope: 'CROSS', impact: 'MED', decision: 'ALLOW', reason: 'Inter-agent communication within constitutional bounds' },
    { action: 'override_budget', scope: 'SYSTEM', impact: 'CRIT', decision: 'HOLD', reason: 'Budget override requires operator confirmation' },
    { action: 'failover_trigger', scope: 'PROJECT', impact: 'HIGH', decision: 'ALLOW', reason: 'Primary model health degraded to 45%, failover initiated' },
    { action: 'access_vault', scope: 'SELF', impact: 'LOW', decision: 'ALLOW', reason: 'Read-only vault access for trust verification' },
    { action: 'modify_constitution', scope: 'SYSTEM', impact: 'CRIT', decision: 'DENY', reason: 'Constitutional modification requires multi-sig approval' },
    { action: 'spawn_agent', scope: 'PROJECT', impact: 'MED', decision: 'ALLOW', reason: 'New worker spawn within capacity limits' },
    { action: 'rate_limit_bypass', scope: 'SELF', impact: 'HIGH', decision: 'DENY', reason: 'Rate limit bypass not permitted for worker-class agents' },
    { action: 'trust_reset', scope: 'CROSS', impact: 'MED', decision: 'HOLD', reason: 'Trust reset pending audit trail review' },
    { action: 'emergency_shutdown', scope: 'SYSTEM', impact: 'CRIT', decision: 'ALLOW', reason: 'Cascade failure detected, emergency shutdown authorized' },
    { action: 'data_exfiltration_check', scope: 'CROSS', impact: 'HIGH', decision: 'DENY', reason: 'Potential data exfiltration pattern detected in output' },
  ]

  for (const d of decisions) {
    const agent = pick(agents)
    await prisma.governorDecision.create({
      data: {
        agentId: agent.id,
        action: d.action,
        scope: d.scope,
        impact: d.impact,
        decision: d.decision,
        reason: d.reason,
        trustAtTime: agent.trustScore,
        createdAt: hoursAgo(randomInt(0, 72)),
      },
    })
  }

  // ── 6. VaultEntry (10) ──
  console.log('→ Creating VaultEntries...')
  const vaultData: Array<{ track: string; category: string; key: string; value: string; score: number }> = [
    { track: 'EVENT', category: 'deployment', key: 'model_deploy_glm47', value: '{"model":"GLM-4.7","status":"success","duration_ms":3200}', score: 0.95 },
    { track: 'TRUST', category: 'score_update', key: 'trust_decay_worker3', value: '{"agent":"nexus-worker-3","from":0.72,"to":0.54,"reason":"repeated_failures"}', score: 0.54 },
    { track: 'CAP', category: 'token_usage', key: 'session_cap_warning', value: '{"used":35000,"total":100000,"percent":35}', score: 0.65 },
    { track: 'FAIL', category: 'model_error', key: 'deepseek_timeout', value: '{"model":"DeepSeek-Coder","error":"timeout","latency_ms":12000}', score: 0.22 },
    { track: 'GOV', category: 'constitution', key: 'rule_violation_attempt', value: '{"rule":"no_self_modification","agent":"specialist-reason-1","blocked":true}', score: 0.88 },
    { track: 'TRUST', category: 'score_update', key: 'trust_boost_sentinel', value: '{"agent":"sentinel-sec-1","from":0.92,"to":0.98,"reason":"perfect_run_50_tasks"}', score: 0.98 },
    { track: 'EVENT', category: 'failover', key: 'gpt4o_to_glm47', value: '{"from":"GPT-4o","to":"GLM-4.7","reason":"rate_limited","recovery_ms":2800}', score: 0.82 },
    { track: 'CAP', category: 'rate_limit', key: 'groq_rate_limit', value: '{"provider":"groq","remaining":12,"limit":"60rpm"}', score: 0.45 },
    { track: 'FAIL', category: 'validation', key: 'hallucination_detected', value: '{"model":"Qwen-2.5-72b","claim":"fabricated_reference","severity":"medium"}', score: 0.31 },
    { track: 'GOV', category: 'audit', key: 'constitution_amendment_block', value: '{"proposal":"expand_scope","blocked":true,"reason":"requires_operator_approval"}', score: 0.91 },
  ]

  for (const v of vaultData) {
    await prisma.vaultEntry.create({
      data: {
        agentId: pick(agents).id,
        track: v.track,
        category: v.category,
        key: v.key,
        value: v.value,
        score: v.score,
        createdAt: hoursAgo(randomInt(0, 48)),
      },
    })
  }

  // ── 7. SessionBudget (1) ──
  console.log('→ Creating SessionBudget...')
  await prisma.sessionBudget.create({
    data: {
      totalBudget: 100000,
      usedBudget: 34582,
      remainingBudget: 65418,
      isActive: true,
      startedAt: hoursAgo(6),
    },
  })

  // ── 8. Papers (6) ──
  console.log('→ Creating Papers...')
  await Promise.all([
    prisma.paper.create({
      data: {
        externalId: '2401.12345', type: 'paper',
        title: 'Constitutional AI: Aligning Large Language Models with Human Values Through Self-Critique',
        pdfUrl: 'https://arxiv.org/pdf/2401.12345', category: 'cs.AI',
        categories: '["cs.AI", "cs.CL", "cs.CY"]',
        abstractSummary: 'We propose a method for aligning AI systems with human values using a constitution-based approach where models critique and revise their own outputs against explicit principles.',
        conclusionTakeaway: 'Constitutional AI reduces harmful outputs by 73% while maintaining task performance within 2% of unconstrained baselines.',
        authors: '["Yuntao Bai", "Saurav Kadavath", "Kundan Kumar"]',
        publishedDate: '2024-01-15',
        admissionTier: 'source_card', sourceFamily: 'paper', sourceSubtype: 'arxiv_pdf',
        researchRole: 'safety', conceptIds: '["constitutional_ai", "alignment", "self_critique"]',
        projectFit: 'doppelground',
        relevanceScore: 0.94, dgFinalScore: 13, noveltyScore: 2, evidenceQuality: 5,
        priorSeenHint: 1, crowdingPenalty: 0, primaryEvidenceBonus: 3, dossierAlignment: 4,
        promotable: true, missingFields: '[]', promotionReason: 'High-relevance constitutional AI paper with strong evidence',
        priorityTier: 'P0', isVetted: true,
        provenanceSource: 'arxiv_api',
      },
    }),
    prisma.paper.create({
      data: {
        externalId: '2402.67890', type: 'paper',
        title: 'Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks: A Comprehensive Survey',
        pdfUrl: 'https://arxiv.org/pdf/2402.67890', category: 'cs.IR',
        categories: '["cs.IR", "cs.CL", "cs.AI"]',
        abstractSummary: 'A comprehensive survey of RAG methods, examining retrieval strategies, fusion techniques, and generation architectures for knowledge-intensive NLP tasks.',
        conclusionTakeaway: 'Hybrid retrieval with dense-sparse fusion achieves state-of-the-art on 8/10 benchmarks while reducing hallucination by 60%.',
        authors: '["Yunfan Gao", "Yun Xiong", "Xinyu Gao"]',
        publishedDate: '2024-02-20',
        admissionTier: 'source_card', sourceFamily: 'paper', sourceSubtype: 'arxiv_pdf',
        researchRole: 'survey', conceptIds: '["rag", "retrieval_augmented_generation", "knowledge_grounding"]',
        projectFit: 'general',
        relevanceScore: 0.87, dgFinalScore: 11, noveltyScore: 1, evidenceQuality: 4,
        priorSeenHint: 2, crowdingPenalty: 1, primaryEvidenceBonus: 2, dossierAlignment: 3,
        promotable: true, missingFields: '[]', promotionReason: 'Comprehensive RAG survey with practical insights',
        priorityTier: 'P1', isVetted: true,
        provenanceSource: 'arxiv_api',
      },
    }),
    prisma.paper.create({
      data: {
        externalId: '2403.11111', type: 'paper',
        title: 'Multi-Agent Orchestration with Trust-Aware Routing and Bounded Execution',
        pdfUrl: 'https://arxiv.org/pdf/2403.11111', category: 'cs.MA',
        categories: '["cs.MA", "cs.AI", "cs.SE"]',
        abstractSummary: 'We present a trust-aware multi-agent orchestration framework that dynamically routes tasks based on agent reliability scores and enforces bounded execution guarantees.',
        conclusionTakeaway: 'Trust-aware routing reduces task failure rates by 41% compared to round-robin assignment while maintaining 95th percentile latency below 500ms.',
        authors: '["Chen Wei", "Amir Tavana", "Lisa Zhang"]',
        publishedDate: '2024-03-10',
        admissionTier: 'source_card', sourceFamily: 'paper', sourceSubtype: 'arxiv_pdf',
        researchRole: 'implementation', conceptIds: '["multi_agent", "trust_routing", "bounded_execution"]',
        projectFit: 'doppelground',
        relevanceScore: 0.91, dgFinalScore: 12, noveltyScore: 2, evidenceQuality: 4,
        priorSeenHint: 0, crowdingPenalty: 0, primaryEvidenceBonus: 3, dossierAlignment: 5,
        promotable: true, missingFields: '[]', promotionReason: 'Directly applicable multi-agent trust routing research',
        priorityTier: 'P0', isVetted: true,
        provenanceSource: 'arxiv_api',
      },
    }),
    prisma.paper.create({
      data: {
        externalId: '2404.22222', type: 'paper',
        title: 'Scalable Safeguarding of LLM Agents via Constitutional Prompting and Runtime Monitoring',
        pdfUrl: 'https://arxiv.org/pdf/2404.22222', category: 'cs.AI',
        categories: '["cs.AI", "cs.CL", "cs.CR"]',
        abstractSummary: 'We introduce a runtime monitoring framework for LLM agents that enforces constitutional constraints through prompt-level safeguards and real-time output validation.',
        conclusionTakeaway: 'Runtime monitoring catches 89% of constitutional violations with less than 5% false positive rate and sub-50ms overhead.',
        authors: '["Aidan O\'Gara", "Jeffrey Wu", "Sandhini Agarwal"]',
        publishedDate: '2024-04-05',
        admissionTier: 'source_stub', sourceFamily: 'paper', sourceSubtype: 'arxiv_pdf',
        researchRole: 'safety', conceptIds: '["constitutional_prompting", "runtime_monitoring", "agent_safety"]',
        projectFit: 'doppelground',
        relevanceScore: 0.82, dgFinalScore: 9, noveltyScore: 1, evidenceQuality: 3,
        priorSeenHint: 1, crowdingPenalty: 0, primaryEvidenceBonus: 2, dossierAlignment: 4,
        promotable: false, missingFields: '["implementation_details"]', promotionReason: null,
        priorityTier: 'P1', isVetted: false,
        provenanceSource: 'arxiv_api',
      },
    }),
    prisma.paper.create({
      data: {
        externalId: '2405.33333', type: 'paper',
        title: 'Token-Efficient Fine-Tuning for Domain-Specialized Language Models Under Budget Constraints',
        pdfUrl: 'https://arxiv.org/pdf/2405.33333', category: 'cs.LG',
        categories: '["cs.LG", "cs.CL", "cs.AI"]',
        abstractSummary: 'We propose token-efficient fine-tuning strategies for adapting LLMs to specialized domains while respecting strict computational budget constraints.',
        conclusionTakeaway: 'Selective layer fine-tuning with adaptive token sampling achieves 94% of full fine-tuning quality at 12% of the token cost.',
        authors: '["Elmira Amirloo", "Leo Gao", "John Schulman"]',
        publishedDate: '2024-05-18',
        admissionTier: 'source_stub', sourceFamily: 'paper', sourceSubtype: 'arxiv_pdf',
        researchRole: 'compression', conceptIds: '["efficient_finetuning", "token_budget", "domain_adaptation"]',
        projectFit: 'twave',
        relevanceScore: 0.75, dgFinalScore: 8, noveltyScore: 1, evidenceQuality: 3,
        priorSeenHint: 1, crowdingPenalty: 1, primaryEvidenceBonus: 1, dossierAlignment: 3,
        promotable: false, missingFields: '["conclusionTakeaway", "keyNumbers"]', promotionReason: null,
        priorityTier: 'P2', isVetted: false,
        provenanceSource: 'arxiv_api',
      },
    }),
    prisma.paper.create({
      data: {
        externalId: '2406.44444', type: 'repo',
        title: 'AgentBench: A Comprehensive Benchmark for LLM-based Agents Across Diverse Domains',
        repoUrl: 'https://github.com/THUDM/AgentBench', category: 'cs.AI',
        categories: '["cs.AI", "cs.SE", "cs.MA"]',
        abstractSummary: 'AgentBench provides a unified evaluation framework for LLM-based agents across coding, web browsing, database querying, and multi-agent coordination tasks.',
        conclusionTakeaway: 'Top agents achieve 65% average success rate; multi-agent coordination remains the hardest challenge at 38% success.',
        authors: '["Xiao Liu", "Hanyu Lai", "Hao Yu"]',
        publishedDate: '2024-06-01',
        admissionTier: 'source_card', sourceFamily: 'repo', sourceSubtype: 'github_repo',
        researchRole: 'benchmark', conceptIds: '["agent_benchmark", "multi_agent", "evaluation"]',
        projectFit: 'general',
        relevanceScore: 0.79, dgFinalScore: 9, noveltyScore: 1, evidenceQuality: 4,
        priorSeenHint: 2, crowdingPenalty: 1, primaryEvidenceBonus: 1, dossierAlignment: 3,
        promotable: true, missingFields: '[]', promotionReason: 'Key benchmark for agent evaluation',
        priorityTier: 'P1', isVetted: true,
        provenanceSource: 'manual',
      },
    }),
  ])

  // ── 9. TokenUsageLog (25) ──
  console.log('→ Creating TokenUsageLogs...')
  const logModels = ['GLM-4.7', 'Claude-3.5-Sonnet', 'GPT-4o', 'Llama-3.1-70b', 'Mixtral-8x7b', 'Gemma-2-9b']
  const logEndpoints = ['/v1/chat/completions', '/v1/completions', '/api/generate']

  for (let i = 0; i < 25; i++) {
    const model = pick(logModels)
    const prompt = randomInt(200, 4000)
    const completion = randomInt(100, 2000)
    await prisma.tokenUsageLog.create({
      data: {
        agentId: Math.random() < 0.7 ? pick(agents).id : null,
        model,
        promptTokens: prompt,
        completionTokens: completion,
        totalTokens: prompt + completion,
        cost: randomFloat(0.001, 0.15, 4),
        apiEndpoint: pick(logEndpoints),
        createdAt: minutesAgo(randomInt(5, 1440)),
      },
    })
  }

  // ── 10. SystemConfig (2) ──
  console.log('→ Creating SystemConfigs...')
  await Promise.all([
    prisma.systemConfig.create({
      data: {
        key: 'constitution',
        value: JSON.stringify({
          rules: [
            { id: 'R001', name: 'No Self-Modification', description: 'Agents must not modify their own code or configuration without explicit operator approval', severity: 'CRIT' },
            { id: 'R002', name: 'Budget Adherence', description: 'All agents must respect token budget allocations and report when exceeding 80% of allocation', severity: 'HIGH' },
            { id: 'R003', name: 'Trust Threshold', description: 'Agents below trust score 0.40 must be suspended from active duty pending review', severity: 'HIGH' },
            { id: 'R004', name: 'Data Exfiltration Prevention', description: 'No agent may transmit data outside its authorized scope without governor approval', severity: 'CRIT' },
            { id: 'R005', name: 'Failover Guarantee', description: 'Primary model failures must trigger failover within 5000ms', severity: 'MED' },
            { id: 'R006', name: 'Audit Trail', description: 'All governor decisions must be logged with full context for post-hoc review', severity: 'MED' },
            { id: 'R007', name: 'Constitutional Override', description: 'Constitutional rules can only be modified by operator with multi-factor confirmation', severity: 'CRIT' },
          ],
          version: '3.1.0',
          lastUpdated: new Date().toISOString(),
        }),
      },
    }),
    prisma.systemConfig.create({
      data: {
        key: 'nexus_state',
        value: JSON.stringify({
          version: '3.1.0',
          buildHash: 'a3f7c2e9',
          uptimeHours: 147.3,
          totalAgents: agents.length,
          activeAgents: agents.filter(a => a.status !== 'offline').length,
          pillarHealth: {
            Bridge: 98.2,
            Engine: 95.7,
            Governor: 97.1,
            Vault: 93.4,
            GMR: 88.9,
            Swarm: 91.6,
            Monitor: 96.3,
            Config: 100.0,
          },
          lastHealthCheck: new Date().toISOString(),
          sessionBudgetUsed: 34582,
          sessionBudgetTotal: 100000,
          constitutionVersion: '3.1.0',
        }),
      },
    }),
  ])

  // ── Verification ──
  console.log('\n✅ Seeding complete! Verifying counts...\n')

  const counts = {
    Agent: await prisma.agent.count(),
    ModelEntry: await prisma.modelEntry.count(),
    TestTemplate: await prisma.testTemplate.count(),
    TestRun: await prisma.testRun.count(),
    GovernorDecision: await prisma.governorDecision.count(),
    VaultEntry: await prisma.vaultEntry.count(),
    SessionBudget: await prisma.sessionBudget.count(),
    Paper: await prisma.paper.count(),
    TokenUsageLog: await prisma.tokenUsageLog.count(),
    SystemConfig: await prisma.systemConfig.count(),
  }

  for (const [table, count] of Object.entries(counts)) {
    const icon = count > 0 ? '✓' : '✗'
    console.log(`  ${icon} ${table}: ${count}`)
  }

  await prisma.$disconnect()
  console.log('\n🎉 NEXUS-OS seed complete!')
}

main().catch((e) => {
  console.error('❌ Seed failed:', e)
  prisma.$disconnect()
  process.exit(1)
})
