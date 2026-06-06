'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  GitPullRequest,
  GitCommit,
  GitBranch,
  GitFork,
  Star,
  ExternalLink,
  RefreshCw,
  Loader2,
  AlertCircle,
  Eye,
  Clock,
  FileCode,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  GitMerge,
  ShieldCheck,
  Globe,
  Lock,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { staggerContainer, staggerItem } from '@/components/nexus/tab-content'
import { DataSourceBadge } from '@/components/nexus/data-source-badge'
import { toast } from 'sonner'

// ── Types matching actual API responses ────────────────────────────

interface RepoData {
  name: string
  full_name: string
  description: string
  language: string
  stars: number
  forks: number
  open_issues: number
  topics: string[]
  updated_at: string
  pushed_at: string
  private: boolean
  default_branch: string
  visibility: string
  html_url: string
}

interface RepoResult {
  repo: string
  success: boolean
  data?: RepoData
  error?: string
}

interface PullData {
  number: number
  title: string
  state: string
  user: string
  created_at: string
  updated_at: string
  commits: number
  additions: number
  deletions: number
  changed_files: number
  mergeable: boolean | null
  mergeable_state: string
  head_ref: string
  base_ref: string
  body_preview: string | null
  html_url: string
  repo: string
}

interface CommitData {
  sha: string
  message: string
  author: string
  date: string
  html_url: string
  repo: string
}

interface BranchData {
  name: string
  repo: string
}

// ── Repo badge helper ──────────────────────────────────────────────

function getRepoBadge(repoFullName: string) {
  if (repoFullName.includes('nexusalpha')) {
    return (
      <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-emerald-700/30 text-[9px]">
        nexusalpha
      </Badge>
    )
  }
  return (
    <Badge className="bg-amber-600/15 text-amber-600 dark:text-amber-400 border-amber-700/30 text-[9px]">
      nexusdashboards
    </Badge>
  )
}

function getRepoKeyBadge(key: string) {
  if (key === 'alpha') {
    return (
      <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-emerald-700/30 text-[9px]">
        nexusalpha
      </Badge>
    )
  }
  return (
    <Badge className="bg-amber-600/15 text-amber-600 dark:text-amber-400 border-amber-700/30 text-[9px]">
      nexusdashboards
    </Badge>
  )
}

function getMergeableBadge(state: string) {
  switch (state) {
    case 'mergeable':
      return (
        <Badge className="bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0 text-[9px]">
          <CheckCircle2 className="h-2.5 w-2.5 mr-1" />
          Mergeable
        </Badge>
      )
    case 'unstable':
      return (
        <Badge className="bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0 text-[9px]">
          <AlertTriangle className="h-2.5 w-2.5 mr-1" />
          Unstable
        </Badge>
      )
    case 'conflicting':
      return (
        <Badge className="bg-red-600/15 text-red-600 dark:text-red-400 border-0 text-[9px]">
          <XCircle className="h-2.5 w-2.5 mr-1" />
          Conflicting
        </Badge>
      )
    case 'unknown':
      return (
        <Badge variant="outline" className="text-[9px]">
          <Clock className="h-2.5 w-2.5 mr-1" />
          Checking
        </Badge>
      )
    default:
      return (
        <Badge variant="outline" className="text-[9px]">{state}</Badge>
      )
  }
}

function getBranchPrefixBadge(name: string) {
  if (name.startsWith('gt/')) {
    return (
      <Badge className="bg-cyan-600/15 text-cyan-600 dark:text-cyan-400 border-cyan-700/30 text-[9px]">
        gt/
      </Badge>
    )
  }
  if (name.startsWith('convoy/')) {
    return (
      <Badge className="bg-purple-600/15 text-purple-600 dark:text-purple-400 border-purple-700/30 text-[9px]">
        convoy/
      </Badge>
    )
  }
  if (name.startsWith('feature/')) {
    return (
      <Badge className="bg-blue-600/15 text-blue-600 dark:text-blue-400 border-blue-700/30 text-[9px]">
        feature/
      </Badge>
    )
  }
  return null
}

// ── Format helpers ─────────────────────────────────────────────────

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  if (diffMs < 0) return 'just now'
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatPushTime(dateStr: string): string {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function truncateMessage(msg: string, maxLen = 72): string {
  if (!msg) return ''
  if (msg.length <= maxLen) return msg
  return msg.slice(0, maxLen - 3) + '...'
}

// ── Section 1: Repository Overview Cards ───────────────────────────

function RepositoryOverview({ repos }: { repos: RepoResult[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {repos.map((repoResult, idx) => (
        <motion.div key={repoResult.repo} variants={staggerItem} initial="hidden" animate="visible">
          <Card className="relative overflow-hidden border-border/50 hover:border-emerald-600/30 transition-all duration-300 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-transparent" />
            <CardContent className="relative p-4">
              {!repoResult.success ? (
                <div className="flex flex-col items-center justify-center py-4 text-muted-foreground">
                  <AlertCircle className="h-6 w-6 mb-2 text-red-500" />
                  <span className="text-xs">Failed to load: {repoResult.error || 'Unknown error'}</span>
                </div>
              ) : repoResult.data ? (
                <>
                  {/* Header row */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <FileCode className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <h3 className="text-sm font-semibold text-foreground truncate">{repoResult.data.name}</h3>
                        <Badge
                          variant="outline"
                          className="text-[8px] px-1.5 py-0 h-4 shrink-0 uppercase tracking-wider"
                        >
                          {repoResult.data.private ? (
                            <Lock className="h-2.5 w-2.5 mr-0.5" />
                          ) : (
                            <Globe className="h-2.5 w-2.5 mr-0.5" />
                          )}
                          {repoResult.data.visibility}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                        {repoResult.data.description || 'No description'}
                      </p>
                    </div>
                    <a href={repoResult.data.html_url} target="_blank" rel="noopener noreferrer">
                      <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0 text-muted-foreground hover:text-foreground">
                        <ExternalLink className="h-3.5 w-3.5" />
                      </Button>
                    </a>
                  </div>

                  {/* Stats row */}
                  <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full bg-blue-500 shrink-0" />
                      {repoResult.data.language || '—'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3 text-amber-500" />
                      <span className="tabular-nums">{repoResult.data.stars}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <GitFork className="h-3 w-3" />
                      <span className="tabular-nums">{repoResult.data.forks}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      <span className="tabular-nums">{repoResult.data.open_issues}</span>
                    </span>
                  </div>

                  {/* Footer */}
                  <div className="mt-3 flex items-center justify-between">
                    <div className="flex flex-wrap gap-1">
                      {repoResult.data.topics?.slice(0, 3).map((topic) => (
                        <Badge key={topic} variant="outline" className="text-[8px] px-1.5 py-0 h-4 border-emerald-700/30 text-emerald-600 dark:text-emerald-400">
                          {topic}
                        </Badge>
                      ))}
                      {(!repoResult.data.topics || repoResult.data.topics.length === 0) && (
                        <span className="text-[10px] text-muted-foreground/40">No topics</span>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatPushTime(repoResult.data.pushed_at)}
                    </span>
                  </div>
                </>
              ) : null}
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}

function RepositoryOverviewSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {[1, 2].map((i) => (
        <Card key={i} className="border-border/50">
          <CardContent className="p-4 space-y-3">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
            <div className="flex gap-4">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// ── Section 2: Active Pull Requests ────────────────────────────────

function ActivePullRequests({ pulls }: { pulls: PullData[] }) {
  if (pulls.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <GitPullRequest className="h-8 w-8 mb-2 opacity-30" />
        <span className="text-xs">No open pull requests</span>
      </div>
    )
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
      {pulls.map((pr) => (
        <motion.div
          key={`${pr.repo}-${pr.number}`}
          variants={staggerItem}
          initial="hidden"
          animate="visible"
          className="group flex items-center gap-3 rounded-lg border border-border/50 bg-card/50 px-3 py-2.5 transition-all duration-200 hover:border-emerald-600/30 hover:bg-accent/30"
        >
          {/* PR Icon */}
          <div className="shrink-0">
            <GitPullRequest className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>

          {/* Repo Badge */}
          {getRepoBadge(pr.repo)}

          {/* PR Title */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-foreground shrink-0">
                #{pr.number}
              </span>
              <span className="text-xs text-muted-foreground truncate">
                {truncateMessage(pr.title, 48)}
              </span>
            </div>
          </div>

          {/* Author */}
          <span className="hidden sm:block text-[10px] text-muted-foreground shrink-0 truncate max-w-[100px]">
            {pr.user}
          </span>

          {/* Branch */}
          <div className="hidden md:flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
            <span className="font-mono truncate max-w-[100px]">{pr.head_ref}</span>
            <span className="text-muted-foreground/50">→</span>
            <span className="font-mono">{pr.base_ref}</span>
          </div>

          {/* File changes */}
          <span className="hidden lg:block text-[10px] text-muted-foreground shrink-0 tabular-nums">
            {pr.changed_files} file{pr.changed_files !== 1 ? 's' : ''}
          </span>

          {/* Additions/Deletions */}
          <div className="hidden sm:flex items-center gap-1.5 shrink-0 text-[10px] font-mono tabular-nums">
            <span className="text-emerald-600 dark:text-emerald-400">+{pr.additions}</span>
            <span className="text-red-600 dark:text-red-400">-{pr.deletions}</span>
          </div>

          {/* Mergeable Status */}
          {getMergeableBadge(pr.mergeable_state)}
        </motion.div>
      ))}
    </div>
  )
}

function PullRequestsSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-16 w-full rounded-lg" />
      ))}
    </div>
  )
}

// ── Section 3: Recent Commits Timeline ─────────────────────────────

function RecentCommitsTimeline({ commits }: { commits: CommitData[] }) {
  if (commits.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <GitCommit className="h-8 w-8 mb-2 opacity-30" />
        <span className="text-xs">No recent commits</span>
      </div>
    )
  }

  return (
    <div className="relative max-h-96 overflow-y-auto custom-scrollbar">
      {/* Timeline line */}
      <div className="absolute left-[15px] top-2 bottom-2 w-px bg-gradient-to-b from-emerald-600/40 via-border/30 to-transparent" />

      <div className="space-y-1">
        {commits.map((commit, idx) => (
          <motion.div
            key={`${commit.repo}-${commit.sha}-${idx}`}
            variants={staggerItem}
            initial="hidden"
            animate="visible"
            className="group relative flex items-start gap-3 pl-2"
          >
            {/* Timeline node */}
            <div className="relative z-10 mt-1.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-emerald-600/40 bg-card">
              <GitCommit className="h-2.5 w-2.5 text-emerald-600 dark:text-emerald-400" />
            </div>

            {/* Commit content */}
            <div className="flex-1 min-w-0 rounded-lg border border-transparent px-2.5 py-1.5 transition-colors group-hover:border-border/50 group-hover:bg-accent/20">
              <div className="flex items-center gap-2 flex-wrap">
                {/* Repo badge */}
                {getRepoBadge(commit.repo)}

                {/* Short SHA */}
                <code className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-600/10 px-1.5 py-0.5 rounded">
                  {commit.sha}
                </code>

                {/* Commit message */}
                <span className="text-xs text-foreground truncate max-w-[280px]">
                  {truncateMessage(commit.message, 55)}
                </span>
              </div>

              <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
                <span className="truncate max-w-[120px]">{commit.author}</span>
                <span className="flex items-center gap-1">
                  <Clock className="h-2.5 w-2.5" />
                  {formatRelativeTime(commit.date)}
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function CommitsSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4, 5].map((i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

// ── Section 4: Branches Overview ───────────────────────────────────

function BranchesOverview({ branches }: { branches: BranchData[] }) {
  // Group by repo
  const grouped = branches.reduce<Record<string, BranchData[]>>((acc, b) => {
    const key = b.repo.includes('nexusalpha') ? 'alpha' : 'dashboards'
    if (!acc[key]) acc[key] = []
    acc[key].push(b)
    return acc
  }, {})

  if (Object.keys(grouped).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <GitBranch className="h-8 w-8 mb-2 opacity-30" />
        <span className="text-xs">No branches found</span>
      </div>
    )
  }

  return (
    <div className="space-y-4 max-h-96 overflow-y-auto custom-scrollbar">
      {Object.entries(grouped).map(([repoKey, repoBranches]) => (
        <motion.div key={repoKey} variants={staggerItem} initial="hidden" animate="visible">
          <div className="mb-2 flex items-center gap-2">
            {getRepoKeyBadge(repoKey)}
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {repoBranches.length} branch{repoBranches.length !== 1 ? 'es' : ''}
            </span>
          </div>

          <div className="space-y-1">
            {repoBranches.map((branch) => {
              const prefixBadge = getBranchPrefixBadge(branch.name)
              const isDefault = branch.name === 'main' || branch.name === 'master'
              return (
                <div
                  key={`${branch.repo}-${branch.name}`}
                  className="group flex items-center gap-2.5 rounded-md border border-transparent px-2.5 py-1.5 transition-all duration-200 hover:border-border/50 hover:bg-accent/20"
                >
                  {/* Branch icon */}
                  <GitBranch className={`h-3.5 w-3.5 shrink-0 ${
                    isDefault
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-muted-foreground'
                  }`} />

                  {/* Branch name */}
                  <span className="text-xs font-mono truncate max-w-[200px] text-foreground">
                    {branch.name}
                  </span>

                  {/* Prefix badge */}
                  {prefixBadge}

                  {/* Default branch indicator */}
                  {isDefault && (
                    <ShieldCheck className="h-3 w-3 text-amber-600 dark:text-amber-400 shrink-0" />
                  )}

                  {/* Spacer */}
                  <span className="flex-1" />
                </div>
              )
            })}
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function BranchesSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2].map((i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-full" />
          <Skeleton className="h-6 w-3/4" />
        </div>
      ))}
    </div>
  )
}

// ── Error / Retry Component ────────────────────────────────────────

function ErrorWithRetry({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
      <AlertCircle className="h-8 w-8 mb-2 text-red-500" />
      <span className="text-xs mb-3 text-center max-w-sm">{message}</span>
      <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5 text-xs">
        <RefreshCw className="h-3 w-3" />
        Retry
      </Button>
    </div>
  )
}

// ── Config warning banner ──────────────────────────────────────────

function ConfigWarning() {
  return (
    <Card className="relative overflow-hidden border-amber-600/30 shadow-lg">
      <div className="absolute inset-0 bg-gradient-to-br from-amber-600/5 via-transparent to-transparent" />
      <CardContent className="relative p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-amber-600 dark:text-amber-400">GitHub Token Not Configured</h3>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              The <code className="text-[10px] font-mono bg-muted px-1 py-0.5 rounded">GITHUB_TOKEN</code> environment variable is not set.
              GitHub integration requires a personal access token to fetch repository data, pull requests, commits, and branches.
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              Set the token in your <code className="text-[10px] font-mono bg-muted px-1 py-0.5 rounded">.env</code> file and restart the server.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Main GithubTab Component ───────────────────────────────────────

export function GithubTab() {
  const [repos, setRepos] = useState<RepoResult[]>([])
  const [pulls, setPulls] = useState<PullData[]>([])
  const [commits, setCommits] = useState<CommitData[]>([])
  const [branches, setBranches] = useState<BranchData[]>([])

  const [reposLoading, setReposLoading] = useState(true)
  const [pullsLoading, setPullsLoading] = useState(true)
  const [commitsLoading, setCommitsLoading] = useState(true)
  const [branchesLoading, setBranchesLoading] = useState(true)

  const [reposError, setReposError] = useState<string | null>(null)
  const [pullsError, setPullsError] = useState<string | null>(null)
  const [commitsError, setCommitsError] = useState<string | null>(null)
  const [branchesError, setBranchesError] = useState<string | null>(null)

  const [tokenConfigured, setTokenConfigured] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  // Fetch functions
  const fetchRepos = useCallback(async () => {
    setReposLoading(true)
    setReposError(null)
    try {
      const res = await fetch('/api/github/repos')
      if (res.status === 500) {
        const data = await res.json().catch(() => ({ error: 'Server error' }))
        if (data.error?.includes('GITHUB_TOKEN')) {
          setTokenConfigured(false)
          setReposError('GITHUB_TOKEN not configured')
        } else {
          setReposError(data.error || 'Server error')
        }
        return
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setRepos(data.repos || [])
      setTokenConfigured(true)
    } catch (e) {
      setReposError(e instanceof Error ? e.message : 'Failed to fetch repositories')
    } finally {
      setReposLoading(false)
    }
  }, [])

  const fetchPulls = useCallback(async () => {
    setPullsLoading(true)
    setPullsError(null)
    try {
      const res = await fetch('/api/github/pulls?repo=all')
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        setPullsError(data.error || `HTTP ${res.status}`)
        return
      }
      const data = await res.json()
      // Flatten grouped pulls into a single array
      const allPulls: PullData[] = []
      if (data.pulls) {
        Object.values(data.pulls).forEach((repoPulls) => {
          if (Array.isArray(repoPulls)) {
            allPulls.push(...(repoPulls as PullData[]))
          }
        })
      }
      // Sort by updated_at descending
      allPulls.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      setPulls(allPulls)
    } catch (e) {
      setPullsError(e instanceof Error ? e.message : 'Failed to fetch pull requests')
    } finally {
      setPullsLoading(false)
    }
  }, [])

  const fetchCommits = useCallback(async () => {
    setCommitsLoading(true)
    setCommitsError(null)
    try {
      const res = await fetch('/api/github/commits?repo=all')
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        setCommitsError(data.error || `HTTP ${res.status}`)
        return
      }
      const data = await res.json()
      // Flatten grouped commits into a single array
      const allCommits: CommitData[] = []
      if (data.commits) {
        Object.values(data.commits).forEach((repoCommits) => {
          if (Array.isArray(repoCommits)) {
            allCommits.push(...(repoCommits as CommitData[]))
          }
        })
      }
      // Sort by date descending
      allCommits.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      setCommits(allCommits)
    } catch (e) {
      setCommitsError(e instanceof Error ? e.message : 'Failed to fetch commits')
    } finally {
      setCommitsLoading(false)
    }
  }, [])

  const fetchBranches = useCallback(async () => {
    setBranchesLoading(true)
    setBranchesError(null)
    try {
      const res = await fetch('/api/github/branches')
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        setBranchesError(data.error || `HTTP ${res.status}`)
        return
      }
      const data = await res.json()
      // Flatten grouped branches into a single array
      const allBranches: BranchData[] = []
      if (data.branches) {
        Object.values(data.branches).forEach((repoBranches) => {
          if (Array.isArray(repoBranches)) {
            allBranches.push(...(repoBranches as BranchData[]))
          }
        })
      }
      setBranches(allBranches)
    } catch (e) {
      setBranchesError(e instanceof Error ? e.message : 'Failed to fetch branches')
    } finally {
      setBranchesLoading(false)
    }
  }, [])

  const fetchAll = useCallback(async () => {
    await Promise.all([fetchRepos(), fetchPulls(), fetchCommits(), fetchBranches()])
    setLastRefresh(new Date())
  }, [fetchRepos, fetchPulls, fetchCommits, fetchBranches])

  // Initial fetch + auto-refresh every 60s
  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 60000)
    return () => clearInterval(interval)
  }, [fetchAll])

  // Manual refresh handler
  const handleRefresh = useCallback(() => {
    toast.success('Refreshing GitHub data...', { duration: 1500 })
    fetchAll()
  }, [fetchAll])

  // Stat summary
  const openPrCount = pulls.length
  const mergeableCount = pulls.filter((p) => p.mergeable_state === 'mergeable').length
  const conflictingCount = pulls.filter((p) => p.mergeable_state === 'conflicting').length
  const featureBranchCount = branches.filter((b) => b.name.startsWith('gt/') || b.name.startsWith('convoy/') || b.name.startsWith('feature/')).length
  const defaultBranchCount = branches.filter((b) => b.name === 'main' || b.name === 'master').length

  // Show config warning if token not set
  if (!tokenConfigured) {
    return (
      <div className="grid-pattern p-4 md:p-6 space-y-6">
        <motion.div variants={staggerItem} initial="hidden" animate="visible">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            <h2 className="text-lg font-bold text-foreground">GitHub Integration</h2>
          </div>
        </motion.div>
        <ConfigWarning />
      </div>
    )
  }

  return (
    <div className="grid-pattern p-4 md:p-6 space-y-6">
      {/* Header */}
      <motion.div variants={staggerItem} initial="hidden" animate="visible">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <GitBranch className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              GitHub Integration
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Repository status, pull requests, commits, and branches across NEXUS OS projects
            </p>
          </div>

          <div className="flex items-center gap-2">
            <DataSourceBadge source="api" />
            <span className="text-[10px] text-muted-foreground tabular-nums">
              Updated {formatRelativeTime(lastRefresh.toISOString())}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className="gap-1.5 text-xs h-7"
            >
              <RefreshCw className="h-3 w-3" />
              Refresh
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Stat Cards Row */}
      <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-emerald-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-600/10 via-emerald-600/5 to-transparent" />
            <CardContent className="relative p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Repositories</p>
                  <p className="text-xl font-bold text-emerald-600 dark:text-emerald-400 tabular-nums">
                    {reposLoading ? '—' : repos.filter((r) => r.success).length}
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600/15">
                  <Eye className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-blue-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-blue-600/5 to-transparent" />
            <CardContent className="relative p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Open PRs</p>
                  <p className="text-xl font-bold text-blue-600 dark:text-blue-400 tabular-nums">
                    {pullsLoading ? '—' : openPrCount}
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600/15">
                  <GitPullRequest className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-purple-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-purple-600/5 to-transparent" />
            <CardContent className="relative p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Mergeable</p>
                  <p className="text-xl font-bold text-purple-600 dark:text-purple-400 tabular-nums">
                    {pullsLoading ? '—' : (
                      <>
                        {mergeableCount}
                        {conflictingCount > 0 && (
                          <span className="text-xs text-red-500 ml-1">({conflictingCount} conflict{conflictingCount > 1 ? 's' : ''})</span>
                        )}
                      </>
                    )}
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-600/15">
                  <GitMerge className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-amber-600/20 hover-lift">
            <div className="absolute inset-0 bg-gradient-to-br from-amber-600/10 via-amber-600/5 to-transparent" />
            <CardContent className="relative p-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Branches</p>
                  <p className="text-xl font-bold text-amber-600 dark:text-amber-400 tabular-nums">
                    {branchesLoading ? '—' : branches.length}
                    {!branchesLoading && featureBranchCount > 0 && (
                      <span className="text-xs text-muted-foreground ml-1">({featureBranchCount} active)</span>
                    )}
                  </p>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-600/15">
                  <GitBranch className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Section 1: Repository Overview */}
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-border/50 shadow-lg">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Eye className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  Repository Overview
                  <DataSourceBadge source="api" />
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              {reposError ? (
                <ErrorWithRetry message={reposError} onRetry={fetchRepos} />
              ) : reposLoading ? (
                <RepositoryOverviewSkeleton />
              ) : (
                <RepositoryOverview repos={repos} />
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Section 2: Active Pull Requests */}
      <motion.div variants={staggerContainer} initial="hidden" animate="visible">
        <motion.div variants={staggerItem}>
          <Card className="relative overflow-hidden border-border/50 shadow-lg">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <GitPullRequest className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  Active Pull Requests
                  <Badge variant="outline" className="text-[9px] ml-1">
                    {pulls.length} open
                  </Badge>
                  <DataSourceBadge source="api" />
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              {pullsError ? (
                <ErrorWithRetry message={pullsError} onRetry={fetchPulls} />
              ) : pullsLoading ? (
                <PullRequestsSkeleton />
              ) : (
                <ActivePullRequests pulls={pulls} />
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Section 3 & 4: Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Section 3: Recent Commits Timeline */}
        <motion.div variants={staggerContainer} initial="hidden" animate="visible">
          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-border/50 shadow-lg">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <GitCommit className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                    Recent Commits
                    <Badge variant="outline" className="text-[9px] ml-1">
                      {commits.length} commits
                    </Badge>
                    <DataSourceBadge source="api" />
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {commitsError ? (
                  <ErrorWithRetry message={commitsError} onRetry={fetchCommits} />
                ) : commitsLoading ? (
                  <CommitsSkeleton />
                ) : (
                  <RecentCommitsTimeline commits={commits} />
                )}
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>

        {/* Section 4: Branches Overview */}
        <motion.div variants={staggerContainer} initial="hidden" animate="visible">
          <motion.div variants={staggerItem}>
            <Card className="relative overflow-hidden border-border/50 shadow-lg">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    Branches Overview
                    <Badge variant="outline" className="text-[9px] ml-1">
                      {branches.length} total
                    </Badge>
                    <DataSourceBadge source="api" />
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                {branchesError ? (
                  <ErrorWithRetry message={branchesError} onRetry={fetchBranches} />
                ) : branchesLoading ? (
                  <BranchesSkeleton />
                ) : (
                  <BranchesOverview branches={branches} />
                )}
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}
