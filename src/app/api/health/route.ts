import { NextResponse } from 'next/server'

/**
 * Simple Health Check Endpoint
 *
 * GET /api/health — Returns basic server availability status.
 * Used by client components to detect if the server is reachable
 * before making expensive API calls (e.g., AI chat completions).
 *
 * This endpoint is intentionally lightweight — no DB queries, no SDK calls.
 * It simply confirms the Next.js server process is alive.
 */

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    timestamp: Date.now(),
    uptime: Math.floor(process.uptime()),
  })
}
