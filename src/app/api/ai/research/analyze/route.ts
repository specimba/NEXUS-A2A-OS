import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'

// ── Types ──────────────────────────────────────────────────────────────

type AnalysisType = 'summary' | 'critique' | 'relevance'

interface ResearchAnalyzeRequest {
  paperTitle: string
  paperContent?: string
  paperAbstract?: string
  analysisType: AnalysisType
  focusAreas?: string[]  // optional specific aspects to focus on
  targetProject?: string // optional project context for relevance analysis
}

interface AnalysisResult {
  analysisType: AnalysisType
  paperTitle: string
  content: string
  keyPoints: string[]
  confidence: number
  metadata: {
    model: string
    provider: string
    latencyMs: number
    wordCount: number
    analysisDepth: 'quick' | 'standard' | 'comprehensive'
  }
}

// ── SDK Singleton ──────────────────────────────────────────────────────

let zaiInstance: Awaited<ReturnType<typeof ZAI.create>> | null = null

async function getZAI() {
  if (!zaiInstance) {
    try {
      zaiInstance = await ZAI.create()
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      throw new Error(
        `Failed to initialize z-ai-web-dev-sdk. Ensure ZAI_API_KEY is set. Error: ${msg}`
      )
    }
  }
  return zaiInstance
}

// ── System Prompt Builders ─────────────────────────────────────────────

function buildSystemPrompt(
  analysisType: AnalysisType,
  focusAreas?: string[],
  targetProject?: string
): string {
  const baseContext = `You are a research analysis assistant for NEXUS OS v3.1, a multi-agent AI governance platform.

IMPORTANT CONTEXT about NEXUS OS terminology:
- "Vault" = 5-track memory plane (event, trust, capability, failure_pattern, governance) — NOT a financial vault
- "Trust scores" = AI agent reliability metrics (0-1) — NOT financial credit scores
- "Tokens" = LLM API token usage — NOT cryptocurrency tokens
- "Governance" = AI agent governance and compliance — NOT corporate governance`

  const focusContext = focusAreas && focusAreas.length > 0
    ? `\n\nPay special attention to these aspects: ${focusAreas.join(', ')}.`
    : ''

  const projectContext = targetProject
    ? `\n\nConsider the relevance to this project: "${targetProject}".`
    : ''

  switch (analysisType) {
    case 'summary':
      return `${baseContext}

You are performing a SUMMARY analysis of a research paper. Your goal is to distill the paper into a clear, structured summary.

Your response MUST be a JSON object with this exact structure:
{
  "summary": "2-4 paragraph summary of the paper's key contributions and findings",
  "keyPoints": ["point1", "point2", "point3", "point4", "point5"],
  "methodology": "Brief description of the methodology used",
  "findings": "Summary of main findings",
  "limitations": "Key limitations noted in the paper",
  "futureWork": "Suggested future directions from the paper"
}

Be precise, technical, and avoid oversimplification. Include specific numbers, metrics, or results where available.${focusContext}${projectContext}

Return ONLY the JSON object, no markdown fences or extra text.`

    case 'critique':
      return `${baseContext}

You are performing a CRITIQUE analysis of a research paper. Your goal is to evaluate the paper's strengths, weaknesses, and methodological rigor.

Your response MUST be a JSON object with this exact structure:
{
  "critique": "2-4 paragraph critical analysis of the paper",
  "keyPoints": ["critical_point1", "critical_point2", "critical_point3", "critical_point4", "critical_point5"],
  "strengths": ["strength1", "strength2", "strength3"],
  "weaknesses": ["weakness1", "weakness2", "weakness3"],
  "methodologicalConcerns": ["concern1", "concern2"],
  "overallAssessment": "Brief overall assessment with a qualitative rating (Strong/Good/Adequate/Weak)",
  "improvementSuggestions": ["suggestion1", "suggestion2", "suggestion3"]
}

Be rigorous but fair. Focus on substantive issues rather than stylistic preferences.${focusContext}${projectContext}

Return ONLY the JSON object, no markdown fences or extra text.`

    case 'relevance':
      return `${baseContext}

You are performing a RELEVANCE analysis of a research paper. Your goal is to assess how relevant this paper is to the NEXUS OS multi-agent AI governance platform and its specific subsystems.

Your response MUST be a JSON object with this exact structure:
{
  "relevanceAnalysis": "2-4 paragraph analysis of the paper's relevance to NEXUS OS",
  "keyPoints": ["relevance_point1", "relevance_point2", "relevance_point3", "relevance_point4", "relevance_point5"],
  "relevantSubsystems": [
    {"subsystem": "Bridge|Engine|Governor|Vault|GMR|Swarm|Monitor|Config|StressLab", "relevance": "High|Medium|Low", "reason": "Why it's relevant"}
  ],
  "applicabilityScore": 0.0-1.0,
  "implementationComplexity": "Low|Medium|High",
  "suggestedIntegrationPath": "How this research could be integrated",
  "priorityRecommendation": "P0|P1|P2 with justification",
  "risksAndConsiderations": ["risk1", "risk2"]
}

Consider the NEXUS OS pillars: Bridge (multi-provider routing), Engine (orchestration), Governor (governance/compliance), Vault (memory), GMR (model routing), Swarm (agent coordination), Monitor (observability), Config (configuration).${focusContext}${projectContext}

Return ONLY the JSON object, no markdown fences or extra text.`

    default:
      return `${baseContext}\n\nAnalyze the paper and return a structured JSON response.`
  }
}

// ── Route Handler ──────────────────────────────────────────────────────

/**
 * POST /api/ai/research/analyze
 *
 * Deep paper analysis endpoint powered by z-ai-web-dev-sdk.
 * Supports three analysis types: summary, critique, and relevance.
 *
 * Body: {
 *   paperTitle: string,
 *   paperContent?: string,        // optional full text
 *   paperAbstract?: string,       // optional abstract
 *   analysisType: 'summary' | 'critique' | 'relevance',
 *   focusAreas?: string[],        // optional specific aspects
 *   targetProject?: string        // optional project context
 * }
 *
 * Rate limiting: TODO - Add per-user rate limiting middleware
 */
export async function POST(request: NextRequest) {
  try {
    const body: ResearchAnalyzeRequest = await request.json()
    const {
      paperTitle,
      paperContent,
      paperAbstract,
      analysisType,
      focusAreas,
      targetProject,
    } = body

    // ── Validate input ──
    if (!paperTitle || typeof paperTitle !== 'string' || paperTitle.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: 'paperTitle is required and must not be empty' },
        { status: 400 }
      )
    }

    const validTypes: AnalysisType[] = ['summary', 'critique', 'relevance']
    if (!analysisType || !validTypes.includes(analysisType)) {
      return NextResponse.json(
        { success: false, error: `Invalid analysisType: "${analysisType}". Valid types: ${validTypes.join(', ')}` },
        { status: 400 }
      )
    }

    // Need at least content or abstract
    if (!paperContent && !paperAbstract) {
      return NextResponse.json(
        { success: false, error: 'At least one of paperContent or paperAbstract must be provided' },
        { status: 400 }
      )
    }

    // ── Initialize SDK ──
    const zai = await getZAI()

    // Build the user prompt with available paper information
    const contentToAnalyze = paperContent || paperAbstract || ''
    const contentLabel = paperContent ? 'Full Paper Content' : 'Abstract'

    const userPrompt = `Analyze the following research paper:

Title: ${paperTitle.trim()}

${contentLabel}:
${contentToAnalyze.slice(0, 8000)}${contentToAnalyze.length > 8000 ? '\n\n[Content truncated for analysis — analyzing first 8000 characters]' : ''}`

    const systemPrompt = buildSystemPrompt(analysisType, focusAreas, targetProject)

    const startTime = Date.now()

    // Use lower temperature for analysis tasks for more consistent output
    const temperature = analysisType === 'summary' ? 0.3 : analysisType === 'critique' ? 0.4 : 0.35

    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      thinking: { type: 'disabled' },
      temperature,
    })

    const rawResponse = completion.choices[0]?.message?.content || ''
    const latencyMs = Date.now() - startTime
    const model = completion.model || 'glm-4.7'

    // Parse the JSON response
    let analysisData: Record<string, any>
    try {
      let jsonStr = rawResponse
      const jsonMatch = rawResponse.match(/```(?:json)?\s*([\s\S]*?)```/)
      if (jsonMatch) {
        jsonStr = jsonMatch[1].trim()
      }
      analysisData = JSON.parse(jsonStr)
    } catch {
      // If parsing fails, wrap the raw text
      analysisData = {
        [analysisType]: rawResponse,
        keyPoints: rawResponse.split('\n').filter(l => l.trim().startsWith('-') || l.trim().startsWith('•') || /^\d+\./.test(l.trim())).map(l => l.replace(/^[-•\d.]\s*/, '').trim()).slice(0, 5),
        rawOutput: true,
      }
    }

    // Extract key points from the analysis
    const keyPoints: string[] = analysisData.keyPoints || analysisData.strengths || analysisData.relevantSubsystems?.map((s: any) => `${s.subsystem}: ${s.relevance}`) || []

    // Determine confidence based on content availability and analysis quality
    const confidence = paperContent
      ? 0.9
      : paperAbstract
        ? 0.7
        : 0.4

    // Determine analysis depth
    const analysisDepth = contentToAnalyze.length > 5000 ? 'comprehensive' : contentToAnalyze.length > 1000 ? 'standard' : 'quick'

    const result: AnalysisResult = {
      analysisType,
      paperTitle: paperTitle.trim(),
      content: JSON.stringify(analysisData),
      keyPoints: keyPoints.slice(0, 8),
      confidence,
      metadata: {
        model,
        provider: 'z-ai',
        latencyMs,
        wordCount: rawResponse.split(/\s+/).length,
        analysisDepth,
      },
    }

    return NextResponse.json({
      success: true,
      data: {
        ...result,
        analysis: analysisData,
      },
    })
  } catch (error: any) {
    console.error('AI Research Analyze API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'

    const status = message.includes('rate limited') ? 429
      : message.includes('API key') ? 503
      : message.includes('timed out') ? 504
      : 500

    return NextResponse.json(
      { success: false, error: message },
      { status }
    )
  }
}
