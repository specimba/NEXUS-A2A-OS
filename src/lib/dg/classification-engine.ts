/**
 * DoppelGround Classification Engine v1.0
 *
 * Ported from DoppelGround_m0_freeze_current research_intake_project_fit.py
 * and RESEARCH_HARNESS_PROGRAM.md
 *
 * Provides:
 * - 7-tier admission class system (source_card, source_stub, web_reference, etc.)
 * - Research role taxonomy (evaluation, safety, memory, harness, etc.)
 * - Concept mapping (7 research concepts)
 * - Scoring formula (0-15 scale)
 * - Promotion tracking
 * - Priority bands (P0/P1/P2/HOLD)
 */

// ─── Type Definitions ────────────────────────────────────────────────

export type AdmissionTier =
  | 'top_attention'
  | 'source_card'
  | 'source_stub'
  | 'web_reference'
  | 'social_reference'
  | 'operator_fragment'
  | 'quarantine'

export type SourceFamily = 'paper' | 'repo' | 'dataset' | 'docs' | 'social' | 'unknown'

export type SourceSubtype =
  | 'arxiv_page'
  | 'arxiv_pdf'
  | 'github_repo'
  | 'hf_paper'
  | 'hf_dataset'
  | 'hf_collection'
  | 'openreview_paper'
  | 'direct_pdf'
  | 'github_pages_docs'
  | 'docs_site'
  | 'social_post'
  | 'unknown_link'

export type ResearchRole =
  | 'evaluation'
  | 'safety'
  | 'memory'
  | 'harness'
  | 'implementation'
  | 'compression'
  | 'benchmark'
  | 'survey'
  | 'infra'
  | 'context_only'

export type ProjectFit = 'doppelground' | 'twave' | 'sequence' | 'general'

export type PriorityBand = 'P0' | 'P1' | 'P2' | 'HOLD'

export type ConceptId =
  | 'agent_memory'
  | 'bounded_execution_harness'
  | 'research_automation'
  | 'evaluation_review'
  | 'compression_optimization'
  | 'safety_traps_manipulation'
  | 'local_deployment'

export interface ClassificationResult {
  admissionTier: AdmissionTier
  sourceFamily: SourceFamily
  sourceSubtype: SourceSubtype | null
  researchRole: ResearchRole
  conceptIds: ConceptId[]
  projectFit: ProjectFit
  priorityBand: PriorityBand
  dgFinalScore: number
  noveltyScore: number
  evidenceQuality: number
  priorSeenHint: number
  crowdingPenalty: number
  primaryEvidenceBonus: number
  dossierAlignment: number
  promotable: boolean
  missingFields: string[]
  promotionReason: string
}

export interface PaperInput {
  title: string
  summary?: string
  category?: string
  categories?: string[]
  pdfUrl?: string
  arxivId?: string
  sourceType?: SourceFamily
  sourceSubtype?: SourceSubtype
  existingPaperCount?: number // For crowding penalty
  seenTitles?: string[] // For prior_seen_hint
}

// ─── Constants ───────────────────────────────────────────────────────

// Base scores by source type (from DG)
const BASE_SCORES: Record<SourceFamily, number> = {
  paper: 4,
  repo: 4,
  docs: 3,
  dataset: 2,
  social: 1,
  unknown: 1,
}

// Role bonuses (from DG)
const ROLE_BONUSES: Record<ResearchRole, number> = {
  evaluation: 3,
  safety: 3,
  memory: 3,
  harness: 3,
  implementation: 2,
  infra: 2,
  benchmark: 2,
  survey: 1,
  compression: 1,
  context_only: -2,
}

// Concept definitions (from DG CONCEPT_RULES)
const CONCEPT_RULES: Record<ConceptId, {
  title: string
  keywords: string[]
  dossierLinks: ProjectFit[]
}> = {
  agent_memory: {
    title: 'Agent Memory',
    keywords: ['mem0', 'memory', 'hindsight', 'retrieval', 'rag', 'context window', 'long-term memory', 'episodic'],
    dossierLinks: ['doppelground', 'sequence'],
  },
  bounded_execution_harness: {
    title: 'Bounded Execution / Harness',
    keywords: ['harness', 'bounded', 'background-agents', 'beads', 'agent-lightning', 'sandbox', 'constrained', 'guardrail'],
    dossierLinks: ['doppelground', 'sequence'],
  },
  research_automation: {
    title: 'Research Automation',
    keywords: ['deer-flow', 'deepresearch', 'research', 'agentflow', 'deepagents', 'autorunner', 'paper discovery', 'literature review'],
    dossierLinks: ['doppelground', 'sequence'],
  },
  evaluation_review: {
    title: 'Evaluation / Review',
    keywords: ['llm-council', 'eval', 'benchmark', 'review', 'vibecosystem', 'risklab', 'leaderboard', 'scoring', 'metric'],
    dossierLinks: ['doppelground'],
  },
  compression_optimization: {
    title: 'Compression / Optimization',
    keywords: ['bitnet', 'bonsai', 'turbo', 'compression', 'ssd', 'attention', 'quantization', 'pruning', 'distillation'],
    dossierLinks: ['twave'],
  },
  safety_traps_manipulation: {
    title: 'Safety / Traps / Manipulation',
    keywords: ['trap', 'harmful', 'risklab', 'defense-in-depth', 'safety', 'manipulation', 'jailbreak', 'red-team', 'alignment'],
    dossierLinks: ['doppelground', 'twave'],
  },
  local_deployment: {
    title: 'Local Deployment',
    keywords: ['localai', 'anything-llm', 'openviking', 'local', 'on-device', 'edge', 'consumer', 'low-resource'],
    dossierLinks: ['sequence', 'doppelground'],
  },
}

// Dossier keyword rules (from DG DOSSIER_KEYWORDS, adapted for NEXUS)
const DOSSIER_KEYWORDS: Record<ProjectFit, { high: string[]; low: string[] }> = {
  doppelground: {
    high: ['memory', 'retrieval', 'mem0', 'hindsight', 'harness', 'bounded', 'review', 'eval', 'benchmark', 'safety', 'trap', 'manipulation', 'research', 'wiki', 'knowledge', 'governance', 'multi-agent', 'orchestration'],
    low: ['swarm', 'social', 'tweet', 'x.com'],
  },
  twave: {
    high: ['compression', 'bitnet', 'bonsai', 'ssd', 'turbo', 'attention', 'runtime', 'optimization', 'low-vram', 'quantization', 'pruning'],
    low: ['workflow', 'social', 'review-only'],
  },
  sequence: {
    high: ['workflow', 'operator', 'task', 'local', 'desktop', 'background', 'practical', 'mission', 'automation', 'tool use'],
    low: ['theory-only', 'social'],
  },
  general: {
    high: [],
    low: [],
  },
}

// Priority band thresholds (DG scale 0-15)
const PRIORITY_THRESHOLDS = {
  P0: 10,
  P1: 6,
  P2: 3,
  HOLD: 0,
}

// ─── Classification Functions ────────────────────────────────────────

/**
 * Determine source family from URL or metadata
 */
export function classifySourceFamily(input: PaperInput): SourceFamily {
  if (input.sourceType) return input.sourceType
  if (input.arxivId || input.category) return 'paper'
  if (input.pdfUrl) {
    if (input.pdfUrl.includes('github.com')) return 'repo'
    if (input.pdfUrl.includes('huggingface.co/datasets')) return 'dataset'
  }
  return 'unknown'
}

/**
 * Determine source subtype from URL patterns
 */
export function classifySourceSubtype(input: PaperInput): SourceSubtype | null {
  if (input.sourceSubtype) return input.sourceSubtype
  if (input.arxivId) return 'arxiv_pdf'
  if (input.pdfUrl) {
    if (input.pdfUrl.includes('arxiv.org/pdf')) return 'arxiv_pdf'
    if (input.pdfUrl.includes('arxiv.org/abs')) return 'arxiv_page'
    if (input.pdfUrl.includes('github.com')) return 'github_repo'
    if (input.pdfUrl.includes('openreview.net')) return 'openreview_paper'
    if (input.pdfUrl.includes('huggingface.co/papers')) return 'hf_paper'
    if (input.pdfUrl.endsWith('.pdf')) return 'direct_pdf'
  }
  return null
}

/**
 * Determine admission tier (7-tier source ontology)
 * Based on DG's admission_class() function
 */
export function classifyAdmissionTier(
  sourceFamily: SourceFamily,
  sourceSubtype: SourceSubtype | null,
  hasFullMetadata: boolean,
  relevanceScore: number
): AdmissionTier {
  // Repos always become source_cards
  if (sourceFamily === 'repo') return 'source_card'

  // Papers depend on metadata completeness and quality
  if (sourceFamily === 'paper') {
    if (hasFullMetadata && relevanceScore >= 0.7) return 'top_attention'
    if (hasFullMetadata) return 'source_card'
    return 'source_stub'
  }

  // Datasets become stubs
  if (sourceFamily === 'dataset') return 'source_stub'

  // Docs depend on source
  if (sourceFamily === 'docs') {
    if (sourceSubtype === 'hf_collection' || sourceSubtype === 'github_pages_docs') return 'web_reference'
    return 'source_stub'
  }

  // Social = reference only
  if (sourceFamily === 'social') return 'social_reference'

  // Unknown
  if (sourceSubtype === 'unknown_link') return 'web_reference'
  return 'quarantine'
}

/**
 * Determine research role from paper content
 * Based on DG's research_role() function
 */
export function classifyResearchRole(title: string, summary?: string, category?: string): ResearchRole {
  const text = `${title} ${summary || ''}`.toLowerCase()

  // Check roles in priority order (highest bonus first)
  if (matchesAny(text, ['eval', 'benchmark', 'review', 'llm-council', 'leaderboard', 'metric', 'scoring'])) return 'evaluation'
  if (matchesAny(text, ['risk', 'trap', 'harmful', 'defense', 'safety', 'manipulation', 'jailbreak', 'red-team', 'alignment', 'constitutional'])) return 'safety'
  if (matchesAny(text, ['memory', 'retrieval', 'mem0', 'hindsight', 'rag', 'context window', 'long-term', 'episodic'])) return 'memory'
  if (matchesAny(text, ['harness', 'bounded', 'background-agents', 'beads', 'sandbox', 'constrained', 'guardrail', 'governance'])) return 'harness'
  if (matchesAny(text, ['implementation', 'deer-flow', 'deepresearch', 'research', 'agentflow', 'tool use', 'agent'])) return 'implementation'
  if (matchesAny(text, ['compression', 'bitnet', 'bonsai', 'turbo', 'ssd', 'quantization', 'pruning', 'distillation'])) return 'compression'
  if (matchesAny(text, ['benchmark', 'leaderboard', 'scoring'])) return 'benchmark'
  if (matchesAny(text, ['survey', 'review', 'overview', 'systematic'])) return 'survey'
  if (matchesAny(text, ['api', 'proxy', 'connector', 'tooling', 'framework', 'infrastructure'])) return 'infra'

  return 'context_only'
}

/**
 * Map paper to research concepts
 * Based on DG's CONCEPT_RULES
 */
export function mapConcepts(title: string, summary?: string, category?: string): ConceptId[] {
  const text = `${title} ${summary || ''} ${category || ''}`.toLowerCase()
  const matched: ConceptId[] = []

  for (const [conceptId, rule] of Object.entries(CONCEPT_RULES)) {
    if (matchesAny(text, rule.keywords)) {
      matched.push(conceptId as ConceptId)
    }
  }

  return matched.length > 0 ? matched : ['research_automation'] // Default concept
}

/**
 * Determine project fit from content
 * Based on DG's project_fit() function
 */
export function classifyProjectFit(title: string, summary?: string): ProjectFit {
  const text = `${title} ${summary || ''}`.toLowerCase()

  let bestFit: ProjectFit = 'general'
  let bestScore = 0

  for (const [fit, keywords] of Object.entries(DOSSIER_KEYWORDS)) {
    if (fit === 'general') continue
    let score = 0
    for (const kw of keywords.high) {
      if (text.includes(kw)) score += 2
    }
    for (const kw of keywords.low) {
      if (text.includes(kw)) score -= 1
    }
    if (score > bestScore) {
      bestScore = score
      bestFit = fit as ProjectFit
    }
  }

  return bestFit
}

/**
 * Compute full DG scoring for a paper
 * Based on DG's final_project_fit_score() formula
 */
export function computeScore(input: PaperInput): {
  dgFinalScore: number
  noveltyScore: number
  evidenceQuality: number
  priorSeenHint: number
  crowdingPenalty: number
  primaryEvidenceBonus: number
  dossierAlignment: number
} {
  const sourceFamily = classifySourceFamily(input)
  const researchRole = classifyResearchRole(input.title, input.summary, input.category)
  const projectFit = classifyProjectFit(input.title, input.summary)
  const concepts = mapConcepts(input.title, input.summary, input.category)

  // Base score by source type
  const base = BASE_SCORES[sourceFamily] || 1

  // Role bonus
  const roleBonus = ROLE_BONUSES[researchRole] || 0

  // Project fit adjustment
  const projectFitAdj = projectFit === 'doppelground' ? 1 : projectFit === 'general' ? 0 : -1

  // Novelty: is this a unique topic?
  const noveltyScore = input.seenTitles?.some(t => t.toLowerCase() === input.title.toLowerCase()) ? 0 : 2

  // Evidence quality: papers with abstracts and categories are higher quality
  const evidenceQuality = Math.min(
    (input.summary ? 2 : 0) +
    (input.category ? 1 : 0) +
    (input.arxivId ? 1 : 0) +
    (input.pdfUrl ? 1 : 0),
    5
  )

  // Prior seen hint: have we seen similar titles?
  const priorSeenHint = input.seenTitles?.filter(t => {
    const tLower = t.toLowerCase()
    const words = input.title.toLowerCase().split(' ').filter(w => w.length > 4)
    return words.some(w => tLower.includes(w))
  }).length ? Math.min(input.seenTitles.filter(t => {
    const tLower = t.toLowerCase()
    const words = input.title.toLowerCase().split(' ').filter(w => w.length > 4)
    return words.some(w => tLower.includes(w))
  }).length, 3) : 0

  // Crowding penalty: too many papers in same category
  const crowdingPenalty = (input.existingPaperCount && input.existingPaperCount > 10) ? 3 :
                          (input.existingPaperCount && input.existingPaperCount > 5) ? 1 : 0

  // Primary evidence bonus: papers with direct evidence
  const primaryEvidenceBonus = (sourceFamily === 'paper' && input.summary && input.summary.length > 200) ? 3 :
                                (sourceFamily === 'paper' && input.summary) ? 2 :
                                (sourceFamily === 'repo') ? 3 : 0

  // Dossier alignment: concept match to active projects
  const dossierAlignment = Math.min(concepts.length * 2, 5)

  // Final score (clamped to 0-15)
  const rawScore = base + roleBonus + projectFitAdj + noveltyScore + evidenceQuality + priorSeenHint - crowdingPenalty + primaryEvidenceBonus + dossierAlignment
  const dgFinalScore = Math.max(0, Math.min(rawScore, 15))

  return {
    dgFinalScore,
    noveltyScore,
    evidenceQuality,
    priorSeenHint,
    crowdingPenalty,
    primaryEvidenceBonus,
    dossierAlignment,
  }
}

/**
 * Determine priority band from score
 */
export function classifyPriorityBand(dgFinalScore: number, relevanceScore: number): PriorityBand {
  // Use DG score as primary, relevance as secondary
  const combinedScore = dgFinalScore + (relevanceScore * 5)

  if (combinedScore >= PRIORITY_THRESHOLDS.P0 + 5) return 'P0'
  if (combinedScore >= PRIORITY_THRESHOLDS.P1 + 5) return 'P1'
  if (combinedScore >= PRIORITY_THRESHOLDS.P2 + 3) return 'P2'
  return 'HOLD'
}

/**
 * Check if a paper is promotable to source_card
 * Based on DG's promotion rules
 */
export function checkPromotability(input: PaperInput): {
  promotable: boolean
  missingFields: string[]
  promotionReason: string
} {
  const missing: string[] = []

  if (!input.title || input.title.length < 5) missing.push('stronger_title_or_topic')
  if (!input.summary || input.summary.length < 50) missing.push('paper_claim_or_method_summary')
  if (!input.category) missing.push('source_category')
  if (!input.arxivId && !input.pdfUrl) missing.push('access_url')
  if (classifyResearchRole(input.title, input.summary, input.category) === 'context_only') {
    missing.push('stronger_research_role_guess')
  }

  const promotable = missing.length === 0
  const promotionReason = promotable
    ? 'promoted_to_source_card: all required fields present'
    : `retained_as_stub: missing [${missing.join(', ')}]`

  return { promotable, missingFields: missing, promotionReason }
}

/**
 * Full classification pipeline — one call classifies everything
 */
export function classifyPaper(input: PaperInput, existingPapers?: { title: string; category?: string | null }[]): ClassificationResult {
  const sourceFamily = classifySourceFamily(input)
  const sourceSubtype = classifySourceSubtype(input)
  const researchRole = classifyResearchRole(input.title, input.summary, input.category)
  const conceptIds = mapConcepts(input.title, input.summary, input.category)
  const projectFit = classifyProjectFit(input.title, input.summary)
  const scoring = computeScore(input)
  const relevanceScore = scoring.dgFinalScore / 15 // Normalize to 0-1
  const hasFullMetadata = !!(input.title && input.summary && input.category && (input.arxivId || input.pdfUrl))
  const admissionTier = classifyAdmissionTier(sourceFamily, sourceSubtype, hasFullMetadata, relevanceScore)
  const priorityBand = classifyPriorityBand(scoring.dgFinalScore, relevanceScore)
  const promotion = checkPromotability(input)

  return {
    admissionTier,
    sourceFamily,
    sourceSubtype,
    researchRole,
    conceptIds,
    projectFit,
    priorityBand,
    relevanceScore,
    ...scoring,
    ...promotion,
  }
}

// ─── Helper ──────────────────────────────────────────────────────────

function matchesAny(text: string, keywords: string[]): boolean {
  return keywords.some(kw => text.includes(kw))
}

// ─── Export concept metadata for UI ──────────────────────────────────

export const CONCEPT_META: Record<ConceptId, { title: string; description: string; color: string; icon: string }> = {
  agent_memory: { title: 'Agent Memory', description: 'Memory, retrieval, RAG, episodic knowledge', color: 'blue', icon: '🧠' },
  bounded_execution_harness: { title: 'Bounded Execution', description: 'Harness, sandbox, guardrails, constrained execution', color: 'emerald', icon: '🛡️' },
  research_automation: { title: 'Research Automation', description: 'Paper discovery, literature review, research workflows', color: 'purple', icon: '🔬' },
  evaluation_review: { title: 'Evaluation / Review', description: 'Benchmarks, leaderboards, scoring, metrics', color: 'orange', icon: '📊' },
  compression_optimization: { title: 'Compression', description: 'Quantization, pruning, distillation, low-VRAM optimization', color: 'amber', icon: '🗜️' },
  safety_traps_manipulation: { title: 'Safety / Alignment', description: 'Jailbreak, red-team, alignment, safety evaluation', color: 'red', icon: '🚨' },
  local_deployment: { title: 'Local Deployment', description: 'On-device, edge, consumer-grade, low-resource', color: 'teal', icon: '💻' },
}

export const ROLE_META: Record<ResearchRole, { label: string; color: string; bonus: number }> = {
  evaluation: { label: 'Evaluation', color: 'orange', bonus: 3 },
  safety: { label: 'Safety', color: 'red', bonus: 3 },
  memory: { label: 'Memory', color: 'blue', bonus: 3 },
  harness: { label: 'Harness', color: 'emerald', bonus: 3 },
  implementation: { label: 'Implementation', color: 'purple', bonus: 2 },
  infra: { label: 'Infrastructure', color: 'teal', bonus: 2 },
  benchmark: { label: 'Benchmark', color: 'amber', bonus: 2 },
  survey: { label: 'Survey', color: 'cyan', bonus: 1 },
  compression: { label: 'Compression', color: 'yellow', bonus: 1 },
  context_only: { label: 'Context Only', color: 'gray', bonus: -2 },
}

export const TIER_META: Record<AdmissionTier, { label: string; color: string; priority: number }> = {
  top_attention: { label: 'Top Attention', color: 'emerald', priority: 6 },
  source_card: { label: 'Source Card', color: 'blue', priority: 5 },
  source_stub: { label: 'Source Stub', color: 'yellow', priority: 4 },
  web_reference: { label: 'Web Reference', color: 'gray', priority: 3 },
  social_reference: { label: 'Social Ref', color: 'purple', priority: 2 },
  operator_fragment: { label: 'Operator', color: 'muted', priority: 1 },
  quarantine: { label: 'Quarantine', color: 'red', priority: 0 },
}
