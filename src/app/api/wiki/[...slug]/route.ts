import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const DOCS_ROOT = path.join(process.cwd(), 'docs')

function normalizeSlug(value: string): string {
  return value
    .replace(/\\/g, '/')
    .replace(/\.md$/i, '')
    .split('/')
    .filter((part) => part && part !== '.' && part !== '..')
    .join('/')
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ slug: string[] }> },
) {
  const params = await context.params
  const slug = normalizeSlug(params.slug.join('/'))
  if (!slug) return NextResponse.json({ error: 'slug is required' }, { status: 400 })
  try {
    const file = path.join(DOCS_ROOT, `${slug}.md`)
    const resolved = path.resolve(file)
    if (!resolved.startsWith(path.resolve(DOCS_ROOT))) {
      return NextResponse.json({ error: 'invalid slug' }, { status: 400 })
    }
    const content = await fs.readFile(file, 'utf8')
    return new NextResponse(content, {
      status: 200,
      headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
