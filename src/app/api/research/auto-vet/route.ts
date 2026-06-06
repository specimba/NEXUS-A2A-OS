import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    zaiInstance = await ZAI.create()
  }
  return zaiInstance
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}))
    const { maxPapers = 5, tier = 'all' } = body

    // Fetch unvetted papers
    const where: Record<string, unknown> = { isVetted: false }
    if (tier !== 'all') where.priorityTier = tier

    const unvetted = await db.paper.findMany({
      where,
      take: Math.min(maxPapers, 20), // Cap at 20 to prevent runaway costs
      orderBy: { relevanceScore: 'desc' },
    })

    if (unvetted.length === 0) {
      return NextResponse.json({ message: 'No unvetted papers found', vetted: 0 })
    }

    // Use z-ai-web-dev-sdk to analyze papers
    const zai = await getZAI()

    const vettedPapers = []

    for (const paper of unvetted) {
      try {
        const prompt = `You are a research analyst for NEXUS OS — a trust-governed multi-agent AI operating system with 8 pillars: Bridge (HMAC auth), Engine (intent routing), Governor (trust scoring), Vault (5-track memory), GMR (model rotation), Swarm (worker pool), Monitor (token budget), Config (constitution).

Analyze this research paper and provide:
1. IMPLEMENTATION TASK: A concrete, specific task describing what to build/integrate from this paper into NEXUS OS (max 100 words)
2. DELIVERABLE: What will be produced (e.g., "Agent trust scoring module", "HMAC session rotation protocol")
3. KEY TAKEAWAY: The single most important insight from this paper for NEXUS OS (max 50 words)
4. PRIORITY: Re-evaluate as P0 (must implement now - safety/critical), P1 (next sprint - high relevance), or P2 (research - future consideration)

Paper Title: ${paper.title}
Abstract: ${paper.abstractSummary || 'No abstract available'}
Category: ${paper.category || 'Unknown'}
DG Score: ${paper.dgFinalScore || 'N/A'}
Research Role: ${paper.researchRole || 'N/A'}
Admission Tier: ${paper.admissionTier || 'N/A'}
Current Priority: ${paper.priorityTier}

Respond in EXACTLY this JSON format:
{"implementationTask": "...", "deliverable": "...", "conclusionTakeaway": "...", "priorityTier": "P0|P1|P2"}`

        const response = await zai.chat.completions.create({
          model: 'glm-4-flash',
          messages: [
            { role: 'system', content: 'You are a precise research analyst. Respond ONLY with valid JSON. No markdown, no explanations.' },
            { role: 'user', content: prompt },
          ],
          temperature: 0.3,
          max_tokens: 500,
        })

        const content = response.choices?.[0]?.message?.content || ''

        // Parse the JSON response
        let analysis: {
          implementationTask: string
          deliverable: string
          conclusionTakeaway: string
          priorityTier: string
        }
        try {
          // Handle potential markdown code blocks
          const jsonStr = content.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim()
          analysis = JSON.parse(jsonStr)
        } catch {
          // Fallback if LLM doesn't return valid JSON
          analysis = {
            implementationTask: `Review and integrate findings from "${paper.title}" into NEXUS ${paper.researchRole || 'core'} module`,
            deliverable: `Integration report for ${paper.category || 'research'} findings`,
            conclusionTakeaway: paper.abstractSummary?.slice(0, 100) || 'Review needed',
            priorityTier: paper.priorityTier || 'P2',
          }
        }

        // Validate priority tier
        const validTiers = ['P0', 'P1', 'P2']
        if (!validTiers.includes(analysis.priorityTier)) {
          analysis.priorityTier = paper.priorityTier || 'P2'
        }

        // Update the paper in DB
        await db.paper.update({
          where: { id: paper.id },
          data: {
            isVetted: true,
            implementationTask: analysis.implementationTask,
            deliverable: analysis.deliverable || paper.pdfUrl,
            conclusionTakeaway: analysis.conclusionTakeaway,
            priorityTier: analysis.priorityTier,
          },
        })

        vettedPapers.push({
          id: paper.id,
          title: paper.title,
          oldPriority: paper.priorityTier,
          newPriority: analysis.priorityTier,
          task: analysis.implementationTask,
        })
      } catch (err) {
        console.error(`Failed to vet paper ${paper.id}:`, err)
        // Still mark as vetted with basic task so it doesn't get stuck
        await db.paper.update({
          where: { id: paper.id },
          data: {
            isVetted: true,
            implementationTask: `Integrate findings from "${paper.title}" — manual review recommended`,
          },
        })
        vettedPapers.push({
          id: paper.id,
          title: paper.title,
          oldPriority: paper.priorityTier,
          newPriority: paper.priorityTier,
          task: 'Manual review needed — LLM analysis failed',
        })
      }
    }

    // Get updated counts
    const totalPapers = await db.paper.count()
    const vettedCount = await db.paper.count({ where: { isVetted: true } })
    const p0Count = await db.paper.count({ where: { priorityTier: 'P0', isVetted: true } })
    const p1Count = await db.paper.count({ where: { priorityTier: 'P1', isVetted: true } })
    const p2Count = await db.paper.count({ where: { priorityTier: 'P2', isVetted: true } })

    return NextResponse.json({
      vetted: vettedPapers.length,
      papers: vettedPapers,
      summary: {
        total: totalPapers,
        vetted: vettedCount,
        unvetted: totalPapers - vettedCount,
        p0: p0Count,
        p1: p1Count,
        p2: p2Count,
      },
    })
  } catch (error) {
    console.error('Auto-vet error:', error)
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
