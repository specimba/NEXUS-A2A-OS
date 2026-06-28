import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'

const DOCS_ROOT = path.join(process.cwd(), 'docs')
const WIKI_DIR = path.join(DOCS_ROOT, 'wiki')
// Canonical ARCHIVIST wiki — fit.py writes dossiers here
const ARCHIVIST_WIKI = path.join(process.cwd(), 'nexus_os', 'archivist', 'wiki')
const ARCHIVIST_DOSSIERS = path.join(ARCHIVIST_WIKI, 'dossiers')

type WikiIndexFile = {
  slug: string
  title: string
  category: string
  updatedAt: string
  size: number
  headings: string[]
  excerpt: string
}

const INDEXED_DOC_DIRS = new Set([
  'wiki',
  'research',
  'coordination',
  'planning',
  'operations',
  'handbook',
  'governance',
  'hermes',
  'grounding',
])

function normalizeSlug(value: string): string {
  return value
    .replace(/\\/g, '/')
    .replace(/\.md$/i, '')
    .split('/')
    .filter((part) => part && part !== '.' && part !== '..')
    .join('/')
}

function titleFromMarkdown(content: string, fallback: string): string {
  const heading = content.match(/^#\s+(.+)$/m)?.[1]?.trim()
  if (heading) return heading
  return fallback
    .split('/')
    .at(-1)!
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (m) => m.toUpperCase())
}

function extractHeadings(content: string): string[] {
  return Array.from(content.matchAll(/^#{1,3}\s+(.+)$/gm))
    .map((match) => match[1].trim())
    .slice(0, 8)
}

function summarize(content: string): string {
  return content
    .replace(/^---[\s\S]*?---/m, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 220)
}

async function collectMarkdownFiles(dir: string, rootLabel: string): Promise<WikiIndexFile[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  const files: WikiIndexFile[] = []
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...await collectMarkdownFiles(full, rootLabel))
      continue
    }
    if (!entry.isFile() || !entry.name.endsWith('.md')) continue

    const stat = await fs.stat(full)
    const content = await fs.readFile(full, 'utf8')
    const relative = path.relative(DOCS_ROOT, full).replace(/\\/g, '/')
    const slug = normalizeSlug(relative)
    files.push({
      slug,
      title: titleFromMarkdown(content, slug),
      category: rootLabel,
      updatedAt: stat.mtime.toISOString(),
      size: stat.size,
      headings: extractHeadings(content),
      excerpt: summarize(content),
    })
  }
  return files
}

export async function GET() {
  try {
    const docsEntries = await fs.readdir(DOCS_ROOT, { withFileTypes: true })
    const groups = await Promise.all(
      docsEntries
        .filter((entry) => entry.isDirectory() && INDEXED_DOC_DIRS.has(entry.name))
        .map((entry) => collectMarkdownFiles(path.join(DOCS_ROOT, entry.name), entry.name)),
    )

    // Also index ARCHIVIST wiki (sources, entities, concepts, dossiers)
    const archivistGroups: Promise<WikiIndexFile[]>[] = []
    if (await fs.stat(ARCHIVIST_WIKI).then(() => true).catch(() => false)) {
      const wikiDirs = await fs.readdir(ARCHIVIST_WIKI, { withFileTypes: true })
      for (const entry of wikiDirs) {
        if (entry.isDirectory() && !entry.name.startsWith('.')) {
          archivistGroups.push(
            collectMarkdownFiles(
              path.join(ARCHIVIST_WIKI, entry.name),
              `archivist/${entry.name}`,
            ),
          )
        }
      }
    }

    const allGroups = await Promise.all([...groups, ...archivistGroups])
    const files = allGroups
      .flat()
      .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))

    const categories = Array.from(new Set(files.map((file) => file.category))).sort()
    return NextResponse.json({
      files,
      categories,
      root: 'docs + archivist/wiki',
      count: files.length,
      generatedAt: new Date().toISOString(),
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { slug, title, content } = body
    if (!slug || typeof slug !== 'string') {
      return NextResponse.json({ error: 'slug is required' }, { status: 400 })
    }
    const safeSlug = normalizeSlug(slug)
    const file = path.join(WIKI_DIR, `${safeSlug}.md`)
    const resolved = path.resolve(file)
    if (!resolved.startsWith(path.resolve(WIKI_DIR))) {
      return NextResponse.json({ error: 'invalid slug' }, { status: 400 })
    }
    await fs.mkdir(path.dirname(file), { recursive: true })
    await fs.writeFile(file, content ?? `# ${title ?? slug}\n`, 'utf8')
    return NextResponse.json({ ok: true, slug: safeSlug })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}

