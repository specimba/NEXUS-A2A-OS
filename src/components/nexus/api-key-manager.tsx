'use client'

/**
 * API Key Manager Component for NEXUS OS
 *
 * Inline key entry for each provider with:
 * - Encrypted storage indicator (🔒 AES-256-GCM)
 * - Key validation (min 8 chars)
 * - Masked display of existing keys
 * - Delete key with confirmation
 * - Immediate provider activation after save
 * - Link to get free API keys
 */

import { useState, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Key,
  Lock,
  Eye,
  EyeOff,
  Save,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Shield,
  AlertTriangle,
} from 'lucide-react'
import { toast } from 'sonner'

// ── Provider signup URLs ────────────────────────────────────────────

const PROVIDER_KEY_INFO: Record<string, {
  envVar: string
  signupUrl?: string
  freeTier?: string
  keyFormat?: string
}> = {
  openrouter: {
    envVar: 'OPENROUTER_API_KEY',
    signupUrl: 'https://openrouter.ai/keys',
    freeTier: 'Free models, 50 req/day',
    keyFormat: 'sk-or-v1-...',
  },
  groq: {
    envVar: 'GROQ_API_KEY',
    signupUrl: 'https://console.groq.com/keys',
    freeTier: 'Free tier, 30 RPM',
    keyFormat: 'gsk_...',
  },
  cerebras: {
    envVar: 'CEREBRAS_API_KEY',
    signupUrl: 'https://cloud.cerebras.ai/',
    freeTier: 'Free tier, 30 RPM',
    keyFormat: 'csk-...',
  },
  mistral: {
    envVar: 'MISTRAL_API_KEY',
    signupUrl: 'https://console.mistral.ai/',
    freeTier: 'Free tier, 2 RPM',
    keyFormat: '...',
  },
  codestral: {
    envVar: 'CODESTRAL_API_KEY',
    signupUrl: 'https://console.mistral.ai/',
    freeTier: 'Free tier, 30 RPM',
    keyFormat: '...',
  },
  fireworks: {
    envVar: 'FIREWORKS_API_KEY',
    signupUrl: 'https://app.fireworks.ai/',
    freeTier: '$1 free credits',
    keyFormat: '...',
  },
  scaleway: {
    envVar: 'SCALEWAY_ACCESS_KEY',
    signupUrl: 'https://console.scaleway.com/',
    freeTier: '1M free tokens',
    keyFormat: 'SCW...',
  },
  dashscope: {
    envVar: 'DASHSCOPE_API_KEY',
    signupUrl: 'https://dashscope.console.aliyun.com/',
    freeTier: '1M free tokens/model',
    keyFormat: 'sk-...',
  },
  bitdeer: {
    envVar: 'BITDEER_ACCESS_KEY',
    signupUrl: 'https://www.bitdeer.ai/',
    freeTier: 'Free tier available',
    keyFormat: '...',
  },
  openai: {
    envVar: 'OPENAI_API_KEY',
    signupUrl: 'https://platform.openai.com/api-keys',
    freeTier: 'Pay-as-you-go',
    keyFormat: 'sk-proj-...',
  },
  'z-ai': {
    envVar: 'ZAI_API_KEY',
    keyFormat: 'sk-...',
  },
}

// ── Types ──────────────────────────────────────────────────────────

interface SavedKey {
  id: string
  provider: string
  masked: string
  isActive: boolean
  health: string
  lastError: string | null
  totalRequests: number
  total429s: number
  successRate: number
  lastUsed: string | null
  createdAt: string
}

interface ApiKeyEntryProps {
  provider: string
  label: string
  hasKey: boolean
  maskedKey: string | null
  onKeySaved: () => void
}

// ── Single Provider Key Entry ──────────────────────────────────────

export function ApiKeyEntry({ provider, label, hasKey, maskedKey, onKeySaved }: ApiKeyEntryProps) {
  const [keyInput, setKeyInput] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const keyInfo = PROVIDER_KEY_INFO[provider]

  const handleSave = useCallback(async () => {
    if (!keyInput.trim() || keyInput.trim().length < 8) {
      toast.error('API key must be at least 8 characters')
      return
    }

    setSaving(true)
    try {
      const res = await globalThis.fetch('/api/providers/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, apiKey: keyInput.trim() }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        toast.error(data.error || 'Failed to save key')
        return
      }

      const data = await res.json()
      if (data.success) {
        toast.success(`${label} API key saved 🔒`, {
          description: `Key: ${data.key.masked}${data.envPersisted ? ` • Saved to .env (${data.envVar})` : ' • In-memory only'}`,
        })
        setKeyInput('')
        setShowKey(false)
        onKeySaved()
      } else {
        toast.error(data.error || 'Failed to save key')
      }
    } catch (err) {
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setSaving(false)
    }
  }, [keyInput, provider, label, onKeySaved])

  const handleDelete = useCallback(async () => {
    setDeleting(true)
    try {
      const res = await globalThis.fetch('/api/providers/keys', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        toast.error(data.error || 'Failed to delete key')
        return
      }

      toast.success(`${label} API key removed`)
      setShowDeleteConfirm(false)
      onKeySaved()
    } catch (err) {
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setDeleting(false)
    }
  }, [provider, label, onKeySaved])

  return (
    <>
      <div className="space-y-2">
        {/* Encryption notice */}
        <div className="flex items-center gap-1.5 text-[9px] text-muted-foreground">
          <Lock className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span>AES-256-GCM encrypted at rest • Keys never sent to client</span>
        </div>

        {/* Current key status */}
        {hasKey ? (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-emerald-600/10 border border-emerald-600/20 flex-1">
              <Shield className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span className="text-xs font-mono text-emerald-700 dark:text-emerald-300">
                {maskedKey || '•••••••'}
              </span>
              <Badge className="border-0 text-[8px] ml-auto bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 shrink-0">
                ACTIVE
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-red-500 hover:text-red-600 hover:bg-red-600/10"
              onClick={() => setShowDeleteConfirm(true)}
              title="Delete key"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-amber-600/10 border border-amber-600/20">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span className="text-xs text-amber-700 dark:text-amber-300">No API key configured</span>
            {keyInfo?.envVar && (
              <span className="text-[9px] text-amber-600/70 dark:text-amber-400/70 ml-1">
                ({keyInfo.envVar})
              </span>
            )}
          </div>
        )}

        {/* Key input */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Input
              type={showKey ? 'text' : 'password'}
              placeholder={keyInfo?.keyFormat || 'Paste your API key here...'}
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              className="pr-9 h-8 text-xs font-mono bg-background/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && keyInput.trim().length >= 8) {
                  handleSave()
                }
              }}
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          <Button
            size="sm"
            className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white shrink-0"
            disabled={saving || keyInput.trim().length < 8}
            onClick={handleSave}
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <>
                <Save className="h-3.5 w-3.5 mr-1" />
                Save
              </>
            )}
          </Button>
        </div>

        {/* Free key link */}
        {keyInfo?.signupUrl && !hasKey && (
          <a
            href={keyInfo.signupUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            {keyInfo.freeTier || 'Get Free Key'} →
          </a>
        )}
      </div>

      {/* Delete confirmation dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <Trash2 className="h-4 w-4" />
              Delete API Key
            </DialogTitle>
            <DialogDescription>
              Remove the API key for {label}? This provider will stop working until a new key is added.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
              ) : (
                <Trash2 className="h-3.5 w-3.5 mr-1" />
              )}
              Delete Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ── Full Key Management Panel ──────────────────────────────────────

interface ApiKeyManagerPanelProps {
  providers: Array<{
    provider: string
    label: string
    hasKey: boolean
    maskedKey: string | null
  }>
  onKeysChanged: () => void
}

export function ApiKeyManagerPanel({ providers, onKeysChanged }: ApiKeyManagerPanelProps) {
  const providersWithKeys = providers.filter(p => p.hasKey)
  const providersWithoutKeys = providers.filter(p => !p.hasKey)

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Key className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          <span className="text-sm font-semibold">API Key Vault</span>
          <Badge className="border-0 text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
            {providersWithKeys.length}/{providers.length} configured
          </Badge>
        </div>
        <div className="flex items-center gap-1.5 text-[9px] text-muted-foreground">
          <Lock className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          AES-256-GCM
        </div>
      </div>

      {/* Providers with keys */}
      {providersWithKeys.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-medium">
            ✅ Configured ({providersWithKeys.length})
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {providersWithKeys.map(p => (
              <Card key={p.provider} className="p-3 border-emerald-600/15 bg-emerald-600/[0.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium">{p.label}</span>
                  <div className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-[9px] font-mono text-emerald-600 dark:text-emerald-400">{p.maskedKey}</span>
                  </div>
                </div>
                <ApiKeyEntry
                  provider={p.provider}
                  label={p.label}
                  hasKey={p.hasKey}
                  maskedKey={p.maskedKey}
                  onKeySaved={onKeysChanged}
                />
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Providers without keys */}
      {providersWithoutKeys.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-amber-600 dark:text-amber-400 font-medium">
            ⏳ Needs API Key ({providersWithoutKeys.length})
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {providersWithoutKeys.map(p => (
              <Card key={p.provider} className="p-3 border-amber-600/15 bg-amber-600/[0.02]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium">{p.label}</span>
                  <Badge className="border-0 text-[8px] bg-amber-600/15 text-amber-600 dark:text-amber-400">
                    NO KEY
                  </Badge>
                </div>
                <ApiKeyEntry
                  provider={p.provider}
                  label={p.label}
                  hasKey={p.hasKey}
                  maskedKey={p.maskedKey}
                  onKeySaved={onKeysChanged}
                />
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
