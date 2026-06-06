import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'
import { classifyPaper } from '@/lib/dg/classification-engine'
import type { PaperInput } from '@/lib/dg/classification-engine'

/**
 * Research Pipeline API
 *
 * POST /api/research/pipeline
 *   Body: { action: 'rescore' | 'status' | 'advance' }
 *
 * Actions:
 *   - rescore: Re-classify all papers with fixed DG engine (fixes inflated scores)
 *   - status: Get pipeline status (counts per stage)
 *   - advance: Auto-advance papers that meet criteria to next stage
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body as { action: string }

    if (action === 'rescore') {
      return await rescorePapers()
    }

    if (action === 'status') {
      return await getPipelineStatus()
    }

    if (action === 'advance') {
      return await advancePapers()
    }

    return NextResponse.json({ error: 'Unknown action. Use: rescore, status, advance' }, { status: 400 })
  } catch (error) {
    console.error('Pipeline error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

async function rescorePapers() {
  const papers = await db.paper.findMany({
    select: {
      id: true,
      title: true,
      abstractSummary: true,
      category: true,
      categories: true,
      pdfUrl: true,
      externalId: true,
      sourceFamily: true,
      sourceSubtype: true,
    },
  })

  // Get all titles for seen-titles calculation
  const allTitles = papers.map(p => p.title)

  let rescored = 0
  let p0Count = 0
  let p1Count = 0
  let p2Count = 0
  let holdCount = 0

  // Classify all papers first (pure computation, no DB calls)
  const updates: { id: string; data: Record<string, unknown> }[] = []

  for (const paper of papers) {
    try {
      let parsedCategories: string[] | undefined
      try {
        parsedCategories = paper.categories ? JSON.parse(paper.categories) : undefined
      } catch {
        parsedCategories = undefined
      }

      const input: PaperInput = {
        title: paper.title,
        summary: paper.abstractSummary || undefined,
        category: paper.category || undefined,
        categories: parsedCategories,
        pdfUrl: paper.pdfUrl || undefined,
        arxivId: paper.externalId?.replace('arxiv-', '') || undefined,
        sourceType: (paper.sourceFamily as PaperInput['sourceType']) || undefined,
        sourceSubtype: (paper.sourceSubtype as PaperInput['sourceSubtype']) || undefined,
        existingPaperCount: papers.length,
        seenTitles: allTitles,
      }

      const classification = classifyPaper(input)
      const priorityTier = classification.priorityBand === 'HOLD' ? 'P2' : classification.priorityBand

      // Determine pipeline stage based on new score
      let pipelineStage = 'intake'
      if (classification.dgFinalScore >= 10 && classification.relevanceScore >= 0.7) {
        pipelineStage = 'priority'
      } else if (classification.dgFinalScore >= 6) {
        pipelineStage = 'manifest'
      } else if (classification.dgFinalScore >= 3) {
        pipelineStage = 'vetting'
      }

      updates.push({
        id: paper.id,
        data: {
          admissionTier: classification.admissionTier,
          sourceFamily: classification.sourceFamily,
          sourceSubtype: classification.sourceSubtype,
          researchRole: classification.researchRole,
          conceptIds: JSON.stringify(classification.conceptIds),
          projectFit: classification.projectFit,
          relevanceScore: classification.relevanceScore,
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
          priorityTier,
          pipelineStage,
        },
      })

      if (priorityTier === 'P0') p0Count++
      else if (priorityTier === 'P1') p1Count++
      else if (priorityTier === 'P2') p2Count++
      else holdCount++
    } catch (err) {
      console.error(`Failed to classify paper ${paper.id}:`, err)
    }
  }

  // Batch update in chunks of 20 to avoid timeout
  const CHUNK_SIZE = 20
  for (let i = 0; i < updates.length; i += CHUNK_SIZE) {
    const chunk = updates.slice(i, i + CHUNK_SIZE)
    try {
      await db.$transaction(
        chunk.map(u => db.paper.update({ where: { id: u.id }, data: u.data }))
      )
      rescored += chunk.length
    } catch (err) {
      console.error(`Failed to update chunk starting at ${i}:`, err)
      // Fall back to individual updates for this chunk
      for (const u of chunk) {
        try {
          await db.paper.update({ where: { id: u.id }, data: u.data })
          rescored++
        } catch {
          // Skip failed individual updates
        }
      }
    }
  }

  return NextResponse.json({
    success: true,
    action: 'rescore',
    total: papers.length,
    rescored,
    distribution: { P0: p0Count, P1: p1Count, P2: p2Count, HOLD: holdCount },
    message: `Re-scored ${rescored}/${papers.length} papers with fixed DG engine. Distribution: P0=${p0Count}, P1=${p1Count}, P2=${p2Count}, HOLD=${holdCount}`,
  })
}

async function getPipelineStatus() {
  const papers = await db.paper.findMany({
    select: {
      id: true,
      pipelineStage: true,
      priorityTier: true,
      isVetted: true,
      analyzedAt: true,
      llmAnalysis: true,
    },
  })

  const stageCounts = {
    intake: 0,
    vetting: 0,
    manifest: 0,
    priority: 0,
    delivered: 0,
  }

  const tierCounts = { P0: 0, P1: 0, P2: 0 }
  let vettedCount = 0
  let analyzedCount = 0

  for (const paper of papers) {
    const stage = paper.pipelineStage || 'intake'
    if (stage in stageCounts) {
      stageCounts[stage as keyof typeof stageCounts]++
    } else {
      stageCounts.intake++
    }

    if (paper.priorityTier in tierCounts) {
      tierCounts[paper.priorityTier as keyof typeof tierCounts]++
    }

    if (paper.isVetted) vettedCount++
    if (paper.analyzedAt && paper.llmAnalysis) analyzedCount++
  }

  return NextResponse.json({
    total: papers.length,
    stages: stageCounts,
    tiers: tierCounts,
    vetted: vettedCount,
    analyzed: analyzedCount,
    completionRate: papers.length > 0 ? ((stageCounts.delivered / papers.length) * 100).toFixed(1) : '0',
  })
}

async function advancePapers() {
  // Auto-advance papers through pipeline stages based on criteria
  let advanced = 0

  // Intake → Vetting: papers with abstracts and DG scores
  const intakePapers = await db.paper.findMany({
    where: {
      pipelineStage: 'intake',
      abstractSummary: { not: null },
    },
  })

  for (const paper of intakePapers) {
    await db.paper.update({
      where: { id: paper.id },
      data: { pipelineStage: 'vetting' },
    })
    advanced++
  }

  // Vetting → Manifest: papers with DG classification complete
  const vettingPapers = await db.paper.findMany({
    where: {
      pipelineStage: 'vetting',
      researchRole: { not: 'context_only' },
    },
  })

  for (const paper of vettingPapers) {
    await db.paper.update({
      where: { id: paper.id },
      data: { pipelineStage: 'manifest' },
    })
    advanced++
  }

  // Manifest → Priority: papers with concept mapping and project fit
  const manifestPapers = await db.paper.findMany({
    where: {
      pipelineStage: 'manifest',
      conceptIds: { not: null },
    },
  })

  for (const paper of manifestPapers) {
    await db.paper.update({
      where: { id: paper.id },
      data: { pipelineStage: 'priority' },
    })
    advanced++
  }

  // Priority → Delivered: papers that are vetted (LLM analyzed)
  const priorityPapers = await db.paper.findMany({
    where: {
      pipelineStage: 'priority',
      isVetted: true,
    },
  })

  for (const paper of priorityPapers) {
    await db.paper.update({
      where: { id: paper.id },
      data: { pipelineStage: 'delivered' },
    })
    advanced++
  }

  return NextResponse.json({
    success: true,
    action: 'advance',
    advanced,
    message: `Advanced ${advanced} papers through pipeline stages`,
  })
}

export async function GET() {
  return getPipelineStatus()
}
