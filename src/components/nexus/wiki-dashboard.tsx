'use client'

import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { BookOpen, FileText, FolderGit2, Hash, Loader2, Search, ShieldCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'

type WikiFile = {
  slug: string
  title: string
  category: string
  updatedAt: string
  size: number
  headings: string[]
  excerpt: string
}

type WikiIndex = {
  files: WikiFile[]
  categories: string[]
  count: number
  generatedAt: string
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function categoryTone(category: string) {
  if (category === 'research') return 'border-cyan-500/25 bg-cyan-500/10 text-cyan-300'
  if (category === 'operations') return 'border-amber-500/25 bg-amber-500/10 text-amber-300'
  if (category === 'coordination') return 'border-fuchsia-500/25 bg-fuchsia-500/10 text-fuchsia-300'
  if (category === 'handbook') return 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
  return 'border-white/10 bg-white/5 text-muted-foreground'
}

export function WikiDashboard() {
  const [index, setIndex] = useState<WikiIndex | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [active, setActive] = useState<WikiFile | null>(null)
  const [content, setContent] = useState<string | null>(null)
  const [loadingIndex, setLoadingIndex] = useState(true)
  const [loadingPage, setLoadingPage] = useState(false)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<string>('all')

  useEffect(() => {
    let cancelled = false
    setLoadingIndex(true)
    fetch('/api/wiki', { cache: 'no-store' })
      .then((r) => {
        if (!r.ok) throw new Error(`Wiki API failed (${r.status})`)
        return r.json()
      })
      .then((data: WikiIndex) => {
        if (cancelled) return
        setIndex(data)
        setActive(data.files[0] ?? null)
        setError(null)
      })
      .catch((err) => {
        if (!cancelled) {
          setIndex(null)
          setError(err instanceof Error ? err.message : String(err))
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingIndex(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!active) {
      setContent(null)
      return
    }
    let cancelled = false
    setLoadingPage(true)
    fetch(`/api/wiki/${active.slug}`, { cache: 'no-store' })
      .then(async (r) => {
        if (!r.ok) throw new Error(`Wiki read failed (${r.status})`)
        const text = await r.text()
        if (!cancelled) setContent(text)
      })
      .catch((err) => {
        if (!cancelled) {
          setContent(null)
          setError(err instanceof Error ? err.message : String(err))
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingPage(false)
      })
    return () => {
      cancelled = true
    }
  }, [active])

  const files = index?.files ?? []
  const categories = index?.categories ?? []
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return files.filter((file) => {
      const categoryMatch = category === 'all' || file.category === category
      if (!categoryMatch) return false
      if (!needle) return true
      return [file.title, file.slug, file.category, file.excerpt, ...file.headings]
        .join(' ')
        .toLowerCase()
        .includes(needle)
    })
  }, [category, files, query])

  const sourceCounts = useMemo(() => {
    return categories.map((name) => ({
      name,
      count: files.filter((file) => file.category === name).length,
    }))
  }, [categories, files])

  return (
    <div className="h-[calc(100vh-5rem)] overflow-hidden">
      <div className="mb-4 grid gap-3 xl:grid-cols-[1.6fr_1fr_1fr]">
        <Card className="border-emerald-500/20 bg-gradient-to-br from-emerald-950/30 via-background to-background">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <BookOpen className="h-4 w-4 text-emerald-300" />
              NEXUS Wiki Control Surface
              <DataSourceBadge source="api" label="DOCS" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Evidence-first reader over tracked docs knowledge. Raw downloads and GROSS evidence stay outside this panel until source-carded.
            </p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{index?.count ?? 0} pages</Badge>
              <Badge variant="outline">{categories.length} categories</Badge>
              <Badge variant="outline">{index ? `indexed ${formatDate(index.generatedAt)}` : 'index pending'}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-cyan-500/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <ShieldCheck className="h-4 w-4 text-cyan-300" />
              Adoption Gate
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground">
            <p>Docs are readable evidence, not automatic execution authority.</p>
            <p>Promote only after source path, local verification, and NEXUS lane mapping are explicit.</p>
          </CardContent>
        </Card>

        <Card className="border-fuchsia-500/20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <FolderGit2 className="h-4 w-4 text-fuchsia-300" />
              Source Mix
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1.5">
              {sourceCounts.slice(0, 8).map((item) => (
                <Badge key={item.name} variant="outline" className={categoryTone(item.name)}>
                  {item.name} - {item.count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid h-[calc(100%-9.5rem)] gap-4 xl:grid-cols-[380px_1fr]">
        <aside className="flex min-h-0 flex-col rounded-xl border bg-background/70">
          <div className="space-y-3 border-b p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search title, path, heading, excerpt..."
                className="pl-8"
              />
            </div>
            <div className="flex flex-wrap gap-1.5" aria-label="Wiki categories">
              <Button type="button" size="sm" variant={category === 'all' ? 'default' : 'outline'} onClick={() => setCategory('all')}>
                All
              </Button>
              {categories.map((name) => (
                <Button key={name} type="button" size="sm" variant={category === name ? 'default' : 'outline'} onClick={() => setCategory(name)} className="capitalize">
                  {name}
                </Button>
              ))}
            </div>
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="space-y-2 p-3">
              {loadingIndex && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Loading wiki index...
                </div>
              )}
              {!loadingIndex && error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300">{error}</div>}
              {!loadingIndex && !error && filtered.length === 0 && <div className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">No matching source-carded docs found.</div>}
              {filtered.map((file) => (
                <button
                  key={file.slug}
                  type="button"
                  onClick={() => setActive(file)}
                  className={cn('w-full rounded-lg border p-3 text-left transition-colors', active?.slug === file.slug ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-white/10 bg-white/[0.02] hover:bg-white/[0.05]')}
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{file.title}</div>
                      <div className="truncate text-[11px] text-muted-foreground">{file.slug}</div>
                    </div>
                    <Badge variant="outline" className={cn('shrink-0 capitalize', categoryTone(file.category))}>{file.category}</Badge>
                  </div>
                  <p className="line-clamp-2 text-xs text-muted-foreground">{file.excerpt || 'No excerpt available.'}</p>
                  <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
                    <span>{formatDate(file.updatedAt)}</span>
                    <span>{formatBytes(file.size)}</span>
                  </div>
                </button>
              ))}
            </div>
          </ScrollArea>
        </aside>

        <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border bg-background/70">
          <div className="flex items-start justify-between gap-4 border-b p-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <FileText className="h-4 w-4 text-emerald-300" />
                <h2 className="truncate text-lg font-semibold">{active?.title ?? 'Select a wiki page'}</h2>
                {active && <Badge variant="outline" className={categoryTone(active.category)}>{active.category}</Badge>}
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {active ? `${active.slug}.md - ${formatBytes(active.size)} - updated ${formatDate(active.updatedAt)}` : 'No document selected'}
              </p>
            </div>
            {active?.headings?.length ? (
              <div className="hidden max-w-md flex-wrap justify-end gap-1 lg:flex">
                {active.headings.slice(0, 4).map((heading) => (
                  <Badge key={heading} variant="secondary" className="max-w-48 truncate">
                    <Hash className="mr-1 h-3 w-3" />
                    {heading}
                  </Badge>
                ))}
              </div>
            ) : null}
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="p-5">
              {loadingPage && <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading document...</div>}
              {!loadingPage && !active && <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">Choose a source-carded document from the left panel.</div>}
              {!loadingPage && active && !content && <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">Document content is unavailable.</div>}
              {content && (
                <article className="prose prose-invert max-w-none prose-headings:scroll-m-20 prose-headings:text-foreground prose-p:text-muted-foreground prose-li:text-muted-foreground prose-strong:text-foreground prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-emerald-200 prose-pre:border prose-pre:bg-black/30">
                  <ReactMarkdown>{content}</ReactMarkdown>
                </article>
              )}
            </div>
          </ScrollArea>
        </section>
      </div>
    </div>
  )
}
