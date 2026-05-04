'use client'

import { useState, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Key,
  Eye,
  EyeOff,
  Shield,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  TestTube2,
} from 'lucide-react'
import { toast } from 'sonner'

// ── Types ─────────────────────────────────────────────────────────

interface KeyInfo {
  id: string
  provider: string
  keyPrefix: string
  keySuffix: string
  masked: string
  isActive: boolean
  health: string
  totalRequests: number
  total429s: number
  successRate: number
  lastError: string | null
  createdAt: string
  updatedAt: string
}

interface ApiKeyEntryProps {
  provider: string
  providerLabel: string
  providerIcon: string
  hasAvailableKey: boolean
  activeKeyMasked: string | null
  healthyKeys: number
  totalKeys: number
  open: boolean
  onClose: () => void
  onKeySaved: () => void
}

// ── Component ─────────────────────────────────────────────────────

export function ApiKeyEntry({
  provider,
  providerLabel,
  providerIcon,
  hasAvailableKey,
  activeKeyMasked,
  healthyKeys,
  totalKeys,
  open,
  onClose,
  onKeySaved,
}: ApiKeyEntryProps) {
  const [keyValue, setKeyValue] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    latencyMs?: number
  } | null>(null)
  const [savedKeyId, setSavedKeyId] = useState<string | null>(null)
  const [savedMasked, setSavedMasked] = useState<string | null>(null)
  const [existingKeys, setExistingKeys] = useState<KeyInfo[]>([])
  const [loadedKeys, setLoadedKeys] = useState(false)

  // Load existing keys for this provider when dialog opens
  const loadExistingKeys = useCallback(async () => {
    if (loadedKeys) return
    try {
      const res = await globalThis.fetch('/api/keys')
      if (res.ok) {
        const data = await res.json()
        const providerKeys = (data.keys || []).filter(
          (k: KeyInfo) => k.provider === provider
        )
        setExistingKeys(providerKeys)
        setLoadedKeys(true)
      }
    } catch {
      // Non-critical — just don't show existing keys
    }
  }, [provider, loadedKeys])

  // Reset state when dialog opens
  const handleOpenChange = useCallback(
    (isOpen: boolean) => {
      if (isOpen) {
        setKeyValue('')
        setShowKey(false)
        setSaving(false)
        setTesting(false)
        setDeleting(false)
        setTestResult(null)
        setSavedKeyId(null)
        setSavedMasked(null)
        setLoadedKeys(false)
        loadExistingKeys()
      } else {
        onClose()
      }
    },
    [onClose, loadExistingKeys]
  )

  const handleSave = useCallback(async () => {
    if (!keyValue.trim()) {
      toast.error('Please enter an API key')
      return
    }
    if (keyValue.trim().length < 8) {
      toast.error('API key must be at least 8 characters')
      return
    }

    setSaving(true)
    setTestResult(null)
    try {
      const res = await globalThis.fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          keyValue: keyValue.trim(),
        }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        toast.error(`Failed to save key: ${errData.error || 'Unknown error'}`)
        return
      }

      const data = await res.json()
      setSavedKeyId(data.key?.id ?? null)
      setSavedMasked(data.key?.masked ?? null)
      setKeyValue('')
      setShowKey(false)

      toast.success(`API key saved for ${providerLabel}`, {
        description: `Key: ${data.key?.masked || '***'}`,
      })

      // Reload existing keys
      setLoadedKeys(false)
      await loadExistingKeys()

      // Notify parent to refetch
      onKeySaved()
    } catch (err) {
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setSaving(false)
    }
  }, [keyValue, provider, providerLabel, onKeySaved, loadExistingKeys])

  const handleTest = useCallback(async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await globalThis.fetch('/api/providers/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
        setTestResult({
          success: false,
          message: errData.error || 'Test request failed',
        })
        toast.error(`Key test failed: ${errData.error || 'Unknown error'}`)
        return
      }

      const data = await res.json()
      if (data.results && data.results.length > 0) {
        const result = data.results[0]
        setTestResult({
          success: result.success,
          message: result.success
            ? `Test passed — ${result.latencyMs}ms, ${result.tokenCount} tokens`
            : result.error || 'Test failed',
          latencyMs: result.latencyMs,
        })
        if (result.success) {
          toast.success(`${providerLabel} key is working — ${result.latencyMs}ms`)
        } else {
          toast.error(`${providerLabel} key test failed — ${result.error || 'Unknown'}`)
        }
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: `Network error: ${err instanceof Error ? err.message : 'Unknown'}`,
      })
      toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
    } finally {
      setTesting(false)
    }
  }, [provider, providerLabel])

  const handleDelete = useCallback(
    async (keyId: string) => {
      setDeleting(true)
      try {
        const res = await globalThis.fetch(`/api/keys?id=${keyId}`, {
          method: 'DELETE',
        })

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }))
          toast.error(`Failed to delete key: ${errData.error || 'Unknown error'}`)
          return
        }

        toast.success('API key deleted', {
          description: 'The key has been removed from the vault',
        })

        // Reload existing keys
        setLoadedKeys(false)
        await loadExistingKeys()

        // Notify parent to refetch
        onKeySaved()
      } catch (err) {
        toast.error(`Network error: ${err instanceof Error ? err.message : 'Unknown'}`)
      } finally {
        setDeleting(false)
      }
    },
    [onKeySaved, loadExistingKeys]
  )

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            Key Vault — {providerIcon} {providerLabel}
          </DialogTitle>
          <DialogDescription>
            Add, update, or remove API keys for {providerLabel}. Keys are encrypted with
            AES-256-GCM before storage.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Current Key Status */}
          <div className="rounded-lg border border-border/50 bg-accent/30 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Current Status
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="text-center">
                <p className="text-[9px] text-muted-foreground uppercase">Key Status</p>
                <div className="mt-1">
                  {hasAvailableKey ? (
                    <Badge className="border-0 text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="h-2.5 w-2.5 mr-0.5" />
                      ACTIVE
                    </Badge>
                  ) : (
                    <Badge className="border-0 text-[9px] bg-red-600/15 text-red-600 dark:text-red-400">
                      <XCircle className="h-2.5 w-2.5 mr-0.5" />
                      NO KEY
                    </Badge>
                  )}
                </div>
              </div>
              <div className="text-center">
                <p className="text-[9px] text-muted-foreground uppercase">Masked Key</p>
                <p className="text-xs font-mono font-medium mt-1">
                  {activeKeyMasked ? (
                    <span className="flex items-center justify-center gap-1">
                      <Lock className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                      {activeKeyMasked}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">---</span>
                  )}
                </p>
              </div>
              <div className="text-center">
                <p className="text-[9px] text-muted-foreground uppercase">Health</p>
                <p className="text-xs font-bold tabular-nums mt-1">
                  <span className={healthyKeys > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}>
                    {healthyKeys}/{totalKeys}
                  </span>
                </p>
              </div>
            </div>
          </div>

          {/* Existing Keys List */}
          {existingKeys.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Stored Keys
              </p>
              <div className="space-y-1.5 max-h-32 overflow-y-auto custom-scrollbar">
                {existingKeys.map((k) => (
                  <div
                    key={k.id}
                    className="flex items-center gap-2 rounded-md border border-border/30 bg-accent/20 px-3 py-2"
                  >
                    <Lock className="h-3 w-3 text-muted-foreground shrink-0" />
                    <span className="text-xs font-mono flex-1 truncate">{k.masked}</span>
                    <Badge
                      className={`border-0 text-[8px] px-1 py-0 ${
                        k.health === 'healthy'
                          ? 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400'
                          : k.health === 'rate_limited'
                          ? 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400'
                          : 'bg-red-600/15 text-red-600 dark:text-red-400'
                      }`}
                    >
                      {k.health}
                    </Badge>
                    <span className="text-[9px] text-muted-foreground tabular-nums">
                      {k.successRate.toFixed(0)}%
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 text-red-500 hover:text-red-600 hover:bg-red-600/10"
                      disabled={deleting}
                      onClick={() => handleDelete(k.id)}
                      title="Delete key"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Save Success Indicator */}
          {savedMasked && (
            <div className="flex items-center gap-2 rounded-md border border-emerald-600/20 bg-emerald-600/5 px-3 py-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <div className="flex-1">
                <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                  Key saved successfully
                </p>
                <p className="text-[10px] font-mono text-muted-foreground">{savedMasked}</p>
              </div>
              <Lock className="h-3.5 w-3.5 text-emerald-600/50" />
            </div>
          )}

          {/* Key Input */}
          <div className="space-y-2">
            <Label htmlFor="api-key-input" className="text-xs">
              {hasAvailableKey ? 'Update API Key' : 'Enter API Key'}
            </Label>
            <div className="relative">
              <Input
                id="api-key-input"
                type={showKey ? 'text' : 'password'}
                placeholder={
                  hasAvailableKey
                    ? 'Enter new key to replace existing...'
                    : `Enter your ${providerLabel} API key...`
                }
                value={keyValue}
                onChange={(e) => setKeyValue(e.target.value)}
                className="pr-10 font-mono text-sm"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !saving && keyValue.trim()) {
                    handleSave()
                  }
                }}
                autoComplete="off"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                onClick={() => setShowKey(!showKey)}
                title={showKey ? 'Hide key' : 'Show key'}
              >
                {showKey ? (
                  <EyeOff className="h-3.5 w-3.5" />
                ) : (
                  <Eye className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
            <p className="text-[10px] text-muted-foreground flex items-center gap-1">
              <Lock className="h-2.5 w-2.5" />
              Keys are encrypted with AES-256-GCM before being stored in the database.
              Plaintext keys are never exposed to the client.
            </p>
          </div>

          {/* Save Button */}
          <div className="flex items-center gap-2">
            <Button
              onClick={handleSave}
              disabled={saving || !keyValue.trim()}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Encrypting & Saving...
                </>
              ) : (
                <>
                  <Shield className="h-4 w-4 mr-2" />
                  {hasAvailableKey ? 'Update Key' : 'Save Key'}
                </>
              )}
            </Button>
            {hasAvailableKey && (
              <Button
                variant="outline"
                onClick={handleTest}
                disabled={testing}
                className="gap-1.5 border-emerald-600/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600/10"
              >
                {testing ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <TestTube2 className="h-3.5 w-3.5" />
                )}
                Test
              </Button>
            )}
          </div>

          {/* Test Result */}
          {testResult && (
            <div
              className={`rounded-lg border p-3 space-y-1.5 ${
                testResult.success
                  ? 'border-emerald-600/20 bg-emerald-600/5'
                  : 'border-red-600/20 bg-red-600/5'
              }`}
            >
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                )}
                <span
                  className={`text-sm font-semibold ${
                    testResult.success
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {testResult.success ? 'Key is Working' : 'Key Test Failed'}
                </span>
                {testResult.latencyMs !== undefined && (
                  <Badge className="border-0 text-[9px] bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 ml-auto">
                    {testResult.latencyMs}ms
                  </Badge>
                )}
              </div>
              <p
                className={`text-xs ${
                  testResult.success ? 'text-muted-foreground' : 'text-red-600/80 dark:text-red-400/80'
                }`}
              >
                {testResult.message}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => handleOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
