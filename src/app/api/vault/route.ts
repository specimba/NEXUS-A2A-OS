import { db } from '@/lib/db'
import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  try {
    const entries = await db.vaultEntry.findMany({
      take: 100,
      orderBy: { createdAt: 'desc' },
      include: { agent: { select: { name: true } } },
    })
    return NextResponse.json({ entries })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { action } = body

    if (action !== 'verify_chain') {
      return NextResponse.json(
        { error: `Unknown action: ${action}. Valid action: verify_chain` },
        { status: 400 }
      )
    }

    const entries = await db.vaultEntry.findMany({
      orderBy: { createdAt: 'asc' },
      include: { agent: { select: { name: true } } },
    })

    const issues: string[] = []

    // Check that entries exist
    if (entries.length === 0) {
      issues.push('No vault entries found in the chain')
    }

    // Verify each entry has a valid agent reference
    for (const entry of entries) {
      if (!entry.agentId) {
        issues.push(`Entry ${entry.id} has no agent reference`)
      }
      if (!entry.track) {
        issues.push(`Entry ${entry.id} has no track specified`)
      }
      if (!entry.key) {
        issues.push(`Entry ${entry.id} has no key specified`)
      }
      // Try to parse the value as JSON
      try {
        JSON.parse(entry.value)
      } catch {
        issues.push(`Entry ${entry.id} has invalid JSON value`)
      }
    }

    // Verify chronological ordering — entries should have monotonically increasing timestamps
    for (let i = 1; i < entries.length; i++) {
      if (entries[i].createdAt < entries[i - 1].createdAt) {
        issues.push(
          `Entry ${entries[i].id} has timestamp before previous entry ${entries[i - 1].id}`
        )
      }
    }

    // Verify track consistency — each track should have entries in order
    const trackEntries = new Map<string, typeof entries>()
    for (const entry of entries) {
      const track = entry.track
      if (!trackEntries.has(track)) {
        trackEntries.set(track, [])
      }
      trackEntries.get(track)!.push(entry)
    }

    // Check that scores are within valid range
    for (const entry of entries) {
      if (entry.score < 0 || entry.score > 1) {
        issues.push(`Entry ${entry.id} has score outside valid range [0, 1]: ${entry.score}`)
      }
    }

    const valid = issues.length === 0

    return NextResponse.json({
      valid,
      entryCount: entries.length,
      issues,
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
