import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const DOCS_ROOT = path.join(process.cwd(), 'docs')
const ARCHIVIST_WIKI = path.join(process.cwd(), 'nexus_os', 'archivist', 'wiki')

function normalizeSlug(value: string): string {
  return value
    .replace(/\\/g, '/')
    .replace(/\.md$/i, '')
    .split('/')
    .filter((part) => part && part !== '.' && part !== '..')
    .join('/')
}

function isSubPath(child: string, parent: string): boolean {
  return path.resolve(child).startsWith(path.resolve(parent))
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
) {
  const params = await context.params
  const slug = normalizeSlug(params.slug.join('/'))
  if (!slug) return NextResponse.json({ error: 'slug is required' }, { status: 400 })

  // Try docs/ first
  const docsFile = path.join(DOCS_ROOT, `${slug}.md`)
  if (isSubPath(docsFile, DOCS_ROOT)) {
    try {
      const content = await fs.readFile(docsFile, 'utf8')
      return new NextResponse(content, {
        status: 200,
        headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
      })
    } catch {
      // Not in docs/ — fall through to archivist/wiki
    }
  }

  // Fall back to archivist/wiki/
  const archivistFile = path.join(ARCHIVIST_WIKI, `${slug}.md`)
  if (isSubPath(archivistFile, ARCHIVIST_WIKI)) {
    try {
      const content = await fs.readFile(archivistFile, 'utf8')
      return new NextResponse(content, {
        status: 200,
        headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
      })
    } catch {
      // Not in either location
    }
  }

  return NextResponse.json({ error: `wiki page not found: ${slug}` }, { status: 404 })
}
