import { NextRequest, NextResponse } from 'next/server'
import { db } from '@/lib/db'
import { classifyPaper, CONCEPT_META, ROLE_META, TIER_META } from '@/lib/dg/classification-engine'
import type { PaperInput } from '@/lib/dg/classification-engine'

/**
 * arXiv Paper Crawler API
 *
 * Direct integration with the arXiv public API — NO API KEY REQUIRED.
 * Based on DoppelGround's arxiv_adapter_clean.py v1.2 (Hardened).
 *
 * Endpoints:
 *   GET /api/arxiv?q=<query>&max=<n>&category=<cat>&sort=<field>&order=<dir>
 *   GET /api/arxiv?id=<arxiv-id>
 *   GET /api/arxiv?trending=true
 *
 * Sort options: relevance (default), lastUpdatedDate, submittedDate
 * Categories: cs.AI, cs.CL, cs.LG, cs.MA, stat.ML, etc.
 */

const ARXIV_API_BASE = 'http://export.arxiv.org/api/query?'
const DEFAULT_TIMEOUT = 15000 // ms
const MAX_RETRIES = 3
const RETRY_DELAY_BASE = 1000 // ms

// arXiv category mappings for NEXUS OS domains
const NEXUS_DOMAINS: Record<string, string[]> = {
  'AI Governance': ['cs.AI', 'cs.MA', 'cs.CY'],
  'Multi-Agent Systems': ['cs.MA', 'cs.AI', 'cs.GT'],
  'LLM Research': ['cs.CL', 'cs.AI', 'cs.LG'],
  'Machine Learning': ['cs.LG', 'stat.ML', 'cs.AI'],
  'NLP & Understanding': ['cs.CL', 'cs.AI'],
  'Robotics & Embodied AI': ['cs.RO', 'cs.AI'],
  'Safety & Alignment': ['cs.AI', 'cs.CY', 'cs.LG'],
  'Reasoning & Planning': ['cs.AI', 'cs.LO'],
}

interface ArxivPaper {
  id: string
  arxivId: string
  title: string
  summary: string
  pdfUrl: string
  category: string
  categories: string[]
  authors: string[]
  published: string
  updated: string
  provenance: {
    source: string
    fetchTimestamp: number
    status: string
    query?: string
  }
}

interface PaperResult {
  id: string
  dbId: string | null
  arxivId: string
  title: string
  summary: string
  pdfUrl: string
  category: string
  categories: string[]
  authors: string[]
  published: string
  updated: string
  relevanceScore: number
  source: string
  fetchedAt: string
  isNew: boolean
  // DG Classification
  admissionTier?: string
  researchRole?: string
  conceptIds?: string[]
  projectFit?: string
  dgFinalScore?: number
  promotable?: boolean
  priorityBand?: string
}

// ── XML Parsing (no external deps needed) ────────────────────────────

function parseArxivXml(xml: string): ArxivPaper[] {
  const papers: ArxivPaper[] = []

  // Simple XML parser — no DOM dependency needed for arXiv's flat Atom feed
  const entryRegex = /<entry>([\s\S]*?)<\/entry>/g
  let entryMatch: RegExpExecArray | null

  while ((entryMatch = entryRegex.exec(xml)) !== null) {
    const entry = entryMatch[1]

    // Extract ID
    const idMatch = entry.match(/<id>([\s\S]*?)<\/id>/)
    const idText = idMatch ? idMatch[1].trim() : ''
    const arxivId = idText.replace('http://arxiv.org/abs/', '').replace('https://arxiv.org/abs/', '')

    // Extract title
    const titleMatch = entry.match(/<title>([\s\S]*?)<\/title>/)
    const title = titleMatch ? titleMatch[1].replace(/\s+/g, ' ').trim() : 'Unknown'

    // Extract summary
    const summaryMatch = entry.match(/<summary>([\s\S]*?)<\/summary>/)
    const summary = summaryMatch ? summaryMatch[1].replace(/\s+/g, ' ').trim() : ''

    // Extract primary category
    const catMatch = entry.match(/<arxiv:primary_category[^>]*term="([^"]*)"/)
    const category = catMatch ? catMatch[1] : 'unknown'

    // Extract all categories
    const categories: string[] = []
    const catRegex = /<category[^>]*term="([^"]*)"/g
    let catMatch2: RegExpExecArray | null
    while ((catMatch2 = catRegex.exec(entry)) !== null) {
      if (catMatch2[1]) categories.push(catMatch2[1])
    }

    // Extract authors
    const authors: string[] = []
    const authorRegex = /<author>[\s\S]*?<name>([\s\S]*?)<\/name>[\s\S]*?<\/author>/g
    let authorMatch: RegExpExecArray | null
    while ((authorMatch = authorRegex.exec(entry)) !== null) {
      if (authorMatch[1]) authors.push(authorMatch[1].trim())
    }

    // Extract PDF URL
    let pdfUrl = ''
    const pdfMatch = entry.match(/<link[^>]*type="application\/pdf"[^>]*href="([^"]*)"/)
    if (pdfMatch) {
      pdfUrl = pdfMatch[1]
    } else {
      // Construct PDF URL from arXiv ID
      if (arxivId) {
        pdfUrl = `https://arxiv.org/pdf/${arxivId}.pdf`
      }
    }

    // Extract published / updated dates
    const publishedMatch = entry.match(/<published>([\s\S]*?)<\/published>/)
    const updatedMatch = entry.match(/<updated>([\s\S]*?)<\/updated>/)
    const published = publishedMatch ? publishedMatch[1].trim() : ''
    const updated = updatedMatch ? updatedMatch[1].trim() : ''

    papers.push({
      id: `arxiv-${arxivId}`,
      arxivId,
      title,
      summary,
      pdfUrl,
      category,
      categories,
      authors,
      published,
      updated,
      provenance: {
        source: 'arXiv_API',
        fetchTimestamp: Date.now(),
        status: 'VALIDATED',
      },
    })
  }

  return papers
}

// ── Fetch with Retry ─────────────────────────────────────────────────

async function fetchWithRetry(url: string): Promise<string> {
  let lastError: Error | null = null

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT)

      const response = await fetch(url, {
        signal: controller.signal,
        headers: {
          'User-Agent': 'NEXUS-OS-Crawler/3.1 (Research Agent; +https://github.com/nexus-os)',
          'Accept': 'application/atom+xml',
        },
      })

      clearTimeout(timeout)

      if (!response.ok) {
        throw new Error(`arXiv API returned ${response.status}: ${response.statusText}`)
      }

      return await response.text()
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))

      if (attempt < MAX_RETRIES - 1) {
        // Exponential backoff
        const delay = RETRY_DELAY_BASE * Math.pow(2, attempt)
        await new Promise(resolve => setTimeout(resolve, delay))
      }
    }
  }

  throw new Error(`arXiv API: Persistent failure after ${MAX_RETRIES} attempts. Last error: ${lastError?.message}`)
}

// ── Search Papers ────────────────────────────────────────────────────

async function searchPapers(query: string, maxResults: number, category?: string, sortBy?: string, sortOrder?: string): Promise<ArxivPaper[]> {
  const params = new URLSearchParams()
  params.set('search_query', `all:${query}${category ? ` AND cat:${category}` : ''}`)
  params.set('start', '0')
  params.set('max_results', String(Math.min(maxResults, 50)))
  params.set('sortBy', sortBy || 'relevance')
  params.set('sortOrder', sortOrder || 'descending')

  const url = ARXIV_API_BASE + params.toString()
  const xml = await fetchWithRetry(url)
  return parseArxivXml(xml)
}

// ── Fetch by arXiv ID ────────────────────────────────────────────────

async function fetchById(arxivId: string): Promise<ArxivPaper | null> {
  const params = new URLSearchParams()
  params.set('id_list', arxivId)
  params.set('max_results', '1')

  const url = ARXIV_API_BASE + params.toString()
  const xml = await fetchWithRetry(url)
  const papers = parseArxivXml(xml)
  return papers[0] || null
}

// ── Fetch Trending Papers ────────────────────────────────────────────

async function fetchTrending(maxResults: number = 10): Promise<ArxivPaper[]> {
  // Fetch recent papers from key NEXUS OS domains
  const queries = [
    { query: 'multi-agent systems', category: 'cs.MA' },
    { query: 'large language model', category: 'cs.CL' },
    { query: 'AI governance alignment', category: 'cs.AI' },
  ]

  const perQuery = Math.ceil(maxResults / queries.length)
  const allPapers: ArxivPaper[] = []
  const seenIds = new Set<string>()

  for (const { query, category } of queries) {
    try {
      const papers = await searchPapers(query, perQuery, category, 'submittedDate', 'descending')
      for (const paper of papers) {
        if (!seenIds.has(paper.arxivId)) {
          seenIds.add(paper.arxivId)
          allPapers.push(paper)
        }
      }
    } catch {
      // Continue with other queries even if one fails
    }
  }

  return allPapers.slice(0, maxResults)
}

// ── Save papers to database (with DG classification) ─────────────────

async function savePapersToDb(papers: ArxivPaper[], query?: string): Promise<PaperResult[]> {
  const saved: PaperResult[] = []

  // Get existing papers for crowding/prior-seen calculation
  const existingPapers = await db.paper.findMany({
    select: { title: true, category: true },
    take: 200,
    orderBy: { createdAt: 'desc' },
  })

  for (const paper of papers) {
    try {
      const externalId = `arxiv-${paper.arxivId}`

      // Check if paper already exists
      const existing = await db.paper.findFirst({
        where: {
          OR: [
            { externalId },
            { title: paper.title },
            { pdfUrl: paper.pdfUrl },
          ],
        },
      })

      if (existing) {
        saved.push({
          id: `arxiv-${paper.arxivId}`,
          dbId: existing.id,
          arxivId: paper.arxivId,
          title: existing.title,
          summary: existing.abstractSummary || paper.summary.slice(0, 500),
          pdfUrl: existing.pdfUrl || paper.pdfUrl,
          category: paper.category,
          categories: paper.categories,
          authors: paper.authors,
          published: paper.published,
          updated: paper.updated,
          relevanceScore: existing.relevanceScore,
          source: 'arxiv-existing',
          fetchedAt: new Date().toISOString(),
          isNew: false,
          // DG classification from DB
          admissionTier: existing.admissionTier as PaperResult['admissionTier'],
          researchRole: existing.researchRole as PaperResult['researchRole'],
          conceptIds: existing.conceptIds ? JSON.parse(existing.conceptIds) : [],
          projectFit: existing.projectFit as PaperResult['projectFit'],
          dgFinalScore: existing.dgFinalScore,
          promotable: existing.promotable,
          priorityBand: existing.priorityTier as PaperResult['priorityBand'],
        })
      } else {
        // Run DG classification engine
        const classification = classifyPaper({
          title: paper.title,
          summary: paper.summary,
          category: paper.category,
          categories: paper.categories,
          pdfUrl: paper.pdfUrl,
          arxivId: paper.arxivId,
          sourceType: 'paper',
          sourceSubtype: 'arxiv_pdf',
          existingPaperCount: existingPapers.length,
          seenTitles: existingPapers.map(p => p.title),
        })

        const created = await db.paper.create({
          data: {
            externalId,
            type: 'paper',
            title: paper.title,
            pdfUrl: paper.pdfUrl,
            abstractSummary: paper.summary.slice(0, 1000),
            authors: JSON.stringify(paper.authors),
            publishedDate: paper.published,
            category: paper.category,
            categories: JSON.stringify(paper.categories),
            // DG Classification
            admissionTier: classification.admissionTier,
            sourceFamily: classification.sourceFamily,
            sourceSubtype: classification.sourceSubtype,
            researchRole: classification.researchRole,
            conceptIds: JSON.stringify(classification.conceptIds),
            projectFit: classification.projectFit,
            // DG Scoring
            relevanceScore: classification.relevanceScore,
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
            // Priority
            priorityTier: classification.priorityBand === 'HOLD' ? 'P2' : classification.priorityBand,
            implementationTask: 'Pending review',
            deliverable: paper.pdfUrl,
            isVetted: false,
            // Provenance
            nexusMapping: JSON.stringify(classification.conceptIds.map(id => CONCEPT_META[id]?.title || id)),
            keyNumbers: JSON.stringify({
              authors: paper.authors.length,
              categories: paper.categories.length,
              primaryCategory: paper.category,
              dgScore: classification.dgFinalScore,
              researchRole: classification.researchRole,
            }),
            traceRef: `arxiv:${new Date().toISOString().replace(/[:.]/g, '')}:${externalId}`,
            provenanceSource: 'arxiv_api',
          },
        })

        saved.push({
          id: `arxiv-${paper.arxivId}`,
          dbId: created.id,
          arxivId: paper.arxivId,
          title: paper.title,
          summary: paper.summary.slice(0, 500),
          pdfUrl: paper.pdfUrl,
          category: paper.category,
          categories: paper.categories,
          authors: paper.authors,
          published: paper.published,
          updated: paper.updated,
          relevanceScore: classification.relevanceScore,
          source: 'arxiv-new',
          fetchedAt: new Date().toISOString(),
          isNew: true,
          // DG Classification
          admissionTier: classification.admissionTier,
          researchRole: classification.researchRole,
          conceptIds: classification.conceptIds,
          projectFit: classification.projectFit,
          dgFinalScore: classification.dgFinalScore,
          promotable: classification.promotable,
          priorityBand: classification.priorityBand,
        })
      }
    } catch (err) {
      console.error('Failed to save arXiv paper:', paper.arxivId, err)
      // Still include the paper even if DB save fails
      const classification = classifyPaper({
        title: paper.title,
        summary: paper.summary,
        category: paper.category,
        arxivId: paper.arxivId,
        sourceType: 'paper',
        sourceSubtype: 'arxiv_pdf',
      })

      saved.push({
        id: `arxiv-${paper.arxivId}`,
        dbId: null,
        arxivId: paper.arxivId,
        title: paper.title,
        summary: paper.summary.slice(0, 500),
        pdfUrl: paper.pdfUrl,
        category: paper.category,
        categories: paper.categories,
        authors: paper.authors,
        published: paper.published,
        updated: paper.updated,
        relevanceScore: classification.relevanceScore,
        source: 'arxiv-unsaved',
        fetchedAt: new Date().toISOString(),
        isNew: true,
        admissionTier: classification.admissionTier,
        researchRole: classification.researchRole,
        conceptIds: classification.conceptIds,
        projectFit: classification.projectFit,
        dgFinalScore: classification.dgFinalScore,
        promotable: classification.promotable,
        priorityBand: classification.priorityBand,
      })
    }
  }

  return saved
}

// ── GET Handler ──────────────────────────────────────────────────────

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)

    // Single paper fetch by ID
    const paperId = searchParams.get('id')
    if (paperId) {
      const paper = await fetchById(paperId)
      if (!paper) {
        return NextResponse.json({ error: 'Paper not found', arxivId: paperId }, { status: 404 })
      }
      const saved = await savePapersToDb([paper])
      return NextResponse.json({
        paper: saved[0],
        provider: 'arxiv-direct',
      })
    }

    // Trending papers
    const trending = searchParams.get('trending')
    if (trending === 'true') {
      const maxResults = Math.min(parseInt(searchParams.get('max') || '10'), 30)
      const papers = await fetchTrending(maxResults)
      const saved = await savePapersToDb(papers)

      return NextResponse.json({
        papers: saved,
        count: saved.length,
        provider: 'arxiv-trending',
        newCount: saved.filter(p => p.isNew).length,
        existingCount: saved.filter(p => !p.isNew).length,
      })
    }

    // Category browsing
    const category = searchParams.get('category') || ''
    const query = searchParams.get('q') || 'AI governance multi-agent systems'
    const maxResults = Math.min(parseInt(searchParams.get('max') || '10'), 50)
    const sortBy = searchParams.get('sort') || 'relevance'
    const sortOrder = searchParams.get('order') || 'descending'

    const papers = await searchPapers(query, maxResults, category || undefined, sortBy, sortOrder)
    const saved = await savePapersToDb(papers, query)

    return NextResponse.json({
      papers: saved,
      query,
      count: saved.length,
      category: category || 'all',
      sortBy,
      sortOrder,
      provider: 'arxiv-search',
      newCount: saved.filter(p => p.isNew).length,
      existingCount: saved.filter(p => !p.isNew).length,
    })
  } catch (error) {
    console.error('arXiv API error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

// ── POST Handler (pipeline queue) ────────────────────────────────────

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { topic, maxResults = 5, category, sortBy = 'submittedDate', sortOrder = 'descending' } = body as {
      topic?: string
      maxResults?: number
      category?: string
      sortBy?: string
      sortOrder?: string
    }

    const query = topic || 'multi-agent AI systems governance'
    const papers = await searchPapers(query, Math.min(maxResults, 20), category, sortBy, sortOrder)
    const saved = await savePapersToDb(papers, query)

    const queuedPapers = saved.map(p => ({
      dbId: p.dbId,
      externalId: p.id,
      arxivId: p.arxivId,
      title: p.title,
      abstract: p.summary?.slice(0, 300) || '',
      pdfUrl: p.pdfUrl,
      category: p.category,
      authors: p.authors,
      published: p.published,
      relevanceScore: p.relevanceScore,
      priorityTier: p.relevanceScore > 0.8 ? 'P0' : p.relevanceScore > 0.5 ? 'P1' : 'P2',
      source: 'arxiv',
      isNew: p.isNew,
    }))

    return NextResponse.json({
      queued: queuedPapers,
      count: queuedPapers.length,
      topic: topic || 'trending',
      provider: 'arxiv-search',
      message: `${queuedPapers.length} papers found via arXiv. ${queuedPapers.filter(p => p.isNew).length} new papers saved to database.`,
    })
  } catch (error) {
    console.error('arXiv queue error:', error)
    const message = error instanceof Error ? error.message : 'Internal server error'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
