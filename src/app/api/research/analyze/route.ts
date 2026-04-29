import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import {
  classifyPaper,
  CONCEPT_META,
  ROLE_META,
  TIER_META,
} from '@/lib/dg/classification-engine'
import type { PaperInput, ResearchRole, ConceptId } from '@/lib/dg/classification-engine'

// ─── Research Role → Implementation Task Mapping ──────────────────────

const ROLE_TASK_MAP: Record<ResearchRole, string> = {
  evaluation: 'Integrate evaluation methodology into StressLab test framework',
  safety: 'Add safety constraints to Governor trust engine',
  memory: 'Implement memory retrieval patterns in Vault 5-track system',
  harness: 'Add bounded execution constraints to Swarm worker protocol',
  implementation: 'Build implementation adapter for research automation pipeline',
  compression: 'Optimize GMR model routing with compression techniques',
  benchmark: 'Add benchmark comparisons to StressLab arena',
  survey: 'Create knowledge synthesis entry for Vault research track',
  infra: 'Integrate infrastructure patterns into Bridge SDK',
  context_only: 'Archive as context reference in Vault EVENT track',
}

// ─── Research Role → Deliverable Path Mapping ────────────────────────

const ROLE_DELIVERABLE_MAP: Record<ResearchRole, string> = {
  evaluation: '/stresslab/eval-integration',
  safety: '/governor/safety-constraints',
  memory: '/vault/memory-retrieval',
  harness: '/swarm/bounded-execution',
  implementation: '/bridge/research-automation',
  compression: '/gmr/compression-optimization',
  benchmark: '/stresslab/benchmark-comparison',
  survey: '/vault/knowledge-synthesis',
  infra: '/bridge/infrastructure-patterns',
  context_only: '/vault/context-archive',
}

// ─── Pipeline Stage Classification ────────────────────────────────────
// A paper's stage is determined by its current state:
//   INTAKE    → paper exists in DB, but may be incomplete
//   VETTING   → paper needs DG classification (not yet classified or default values)
//   MANIFEST  → paper is classified but still has "Pending review" implementationTask
//   PRIORITY  → paper has a task but priority may need re-computation
//   DELIVERED → paper is vetted (isVetted = true) with a concrete implementationTask

type PipelineStage = 'intake' | 'vetting' | 'manifest' | 'priority' | 'delivered'

function classifyStage(paper: {
  isVetted: boolean
  implementationTask: string | null
  admissionTier: string
  researchRole: string
  dgFinalScore: number
}): PipelineStage {
  // Delivered: vetted papers with concrete tasks
  if (paper.isVetted && paper.implementationTask && paper.implementationTask !== 'Pending review') {
    return 'delivered'
  }

  // Priority: has DG classification and a non-pending task, but not yet vetted
  if (
    paper.researchRole !== 'context_only' &&
    paper.dgFinalScore > 0 &&
    paper.implementationTask &&
    paper.implementationTask !== 'Pending review' &&
    !paper.isVetted
  ) {
    return 'priority'
  }

  // Manifest: has been DG-classified but still has "Pending review" task
  if (
    paper.dgFinalScore > 0 &&
    paper.admissionTier !== 'source_stub' &&
    (!paper.implementationTask || paper.implementationTask === 'Pending review')
  ) {
    return 'manifest'
  }

  // Vetting: still has default/unset DG classification values
  if (
    paper.admissionTier === 'source_stub' ||
    paper.dgFinalScore === 0 ||
    paper.researchRole === 'context_only'
  ) {
    return 'vetting'
  }

  // Intake: base state — exists in DB
  return 'intake'
}

// ─── INTAKE: Validate data completeness ──────────────────────────────

function validateIntake(paper: {
  title: string
  abstractSummary: string | null
  category: string | null
  pdfUrl: string | null
  externalId: string | null
}): { complete: boolean; missing: string[] } {
  const missing: string[] = []
  if (!paper.title || paper.title.length < 5) missing.push('title')
  if (!paper.abstractSummary || paper.abstractSummary.length < 20) missing.push('abstractSummary')
  if (!paper.category) missing.push('category')
  if (!paper.pdfUrl && !paper.externalId) missing.push('accessUrl')
  return { complete: missing.length === 0, missing }
}

// ─── VETTING: Run DG classification on a paper ───────────────────────

async function runVetting(paperId: string, dryRun: boolean) {
  const paper = await db.paper.findUnique({ where: { id: paperId } })
  if (!paper) return null

  // Get existing papers for crowding/prior-seen calculation
  const existingPapers = await db.paper.findMany({
    select: { title: true, category: true },
    where: { id: { not: paperId } },
    take: 200,
    orderBy: { createdAt: 'desc' },
  })

  const input: PaperInput = {
    title: paper.title,
    summary: paper.abstractSummary || undefined,
    category: paper.category || undefined,
    categories: paper.categories ? JSON.parse(paper.categories) : undefined,
    pdfUrl: paper.pdfUrl || undefined,
    arxivId: paper.externalId?.replace('arxiv-', '') || undefined,
    sourceType: (paper.sourceFamily as PaperInput['sourceType']) || 'paper',
    sourceSubtype: (paper.sourceSubtype as PaperInput['sourceSubtype']) || undefined,
    existingPaperCount: existingPapers.length,
    seenTitles: existingPapers.map(p => p.title),
  }

  const classification = classifyPaper(input)

  // Compute relevance score (normalized from dgFinalScore)
  const relevanceScore = classification.dgFinalScore / 15

  if (dryRun) {
    return { paperId, classification, relevanceScore, updated: false }
  }

  const updated = await db.paper.update({
    where: { id: paperId },
    data: {
      admissionTier: classification.admissionTier,
      sourceFamily: classification.sourceFamily,
      sourceSubtype: classification.sourceSubtype,
      researchRole: classification.researchRole,
      conceptIds: JSON.stringify(classification.conceptIds),
      projectFit: classification.projectFit,
      relevanceScore,
      dgFinalScore: classification.dgFinalScore,
      noveltyScore: classification.noveltyScore,
      evidenceQuality: classification.evidenceQuality,
      priorSeenHint: classification.priorSeenHint,
      crowdingPenalty: classification.crowdingPenalty,
      primaryEvidenceBonus: classification.primaryEvidenceBonus,
      dossierAlignment: classification.dossierAlignment,
      promotable: classification.promotable,
      missingFields: JSON.stringify(classification.missingFields),
      promotionReason: classification.promotionReason,
      priorityTier: classification.priorityBand === 'HOLD' ? 'P2' : classification.priorityBand,
      nexusMapping: JSON.stringify(
        classification.conceptIds.map(id => CONCEPT_META[id]?.title || id)
      ),
      keyNumbers: JSON.stringify({
        dgScore: classification.dgFinalScore,
        researchRole: classification.researchRole,
        projectFit: classification.projectFit,
        admissionTier: classification.admissionTier,
        conceptCount: classification.conceptIds.length,
      }),
    },
  })

  return { paperId, classification, relevanceScore, updated: true, paper: updated }
}

// ─── MANIFEST: Generate implementation tasks and manifest data ────────

async function runManifest(paperId: string, dryRun: boolean) {
  const paper = await db.paper.findUnique({ where: { id: paperId } })
  if (!paper) return null

  const role = (paper.researchRole || 'context_only') as ResearchRole
  const conceptIds: ConceptId[] = paper.conceptIds
    ? JSON.parse(paper.conceptIds)
    : []

  // Generate implementation task based on research role
  const implementationTask = ROLE_TASK_MAP[role] || ROLE_TASK_MAP.context_only

  // Generate deliverable path based on research role
  const deliverable = ROLE_DELIVERABLE_MAP[role] || ROLE_DELIVERABLE_MAP.context_only

  // Map concepts to NEXUS modules
  const conceptMapping = conceptIds.map(id => ({
    id,
    title: CONCEPT_META[id]?.title || id,
    description: CONCEPT_META[id]?.description || '',
    color: CONCEPT_META[id]?.color || 'gray',
  }))

  // Extract key takeaways from abstract
  const takeaways = extractTakeaways(paper.abstractSummary || '')

  // Build manifest
  const manifest = {
    paperId: paper.id,
    title: paper.title,
    researchRole: role,
    roleMeta: ROLE_META[role],
    admissionTier: paper.admissionTier,
    tierMeta: TIER_META[paper.admissionTier as keyof typeof TIER_META] || null,
    conceptMapping,
    implementationTask,
    deliverable,
    takeaways,
    projectFit: paper.projectFit,
    dgScore: paper.dgFinalScore,
    relevanceScore: paper.relevanceScore,
  }

  if (dryRun) {
    return { paperId, manifest, updated: false }
  }

  const updated = await db.paper.update({
    where: { id: paperId },
    data: {
      implementationTask,
      deliverable,
    },
  })

  return { paperId, manifest, updated: true, paper: updated }
}

// ─── PRIORITY: Re-compute priority bands and assign tasks ────────────

async function runPriority(paperId: string, dryRun: boolean) {
  const paper = await db.paper.findUnique({ where: { id: paperId } })
  if (!paper) return null

  // Re-compute priority based on DG scores
  const combinedScore = paper.dgFinalScore + paper.relevanceScore * 5
  let priorityTier: string

  if (combinedScore >= 15) priorityTier = 'P0'
  else if (combinedScore >= 11) priorityTier = 'P1'
  else if (combinedScore >= 6) priorityTier = 'P2'
  else priorityTier = 'P2' // Never use HOLD in DB

  // For P0/P1 papers, refine the implementation task with more detail
  let implementationTask = paper.implementationTask
  const role = (paper.researchRole || 'context_only') as ResearchRole

  if ((priorityTier === 'P0' || priorityTier === 'P1') && implementationTask) {
    // Add priority-specific detail to the task
    const conceptIds: ConceptId[] = paper.conceptIds
      ? JSON.parse(paper.conceptIds)
      : []

    const conceptTitles = conceptIds
      .map(id => CONCEPT_META[id]?.title)
      .filter(Boolean)

    if (conceptTitles.length > 0) {
      implementationTask = `${implementationTask} [Concepts: ${conceptTitles.join(', ')}]`
    }

    if (priorityTier === 'P0') {
      implementationTask = `[URGENT] ${implementationTask}`
    }
  }

  // Assign deliverable path
  const deliverable = ROLE_DELIVERABLE_MAP[role] || ROLE_DELIVERABLE_MAP.context_only

  if (dryRun) {
    return {
      paperId,
      priorityTier,
      implementationTask,
      deliverable,
      updated: false,
    }
  }

  const updated = await db.paper.update({
    where: { id: paperId },
    data: {
      priorityTier,
      implementationTask,
      deliverable,
    },
  })

  return { paperId, priorityTier, implementationTask, deliverable, updated: true, paper: updated }
}

// ─── DELIVERED: Mark papers as vetted ────────────────────────────────

async function runDelivered(paperId: string, dryRun: boolean) {
  const paper = await db.paper.findUnique({ where: { id: paperId } })
  if (!paper) return null

  // Only deliver papers that have concrete implementation tasks
  if (!paper.implementationTask || paper.implementationTask === 'Pending review') {
    return { paperId, delivered: false, reason: 'No concrete implementation task assigned' }
  }

  // Only deliver papers with meaningful DG scores
  if (paper.dgFinalScore < 3) {
    return { paperId, delivered: false, reason: 'DG score too low for delivery' }
  }

  if (dryRun) {
    return { paperId, delivered: true, updated: false }
  }

  const updated = await db.paper.update({
    where: { id: paperId },
    data: {
      isVetted: true,
    },
  })

  return { paperId, delivered: true, updated: true, paper: updated }
}

// ─── Helper: Extract key takeaways from abstract ─────────────────────

function extractTakeaways(abstract: string): string[] {
  if (!abstract || abstract.length < 50) return ['No abstract available for takeaway extraction']

  const takeaways: string[] = []

  // Extract sentences with key indicator phrases
  const sentences = abstract
    .replace(/\n/g, ' ')
    .split(/(?<=[.!?])\s+/)
    .filter(s => s.trim().length > 15)

  // Look for results/contribution sentences
  const resultPatterns = [
    /we (?:propose|present|introduce|develop|demonstrate|show)/i,
    /our (?:approach|method|framework|system|model)/i,
    /results?(?:\s+show)?\s+(?:indicate|demonstrate|achieve|improve)/i,
    /achieves?\s+/i,
    /improves?\s+/i,
    /outperforms?\s+/i,
  ]

  for (const sentence of sentences) {
    if (resultPatterns.some(p => p.test(sentence))) {
      takeaways.push(sentence.trim())
    }
    if (takeaways.length >= 3) break
  }

  // If no result sentences found, take the first 2 meaningful sentences
  if (takeaways.length === 0) {
    const meaningful = sentences.filter(s => s.length > 30).slice(0, 2)
    takeaways.push(...meaningful)
  }

  return takeaways.length > 0 ? takeaways : ['Key takeaways could not be extracted automatically']
}

// ═══════════════════════════════════════════════════════════════════════
// GET /api/research/analyze — Pipeline Status
// ═══════════════════════════════════════════════════════════════════════

export async function GET() {
  try {
    const allPapers = await db.paper.findMany({
      select: {
        id: true,
        isVetted: true,
        implementationTask: true,
        admissionTier: true,
        researchRole: true,
        dgFinalScore: true,
        priorityTier: true,
        title: true,
        abstractSummary: true,
        category: true,
        pdfUrl: true,
        externalId: true,
        relevanceScore: true,
        projectFit: true,
        conceptIds: true,
        createdAt: true,
        updatedAt: true,
        provenanceSource: true,
      },
    })

    // Classify each paper into a pipeline stage
    const stageCounts: Record<PipelineStage, number> = {
      intake: 0,
      vetting: 0,
      manifest: 0,
      priority: 0,
      delivered: 0,
    }

    const stagePaperIds: Record<PipelineStage, string[]> = {
      intake: [],
      vetting: [],
      manifest: [],
      priority: [],
      delivered: [],
    }

    for (const paper of allPapers) {
      const stage = classifyStage(paper)
      stageCounts[stage]++
      stagePaperIds[stage].push(paper.id)
    }

    // Pipeline throughput metrics
    const totalPapers = allPapers.length
    const deliveredPapers = stageCounts.delivered
    const throughputRate = totalPapers > 0 ? deliveredPapers / totalPapers : 0

    // Average DG score across all papers
    const avgDgScore =
      totalPapers > 0
        ? allPapers.reduce((sum, p) => sum + p.dgFinalScore, 0) / totalPapers
        : 0

    // Average relevance score
    const avgRelevance =
      totalPapers > 0
        ? allPapers.reduce((sum, p) => sum + p.relevanceScore, 0) / totalPapers
        : 0

    // Priority tier distribution
    const priorityDistribution = {
      P0: allPapers.filter(p => p.priorityTier === 'P0').length,
      P1: allPapers.filter(p => p.priorityTier === 'P1').length,
      P2: allPapers.filter(p => p.priorityTier === 'P2').length,
    }

    // Research role distribution
    const roleDistribution: Record<string, number> = {}
    for (const paper of allPapers) {
      const role = paper.researchRole || 'context_only'
      roleDistribution[role] = (roleDistribution[role] || 0) + 1
    }

    // Admission tier distribution
    const tierDistribution: Record<string, number> = {}
    for (const paper of allPapers) {
      const tier = paper.admissionTier || 'source_stub'
      tierDistribution[tier] = (tierDistribution[tier] || 0) + 1
    }

    // Project fit distribution
    const fitDistribution: Record<string, number> = {}
    for (const paper of allPapers) {
      const fit = paper.projectFit || 'general'
      fitDistribution[fit] = (fitDistribution[fit] || 0) + 1
    }

    // Provenance source distribution
    const provenanceDistribution: Record<string, number> = {}
    for (const paper of allPapers) {
      const source = paper.provenanceSource || 'unknown'
      provenanceDistribution[source] = (provenanceDistribution[source] || 0) + 1
    }

    // Bottleneck analysis: identify the stage with the most papers stuck
    const bottleneckStages = (Object.entries(stageCounts) as [PipelineStage, number][])
      .filter(([stage]) => stage !== 'delivered')
      .sort((a, b) => b[1] - a[1])

    const bottleneck = bottleneckStages.length > 0 ? bottleneckStages[0] : null

    // Intake validation: how many papers are complete vs incomplete
    const intakeValidation = allPapers.map(p => ({
      id: p.id,
      title: p.title,
      ...validateIntake(p),
    }))
    const completeCount = intakeValidation.filter(v => v.complete).length
    const incompleteCount = intakeValidation.filter(v => !v.complete).length

    // Identify bottleneck details
    const bottleneckAnalysis = {
      stage: bottleneck ? bottleneck[0] : 'none',
      paperCount: bottleneck ? bottleneck[1] : 0,
      percentage: totalPapers > 0 && bottleneck ? Math.round((bottleneck[1] / totalPapers) * 100) : 0,
      recommendation: getBottleneckRecommendation(bottleneck ? bottleneck[0] : 'none'),
    }

    return NextResponse.json({
      pipeline: {
        stages: stageCounts,
        stagePaperIds,
        totalPapers,
        throughputRate: Math.round(throughputRate * 100) / 100,
      },
      metrics: {
        avgDgScore: Math.round(avgDgScore * 100) / 100,
        avgRelevance: Math.round(avgRelevance * 100) / 100,
        deliveredPapers,
        throughputPercent: Math.round(throughputRate * 100),
      },
      distributions: {
        priority: priorityDistribution,
        role: roleDistribution,
        tier: tierDistribution,
        projectFit: fitDistribution,
        provenance: provenanceDistribution,
      },
      intakeValidation: {
        complete: completeCount,
        incomplete: incompleteCount,
        details: intakeValidation.filter(v => !v.complete).slice(0, 20),
      },
      bottleneck: bottleneckAnalysis,
    })
  } catch (error) {
    console.error('Research analyze GET error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

// ─── Bottleneck recommendation helper ─────────────────────────────────

function getBottleneckRecommendation(stage: string): string {
  switch (stage) {
    case 'intake':
      return 'Papers exist but may have incomplete metadata. Run vetting to classify and enrich paper data.'
    case 'vetting':
      return 'Papers need DG classification. Run the VETTING stage to apply the DoppelGround classification engine.'
    case 'manifest':
      return 'Papers are classified but lack implementation tasks. Run the MANIFEST stage to generate tasks and deliverable paths.'
    case 'priority':
      return 'Papers have tasks but need priority verification. Run the PRIORITY stage to finalize priority bands.'
    case 'delivered':
      return 'No bottleneck — all papers are delivered. Pipeline is healthy.'
    default:
      return 'No bottleneck detected. Pipeline is functioning normally.'
  }
}

// ═══════════════════════════════════════════════════════════════════════
// POST /api/research/analyze — Run Analysis Pipeline
// ═══════════════════════════════════════════════════════════════════════

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { stage, paperIds, dryRun = false } = body as {
      stage?: string
      paperIds?: string[]
      dryRun?: boolean
    }

    // Determine which papers to process
    let targetPapers: Array<{
      id: string
      isVetted: boolean
      implementationTask: string | null
      admissionTier: string
      researchRole: string
      dgFinalScore: number
      priorityTier: string
      title: string
      abstractSummary: string | null
      category: string | null
      pdfUrl: string | null
      externalId: string | null
      relevanceScore: number
    }>

    if (paperIds && paperIds.length > 0) {
      targetPapers = await db.paper.findMany({
        where: { id: { in: paperIds } },
      })
    } else {
      targetPapers = await db.paper.findMany()
    }

    if (targetPapers.length === 0) {
      return NextResponse.json({
        message: 'No papers found to process',
        stages: {},
      })
    }

    // If a specific stage is requested, filter papers to those at that stage
    const stagesToRun: PipelineStage[] = stage
      ? [stage as PipelineStage]
      : ['intake', 'vetting', 'manifest', 'priority', 'delivered']

    const results: Record<string, {
      processed: number
      succeeded: number
      failed: number
      details: Array<Record<string, unknown>>
    }> = {}

    for (const currentStage of stagesToRun) {
      const stageResult = {
        processed: 0,
        succeeded: 0,
        failed: 0,
        details: [] as Array<Record<string, unknown>>,
      }

      // Filter papers that belong to this stage
      const papersInStage = targetPapers.filter(p => {
        if (stage) return true // If a specific stage was requested, process all papers through it
        return classifyStage(p) === currentStage
      })

      for (const paper of papersInStage) {
        try {
          stageResult.processed++
          let result: Record<string, unknown> | null = null

          switch (currentStage) {
            case 'intake': {
              // INTAKE: Validate data completeness
              const validation = validateIntake(paper)
              result = {
                paperId: paper.id,
                title: paper.title,
                complete: validation.complete,
                missing: validation.missing,
              }

              // If paper is incomplete, mark it with missing fields
              if (!validation.complete && !dryRun) {
                await db.paper.update({
                  where: { id: paper.id },
                  data: {
                    missingFields: JSON.stringify(validation.missing),
                  },
                })
              }
              break
            }

            case 'vetting': {
              result = await runVetting(paper.id, dryRun)
              break
            }

            case 'manifest': {
              result = await runManifest(paper.id, dryRun)
              break
            }

            case 'priority': {
              result = await runPriority(paper.id, dryRun)
              break
            }

            case 'delivered': {
              result = await runDelivered(paper.id, dryRun)
              break
            }
          }

          if (result) {
            stageResult.succeeded++
            stageResult.details.push(result)
          }
        } catch (err) {
          stageResult.failed++
          stageResult.details.push({
            paperId: paper.id,
            error: err instanceof Error ? err.message : String(err),
          })
        }
      }

      results[currentStage] = stageResult
    }

    // Build summary
    const summary = {
      totalPapers: targetPapers.length,
      dryRun,
      stagesRun: stagesToRun,
      results: Object.fromEntries(
        Object.entries(results).map(([stageName, r]) => [
          stageName,
          {
            processed: r.processed,
            succeeded: r.succeeded,
            failed: r.failed,
          },
        ])
      ),
    }

    return NextResponse.json({
      summary,
      stages: results,
    })
  } catch (error) {
    console.error('Research analyze POST error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

// ═══════════════════════════════════════════════════════════════════════
// PUT /api/research/analyze — Re-analyze a single paper
// ═══════════════════════════════════════════════════════════════════════

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json()
    const { paperId, force = false } = body as {
      paperId?: string
      force?: boolean
    }

    if (!paperId) {
      return NextResponse.json(
        { error: 'Missing required field: paperId' },
        { status: 400 }
      )
    }

    const paper = await db.paper.findUnique({ where: { id: paperId } })
    if (!paper) {
      return NextResponse.json(
        { error: 'Paper not found' },
        { status: 404 }
      )
    }

    // If paper is already vetted and force is not set, warn
    if (paper.isVetted && !force) {
      return NextResponse.json({
        paperId,
        message: 'Paper is already vetted. Set force=true to re-analyze.',
        currentStage: 'delivered',
        currentClassification: {
          admissionTier: paper.admissionTier,
          researchRole: paper.researchRole,
          dgFinalScore: paper.dgFinalScore,
          priorityTier: paper.priorityTier,
          implementationTask: paper.implementationTask,
        },
      })
    }

    // Reset vetting status if forcing re-analysis
    if (force && paper.isVetted) {
      await db.paper.update({
        where: { id: paperId },
        data: {
          isVetted: false,
          implementationTask: 'Pending review',
        },
      })
    }

    // Run full DG re-classification
    const existingPapers = await db.paper.findMany({
      select: { title: true, category: true },
      where: { id: { not: paperId } },
      take: 200,
      orderBy: { createdAt: 'desc' },
    })

    const input: PaperInput = {
      title: paper.title,
      summary: paper.abstractSummary || undefined,
      category: paper.category || undefined,
      categories: paper.categories ? JSON.parse(paper.categories) : undefined,
      pdfUrl: paper.pdfUrl || undefined,
      arxivId: paper.externalId?.replace('arxiv-', '') || undefined,
      sourceType: (paper.sourceFamily as PaperInput['sourceType']) || 'paper',
      sourceSubtype: (paper.sourceSubtype as PaperInput['sourceSubtype']) || undefined,
      existingPaperCount: existingPapers.length,
      seenTitles: existingPapers.map(p => p.title),
    }

    const classification = classifyPaper(input)

    // Compute relevance score (normalized from dgFinalScore)
    const relevanceScore = classification.dgFinalScore / 15

    // Generate implementation task based on new classification
    const role = classification.researchRole
    const implementationTask = ROLE_TASK_MAP[role] || ROLE_TASK_MAP.context_only
    const deliverable = ROLE_DELIVERABLE_MAP[role] || ROLE_DELIVERABLE_MAP.context_only

    // Compute priority tier
    const combinedScore = classification.dgFinalScore + relevanceScore * 5
    let priorityTier: string
    if (combinedScore >= 15) priorityTier = 'P0'
    else if (combinedScore >= 11) priorityTier = 'P1'
    else if (combinedScore >= 6) priorityTier = 'P2'
    else priorityTier = 'P2'

    // Add concept details for P0/P1
    let finalTask = implementationTask
    if (priorityTier === 'P0' || priorityTier === 'P1') {
      const conceptTitles = classification.conceptIds
        .map(id => CONCEPT_META[id]?.title)
        .filter(Boolean)
      if (conceptTitles.length > 0) {
        finalTask = `${implementationTask} [Concepts: ${conceptTitles.join(', ')}]`
      }
      if (priorityTier === 'P0') {
        finalTask = `[URGENT] ${finalTask}`
      }
    }

    // Update the paper with all new classification data
    const updated = await db.paper.update({
      where: { id: paperId },
      data: {
        // DG Classification
        admissionTier: classification.admissionTier,
        sourceFamily: classification.sourceFamily,
        sourceSubtype: classification.sourceSubtype,
        researchRole: classification.researchRole,
        conceptIds: JSON.stringify(classification.conceptIds),
        projectFit: classification.projectFit,
        // DG Scoring
        relevanceScore,
        dgFinalScore: classification.dgFinalScore,
        noveltyScore: classification.noveltyScore,
        evidenceQuality: classification.evidenceQuality,
        priorSeenHint: classification.priorSeenHint,
        crowdingPenalty: classification.crowdingPenalty,
        primaryEvidenceBonus: classification.primaryEvidenceBonus,
        dossierAlignment: classification.dossierAlignment,
        // Promotion
        promotable: classification.promotable,
        missingFields: JSON.stringify(classification.missingFields),
        promotionReason: classification.promotionReason,
        // Priority & Task
        priorityTier,
        implementationTask: finalTask,
        deliverable,
        // Reset vetting status (paper needs to go through pipeline again)
        isVetted: false,
        // Provenance
        nexusMapping: JSON.stringify(
          classification.conceptIds.map(id => CONCEPT_META[id]?.title || id)
        ),
        keyNumbers: JSON.stringify({
          dgScore: classification.dgFinalScore,
          researchRole: classification.researchRole,
          projectFit: classification.projectFit,
          admissionTier: classification.admissionTier,
          conceptCount: classification.conceptIds.length,
        }),
        traceRef: `reanalyze:${new Date().toISOString().replace(/[:.]/g, '')}:${paperId}`,
      },
    })

    return NextResponse.json({
      paperId,
      reAnalyzed: true,
      force,
      previousStage: paper.isVetted ? 'delivered' : classifyStage(paper),
      classification: {
        admissionTier: classification.admissionTier,
        researchRole: classification.researchRole,
        conceptIds: classification.conceptIds,
        projectFit: classification.projectFit,
        priorityBand: classification.priorityBand,
        relevanceScore,
        dgFinalScore: classification.dgFinalScore,
        noveltyScore: classification.noveltyScore,
        evidenceQuality: classification.evidenceQuality,
        priorSeenHint: classification.priorSeenHint,
        crowdingPenalty: classification.crowdingPenalty,
        primaryEvidenceBonus: classification.primaryEvidenceBonus,
        dossierAlignment: classification.dossierAlignment,
        promotable: classification.promotable,
      },
      task: {
        priorityTier,
        implementationTask: finalTask,
        deliverable,
      },
      paper: updated,
    })
  } catch (error) {
    console.error('Research analyze PUT error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
