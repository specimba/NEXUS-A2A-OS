'use client'

import { useState, useCallback, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Settings,
  Key,
  Gauge,
  Sun,
  Moon,
  RefreshCw,
  Bell,
  BellOff,
  Shield,
  Database,
  Trash2,
  Download,
  RotateCcw,
  Eye,
  EyeOff,
  Plus,
  X,
  CheckCircle2,
  AlertTriangle,
  Info,
  Save,
  Monitor,
} from 'lucide-react'
import { useTheme } from 'next-themes'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { motion } from 'framer-motion'
import { staggerContainer, staggerItem } from '@/components/nexus/tab-content'

// ── API Key Provider Definitions ──────────────────────────────────

interface ProviderKeyConfig {
  id: string
  name: string
  color: string
  keyPrefix: string
  rpm: number
  rpd: number
}

const PROVIDER_KEYS: ProviderKeyConfig[] = [
  { id: 'z-ai', name: 'Z-AI', color: 'emerald', keyPrefix: 'zai_', rpm: 60, rpd: 1440 },
  { id: 'openai', name: 'OpenAI', color: 'green', keyPrefix: 'sk-', rpm: 500, rpd: 10000 },
  { id: 'anthropic', name: 'Anthropic', color: 'orange', keyPrefix: 'sk-ant-', rpm: 1000, rpd: 50000 },
  { id: 'google', name: 'Google AI', color: 'blue', keyPrefix: 'AIza', rpm: 300, rpd: 10000 },
  { id: 'cerebras', name: 'Cerebras', color: 'purple', keyPrefix: 'csk-', rpm: 30, rpd: 720 },
  { id: 'openrouter', name: 'OpenRouter', color: 'cyan', keyPrefix: 'sk-or-', rpm: 100, rpd: 2400 },
  { id: 'dashscope', name: 'DashScope', color: 'red', keyPrefix: 'sk-', rpm: 60, rpd: 1440 },
  { id: 'nvidia', name: 'NVIDIA', color: 'green', keyPrefix: 'nvapi-', rpm: 40, rpd: 960 },
  { id: 'sambanova', name: 'SambaNova', color: 'yellow', keyPrefix: 'smb_', rpm: 20, rpd: 480 },
  { id: 'siliconflow', name: 'SiliconFlow', color: 'teal', keyPrefix: 'sk-', rpm: 60, rpd: 1440 },
  { id: 'codestral', name: 'Codestral', color: 'pink', keyPrefix: 'cs_', rpm: 30, rpd: 720 },
  { id: 'bitdeer', name: 'BitDeer', color: 'amber', keyPrefix: 'bd_', rpm: 20, rpd: 480 },
]

// ── Constitutional Rules Defaults ─────────────────────────────────

interface ConstitutionalRules {
  maxAgents: number
  apiCallsLimit: number
  fileWritesLimit: number
  maxConcurrent: number
  healthCheckInterval: number
  fallbackEnabled: boolean
  autoBlockCrit: boolean
  trustDecayRate: number
}

const DEFAULT_CONSTITUTION: ConstitutionalRules = {
  maxAgents: 5,
  apiCallsLimit: 20,
  fileWritesLimit: 30,
  maxConcurrent: 2,
  healthCheckInterval: 30,
  fallbackEnabled: true,
  autoBlockCrit: true,
  trustDecayRate: 0.02,
}

// ── Color helpers ─────────────────────────────────────────────────

function getColorClasses(color: string) {
  const map: Record<string, { border: string; bg: string; text: string; badge: string }> = {
    emerald: { border: 'border-emerald-600/30', bg: 'bg-emerald-600/10', text: 'text-emerald-600 dark:text-emerald-400', badge: 'bg-emerald-600/15 text-emerald-600 dark:text-emerald-400 border-0' },
    green: { border: 'border-green-600/30', bg: 'bg-green-600/10', text: 'text-green-600 dark:text-green-400', badge: 'bg-green-600/15 text-green-600 dark:text-green-400 border-0' },
    orange: { border: 'border-orange-600/30', bg: 'bg-orange-600/10', text: 'text-orange-600 dark:text-orange-400', badge: 'bg-orange-600/15 text-orange-600 dark:text-orange-400 border-0' },
    blue: { border: 'border-blue-600/30', bg: 'bg-blue-600/10', text: 'text-blue-600 dark:text-blue-400', badge: 'bg-blue-600/15 text-blue-600 dark:text-blue-400 border-0' },
    purple: { border: 'border-purple-600/30', bg: 'bg-purple-600/10', text: 'text-purple-600 dark:text-purple-400', badge: 'bg-purple-600/15 text-purple-600 dark:text-purple-400 border-0' },
    cyan: { border: 'border-cyan-600/30', bg: 'bg-cyan-600/10', text: 'text-cyan-600 dark:text-cyan-400', badge: 'bg-cyan-600/15 text-cyan-600 dark:text-cyan-400 border-0' },
    red: { border: 'border-red-600/30', bg: 'bg-red-600/10', text: 'text-red-600 dark:text-red-400', badge: 'bg-red-600/15 text-red-600 dark:text-red-400 border-0' },
    yellow: { border: 'border-yellow-600/30', bg: 'bg-yellow-600/10', text: 'text-yellow-600 dark:text-yellow-400', badge: 'bg-yellow-600/15 text-yellow-600 dark:text-yellow-400 border-0' },
    teal: { border: 'border-teal-600/30', bg: 'bg-teal-600/10', text: 'text-teal-600 dark:text-teal-400', badge: 'bg-teal-600/15 text-teal-600 dark:text-teal-400 border-0' },
    pink: { border: 'border-pink-600/30', bg: 'bg-pink-600/10', text: 'text-pink-600 dark:text-pink-400', badge: 'bg-pink-600/15 text-pink-600 dark:text-pink-400 border-0' },
    amber: { border: 'border-amber-600/30', bg: 'bg-amber-600/10', text: 'text-amber-600 dark:text-amber-400', badge: 'bg-amber-600/15 text-amber-600 dark:text-amber-400 border-0' },
  }
  return map[color] ?? map.emerald
}

function maskKey(key: string): string {
  if (!key || key.length < 8) return key
  return key.slice(0, 4) + '••••••••' + key.slice(-4)
}

// ── Section Header ────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, description, badge }: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  badge?: string
}) {
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600/10">
          <Icon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="text-[10px] text-muted-foreground">{description}</p>
        </div>
      </div>
      {badge && (
        <Badge variant="outline" className="text-[9px]">{badge}</Badge>
      )}
    </div>
  )
}

// ── API Key Row ───────────────────────────────────────────────────

function ApiKeyRow({ provider, savedKeys, onUpdateKey, onRemoveKey }: {
  provider: ProviderKeyConfig
  savedKeys: Record<string, string>
  onUpdateKey: (id: string, key: string) => void
  onRemoveKey: (id: string) => void
}) {
  const [showKey, setShowKey] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const c = getColorClasses(provider.color)
  const hasKey = !!savedKeys[provider.id]
  const currentKey = savedKeys[provider.id] || ''

  const handleSave = useCallback(() => {
    if (inputValue.trim()) {
      onUpdateKey(provider.id, inputValue.trim())
      setEditMode(false)
      setInputValue('')
    }
  }, [inputValue, provider.id, onUpdateKey])

  return (
    <div className={`flex items-center gap-3 rounded-lg border ${c.border} ${c.bg} px-3 py-2.5`}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={`text-xs font-semibold ${c.text}`}>{provider.name}</span>
          {hasKey ? (
            <Badge className={`${c.badge} text-[8px] px-1.5 py-0`}>Configured</Badge>
          ) : (
            <Badge variant="outline" className="text-[8px] px-1.5 py-0 text-muted-foreground">Not Set</Badge>
          )}
        </div>
        {hasKey && !editMode && (
          <span className="text-[10px] font-mono text-muted-foreground">
            {showKey ? currentKey : maskKey(currentKey)}
          </span>
        )}
        {editMode && (
          <div className="flex items-center gap-2 mt-1">
            <Input
              type="password"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={`${provider.keyPrefix}...`}
              className="h-7 text-xs font-mono"
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            />
            <Button size="sm" className="h-7 text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white px-2" onClick={handleSave}>
              <CheckCircle2 className="h-3 w-3 mr-1" /> Save
            </Button>
            <Button size="sm" variant="ghost" className="h-7 text-[10px] px-2" onClick={() => { setEditMode(false); setInputValue('') }}>
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {hasKey && !editMode && (
          <>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setShowKey(!showKey)}
            >
              {showKey ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setEditMode(true)}
            >
              <Settings className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-red-600 hover:text-red-500"
              onClick={() => onRemoveKey(provider.id)}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </>
        )}
        {!hasKey && !editMode && (
          <Button
            variant="outline"
            size="sm"
            className={`h-7 text-[10px] gap-1 ${c.border} ${c.text}`}
            onClick={() => setEditMode(true)}
          >
            <Plus className="h-3 w-3" /> Add Key
          </Button>
        )}
      </div>
    </div>
  )
}

// ── Rate Limit Row ────────────────────────────────────────────────

function RateLimitRow({ provider, savedLimits, onUpdateLimit }: {
  provider: ProviderKeyConfig
  savedLimits: Record<string, { rpm: number; rpd: number }>
  onUpdateLimit: (id: string, field: 'rpm' | 'rpd', value: number) => void
}) {
  const limits = savedLimits[provider.id] ?? { rpm: provider.rpm, rpd: provider.rpd }
  const c = getColorClasses(provider.color)

  return (
    <div className={`flex items-center gap-3 rounded-lg border ${c.border} px-3 py-2.5`}>
      <span className={`text-xs font-semibold ${c.text} w-24 shrink-0`}>{provider.name}</span>
      <div className="flex items-center gap-2 flex-1">
        <div className="flex items-center gap-1.5">
          <Label className="text-[10px] text-muted-foreground shrink-0">RPM</Label>
          <Input
            type="number"
            value={limits.rpm}
            onChange={(e) => onUpdateLimit(provider.id, 'rpm', parseInt(e.target.value) || 0)}
            className="h-7 w-20 text-xs font-mono text-center"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <Label className="text-[10px] text-muted-foreground shrink-0">RPD</Label>
          <Input
            type="number"
            value={limits.rpd}
            onChange={(e) => onUpdateLimit(provider.id, 'rpd', parseInt(e.target.value) || 0)}
            className="h-7 w-20 text-xs font-mono text-center"
          />
        </div>
      </div>
      <Badge variant="outline" className="text-[8px] shrink-0">Default: {provider.rpm}/{provider.rpd}</Badge>
    </div>
  )
}

// ── Notification Type Toggle ──────────────────────────────────────

interface NotificationType {
  id: string
  label: string
  description: string
  defaultEnabled: boolean
}

const NOTIFICATION_TYPES: NotificationType[] = [
  { id: 'agent_errors', label: 'Agent Errors', description: 'Alert when agents enter error state', defaultEnabled: true },
  { id: 'rate_limits', label: 'Rate Limits', description: 'Notify when approaching rate limits', defaultEnabled: true },
  { id: 'trust_changes', label: 'Trust Score Changes', description: 'Alert on significant trust score changes', defaultEnabled: false },
  { id: 'governor_blocks', label: 'Governor Blocks', description: 'Notify when Governor blocks CRITICAL actions', defaultEnabled: true },
  { id: 'budget_warnings', label: 'Budget Warnings', description: 'Alert when token budget exceeds thresholds', defaultEnabled: true },
  { id: 'system_updates', label: 'System Updates', description: 'Notify on system updates and restarts', defaultEnabled: false },
  { id: 'task_completions', label: 'Task Completions', description: 'Notify on task completions and failures', defaultEnabled: false },
]

// ── Main Settings Tab ─────────────────────────────────────────────

export function SettingsTab() {
  const { theme, setTheme } = useTheme()

  // Load saved settings helper — reads from localStorage
  const loadSavedSettings = (): {
    apiKeys?: Record<string, string>
    rateLimits?: Record<string, { rpm: number; rpd: number }>
    autoRefresh?: '15' | '30' | '60' | 'off'
    notificationsEnabled?: boolean
    notificationTypes?: Record<string, boolean>
    constitution?: ConstitutionalRules
    dashboardLayout?: 'compact' | 'comfortable' | 'spacious'
  } | null => {
    try {
      const saved = localStorage.getItem('nexus-settings')
      if (saved) return JSON.parse(saved)
    } catch {
      // Ignore parse errors
    }
    return null
  }

  const [apiKeys, setApiKeys] = useState<Record<string, string>>(() => loadSavedSettings()?.apiKeys ?? {})
  const [rateLimits, setRateLimits] = useState<Record<string, { rpm: number; rpd: number }>>(() => loadSavedSettings()?.rateLimits ?? {})
  const [autoRefresh, setAutoRefresh] = useState<'15' | '30' | '60' | 'off'>(() => loadSavedSettings()?.autoRefresh ?? '30')
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => loadSavedSettings()?.notificationsEnabled ?? true)
  const [notificationTypes, setNotificationTypes] = useState<Record<string, boolean>>(() => {
    const saved = loadSavedSettings()?.notificationTypes
    if (saved) return saved
    const initial: Record<string, boolean> = {}
    NOTIFICATION_TYPES.forEach(t => { initial[t.id] = t.defaultEnabled })
    return initial
  })
  const [constitution, setConstitution] = useState<ConstitutionalRules>(() => loadSavedSettings()?.constitution ?? DEFAULT_CONSTITUTION)
  const [dashboardLayout, setDashboardLayout] = useState<'compact' | 'comfortable' | 'spacious'>(() => loadSavedSettings()?.dashboardLayout ?? 'comfortable')
  const [resetDialogOpen, setResetDialogOpen] = useState(false)

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('nexus-settings', JSON.stringify({
        apiKeys,
        rateLimits,
        autoRefresh,
        notificationsEnabled,
        notificationTypes,
        constitution,
        dashboardLayout,
      }))
    } catch {
      // Ignore storage errors
    }
  }, [apiKeys, rateLimits, autoRefresh, notificationsEnabled, notificationTypes, constitution, dashboardLayout])

  // Handlers
  const handleUpdateKey = useCallback((id: string, key: string) => {
    setApiKeys(prev => ({ ...prev, [id]: key }))
    toast.success('API key updated', { description: `${PROVIDER_KEYS.find(p => p.id === id)?.name} key saved.` })
  }, [])

  const handleRemoveKey = useCallback((id: string) => {
    setApiKeys(prev => {
      const next = { ...prev }
      delete next[id]
      return next
    })
    toast.success('API key removed', { description: `${PROVIDER_KEYS.find(p => p.id === id)?.name} key deleted.` })
  }, [])

  const handleUpdateLimit = useCallback((id: string, field: 'rpm' | 'rpd', value: number) => {
    setRateLimits(prev => ({
      ...prev,
      [id]: {
        ...(prev[id] ?? { rpm: PROVIDER_KEYS.find(p => p.id === id)?.rpm ?? 60, rpd: PROVIDER_KEYS.find(p => p.id === id)?.rpd ?? 1440 }),
        [field]: value,
      },
    }))
  }, [])

  const handleToggleNotification = useCallback((id: string) => {
    setNotificationTypes(prev => ({ ...prev, [id]: !prev[id] }))
  }, [])

  const handleClearCache = useCallback(() => {
    try {
      // Clear API cache entries from localStorage
      const keysToRemove: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && (key.startsWith('api-cache-') || key.startsWith('nexus-data-'))) {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach(k => localStorage.removeItem(k))
      toast.success('Cache cleared', { description: `Removed ${keysToRemove.length} cache entries.` })
    } catch {
      toast.error('Failed to clear cache')
    }
  }, [])

  const handleExportData = useCallback(() => {
    const data = {
      apiKeys: Object.fromEntries(Object.entries(apiKeys).map(([k, v]) => [k, maskKey(v)])),
      rateLimits,
      autoRefresh,
      notificationsEnabled,
      notificationTypes,
      constitution,
      dashboardLayout,
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `nexus-settings-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Settings exported', { description: 'Download started.' })
  }, [apiKeys, rateLimits, autoRefresh, notificationsEnabled, notificationTypes, constitution, dashboardLayout])

  const handleResetDefaults = useCallback(() => {
    setApiKeys({})
    setRateLimits({})
    setAutoRefresh('30')
    setNotificationsEnabled(true)
    const initial: Record<string, boolean> = {}
    NOTIFICATION_TYPES.forEach(t => { initial[t.id] = t.defaultEnabled })
    setNotificationTypes(initial)
    setConstitution(DEFAULT_CONSTITUTION)
    setDashboardLayout('comfortable')
    setResetDialogOpen(false)
    toast.success('Settings reset', { description: 'All settings restored to defaults.' })
  }, [])

  const configuredCount = Object.keys(apiKeys).length
  const totalProviders = PROVIDER_KEYS.length

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-lg shadow-emerald-600/20">
            <Settings className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold">Settings</h2>
            <p className="text-xs text-muted-foreground">Configure NEXUS OS dashboard preferences and system parameters</p>
          </div>
        </div>
        <Badge variant="outline" className="text-[9px] gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          {configuredCount}/{totalProviders} keys
        </Badge>
      </div>

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="space-y-6"
      >
        {/* ── Section 1: API Key Management ─────────────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="border-emerald-600/15">
            <CardHeader className="pb-3">
              <SectionHeader
                icon={Key}
                title="API Key Management"
                description="Manage provider API keys for model routing and authentication"
                badge={`${configuredCount} configured`}
              />
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid gap-2 sm:grid-cols-2">
                {PROVIDER_KEYS.map(provider => (
                  <ApiKeyRow
                    key={provider.id}
                    provider={provider}
                    savedKeys={apiKeys}
                    onUpdateKey={handleUpdateKey}
                    onRemoveKey={handleRemoveKey}
                  />
                ))}
              </div>
              {configuredCount === 0 && (
                <div className="flex items-center gap-2 rounded-lg border border-yellow-600/20 bg-yellow-600/5 p-3 mt-3">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0" />
                  <p className="text-[11px] text-muted-foreground">
                    No API keys configured. Add at least one provider key to enable model routing and AI features.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* ── Section 2: Rate Limit Configuration ───────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="border-blue-600/15">
            <CardHeader className="pb-3">
              <SectionHeader
                icon={Gauge}
                title="Rate Limit Configuration"
                description="Adjust per-provider RPM and RPD limits to match your plan"
                badge="RPM / RPD"
              />
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-2">
                {PROVIDER_KEYS.map(provider => (
                  <RateLimitRow
                    key={provider.id}
                    provider={provider}
                    savedLimits={rateLimits}
                    onUpdateLimit={handleUpdateLimit}
                  />
                ))}
              </div>
              <div className="flex items-center gap-2 mt-3">
                <Info className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                <p className="text-[10px] text-muted-foreground">
                  Changes take effect immediately. Values override provider defaults. Leave at default if unsure.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ── Section 3 & 4: Theme & Auto-Refresh (side-by-side) ── */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Theme Settings */}
          <motion.div variants={staggerItem}>
            <Card className="border-purple-600/15">
              <CardHeader className="pb-3">
                <SectionHeader
                  icon={theme === 'dark' ? Moon : Sun}
                  title="Theme Settings"
                  description="Switch between light and dark mode"
                />
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-3 gap-2">
                  {(['light', 'dark', 'system'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setTheme(t)}
                      className={`flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all duration-200 ${
                        theme === t
                          ? 'border-emerald-600/40 bg-emerald-600/10 shadow-sm shadow-emerald-600/10'
                          : 'border-border/50 bg-card/50 hover:bg-accent/30'
                      }`}
                    >
                      {t === 'light' && <Sun className="h-5 w-5 text-yellow-600" />}
                      {t === 'dark' && <Moon className="h-5 w-5 text-purple-600" />}
                      {t === 'system' && <Monitor className="h-5 w-5 text-muted-foreground" />}
                      <span className="text-[10px] font-medium capitalize">{t}</span>
                      {theme === t && (
                        <span className="h-1 w-1 rounded-full bg-emerald-600" />
                      )}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Dashboard Layout */}
          <motion.div variants={staggerItem}>
            <Card className="border-teal-600/15">
              <CardHeader className="pb-3">
                <SectionHeader
                  icon={Monitor}
                  title="Dashboard Layout"
                  description="Adjust card density and spacing preferences"
                />
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-3 gap-2">
                  {([
                    { value: 'compact' as const, label: 'Compact', desc: 'Tighter spacing', icon: '⊞' },
                    { value: 'comfortable' as const, label: 'Comfortable', desc: 'Default spacing', icon: '⊡' },
                    { value: 'spacious' as const, label: 'Spacious', desc: 'More breathing room', icon: '☐' },
                  ]).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setDashboardLayout(opt.value)}
                      className={`flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all duration-200 ${
                        dashboardLayout === opt.value
                          ? 'border-emerald-600/40 bg-emerald-600/10 shadow-sm shadow-emerald-600/10'
                          : 'border-border/50 bg-card/50 hover:bg-accent/30'
                      }`}
                    >
                      <span className="text-lg">{opt.icon}</span>
                      <span className="text-[10px] font-medium">{opt.label}</span>
                      <span className="text-[8px] text-muted-foreground">{opt.desc}</span>
                      {dashboardLayout === opt.value && (
                        <span className="h-1 w-1 rounded-full bg-emerald-600" />
                      )}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Info className="h-3.5 w-3.5 text-teal-600 dark:text-teal-400 shrink-0" />
                  <p className="text-[10px] text-muted-foreground">
                    Layout preference affects card padding, grid gaps, and font sizes across the dashboard.
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Auto-Refresh & Data Refresh Row */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Auto-Refresh Interval */}
          <motion.div variants={staggerItem}>
            <Card className="border-cyan-600/15">
              <CardHeader className="pb-3">
                <SectionHeader
                  icon={RefreshCw}
                  title="Auto-Refresh Interval"
                  description="How often dashboard data refreshes from the API"
                />
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-4 gap-2">
                  {([
                    { value: '15' as const, label: '15s', desc: 'Fast' },
                    { value: '30' as const, label: '30s', desc: 'Default' },
                    { value: '60' as const, label: '60s', desc: 'Slow' },
                    { value: 'off' as const, label: 'Off', desc: 'Manual' },
                  ]).map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setAutoRefresh(opt.value)}
                      className={`flex flex-col items-center gap-1 rounded-lg border p-3 transition-all duration-200 ${
                        autoRefresh === opt.value
                          ? 'border-emerald-600/40 bg-emerald-600/10 shadow-sm shadow-emerald-600/10'
                          : 'border-border/50 bg-card/50 hover:bg-accent/30'
                      }`}
                    >
                      <span className="text-sm font-bold">{opt.label}</span>
                      <span className="text-[9px] text-muted-foreground">{opt.desc}</span>
                      {autoRefresh === opt.value && (
                        <span className="h-1 w-1 rounded-full bg-emerald-600" />
                      )}
                    </button>
                  ))}
                </div>
                {autoRefresh === 'off' && (
                  <div className="flex items-center gap-2 mt-3 rounded-lg border border-yellow-600/20 bg-yellow-600/5 p-2.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                    <p className="text-[10px] text-muted-foreground">Auto-refresh is disabled. You will need to manually refresh data.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Dashboard Info Card */}
          <motion.div variants={staggerItem}>
            <Card className="border-emerald-600/15">
              <CardHeader className="pb-3">
                <SectionHeader
                  icon={Shield}
                  title="Session & Security"
                  description="Current session information and security status"
                />
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-2.5">
                  {[
                    { label: 'Session Mode', value: 'Sandbox', badge: 'Active' },
                    { label: 'Constitution Version', value: 'v3.2', badge: 'Latest' },
                    { label: 'Dashboard Layout', value: dashboardLayout.charAt(0).toUpperCase() + dashboardLayout.slice(1), badge: 'Saved' },
                    { label: 'Auto-Refresh', value: autoRefresh === 'off' ? 'Disabled' : `Every ${autoRefresh}s`, badge: autoRefresh !== 'off' ? 'On' : 'Off' },
                  ].map(item => (
                    <div key={item.label} className="flex items-center justify-between rounded-lg border border-border/50 px-3 py-2">
                      <span className="text-xs text-muted-foreground">{item.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">{item.value}</span>
                        <Badge variant="outline" className={cn('text-[8px]', item.badge === 'Active' || item.badge === 'On' || item.badge === 'Latest' || item.badge === 'Saved' ? 'border-emerald-600/30 text-emerald-600 dark:text-emerald-400' : 'border-yellow-600/30 text-yellow-600 dark:text-yellow-400')}>
                          {item.badge}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* ── Section 5: Notification Preferences ───────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="border-orange-600/15">
            <CardHeader className="pb-3">
              <SectionHeader
                icon={notificationsEnabled ? Bell : BellOff}
                title="Notification Preferences"
                description="Control which notifications appear in the notification center"
                badge={notificationsEnabled ? 'On' : 'Off'}
              />
            </CardHeader>
            <CardContent className="pt-0">
              {/* Master toggle */}
              <div className="flex items-center justify-between rounded-lg border border-border/50 px-3 py-2.5 mb-3">
                <div>
                  <span className="text-xs font-medium">Enable Notifications</span>
                  <p className="text-[10px] text-muted-foreground">Master toggle for all notification types</p>
                </div>
                <Switch
                  checked={notificationsEnabled}
                  onCheckedChange={setNotificationsEnabled}
                />
              </div>

              {/* Per-type toggles */}
              <div className={`grid gap-2 sm:grid-cols-2 transition-opacity duration-200 ${notificationsEnabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
                {NOTIFICATION_TYPES.map(nt => (
                  <div key={nt.id} className="flex items-center justify-between rounded-lg border border-border/50 px-3 py-2.5">
                    <div>
                      <span className="text-xs font-medium">{nt.label}</span>
                      <p className="text-[10px] text-muted-foreground">{nt.description}</p>
                    </div>
                    <Switch
                      checked={notificationTypes[nt.id] ?? nt.defaultEnabled}
                      onCheckedChange={() => handleToggleNotification(nt.id)}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ── Section 6: Constitutional Rules ───────────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="border-red-600/15">
            <CardHeader className="pb-3">
              <SectionHeader
                icon={Shield}
                title="Constitutional Rules"
                description="System limits enforced by the NEXUS OS constitution"
                badge="v3.2"
              />
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium">Max Agents / hr</Label>
                  <Input
                    type="number"
                    value={constitution.maxAgents}
                    onChange={(e) => setConstitution(c => ({ ...c, maxAgents: parseInt(e.target.value) || 0 }))}
                    className="h-8 text-xs"
                  />
                  <p className="text-[9px] text-muted-foreground">Maximum concurrent agents allowed per hour</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium">API Calls / session</Label>
                  <Input
                    type="number"
                    value={constitution.apiCallsLimit}
                    onChange={(e) => setConstitution(c => ({ ...c, apiCallsLimit: parseInt(e.target.value) || 0 }))}
                    className="h-8 text-xs"
                  />
                  <p className="text-[9px] text-muted-foreground">Maximum API calls per session cycle</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium">File Writes / session</Label>
                  <Input
                    type="number"
                    value={constitution.fileWritesLimit}
                    onChange={(e) => setConstitution(c => ({ ...c, fileWritesLimit: parseInt(e.target.value) || 0 }))}
                    className="h-8 text-xs"
                  />
                  <p className="text-[9px] text-muted-foreground">Maximum file write operations per session</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium">Max Concurrent</Label>
                  <Input
                    type="number"
                    value={constitution.maxConcurrent}
                    onChange={(e) => setConstitution(c => ({ ...c, maxConcurrent: parseInt(e.target.value) || 0 }))}
                    className="h-8 text-xs"
                  />
                  <p className="text-[9px] text-muted-foreground">Maximum concurrent operations</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium">Health Check Interval (s)</Label>
                  <Input
                    type="number"
                    value={constitution.healthCheckInterval}
                    onChange={(e) => setConstitution(c => ({ ...c, healthCheckInterval: parseInt(e.target.value) || 0 }))}
                    className="h-8 text-xs"
                  />
                  <p className="text-[9px] text-muted-foreground">Seconds between health checks</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium">Trust Decay Rate / hr</Label>
                  <Input
                    type="number"
                    step="0.001"
                    value={constitution.trustDecayRate}
                    onChange={(e) => setConstitution(c => ({ ...c, trustDecayRate: parseFloat(e.target.value) || 0 }))}
                    className="h-8 text-xs font-mono"
                  />
                  <p className="text-[9px] text-muted-foreground">Rate at which trust scores decay per hour</p>
                </div>
              </div>
              <Separator className="my-4" />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={constitution.fallbackEnabled}
                    onCheckedChange={(checked) => setConstitution(c => ({ ...c, fallbackEnabled: checked }))}
                  />
                  <span className="text-xs font-medium">Pool Fallback</span>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={constitution.autoBlockCrit}
                    onCheckedChange={(checked) => setConstitution(c => ({ ...c, autoBlockCrit: checked }))}
                  />
                  <span className="text-xs font-medium">Auto-Block CRIT</span>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <Info className="h-3.5 w-3.5 text-red-600 dark:text-red-400 shrink-0" />
                <p className="text-[10px] text-muted-foreground">
                  Constitutional rules are enforced at runtime. Changes take effect on next session cycle.
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ── Section 7: Data Management ────────────────────────── */}
        <motion.div variants={staggerItem}>
          <Card className="border-amber-600/15">
            <CardHeader className="pb-3">
              <SectionHeader
                icon={Database}
                title="Data Management"
                description="Clear cache, export settings, or reset to factory defaults"
              />
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid gap-3 sm:grid-cols-3">
                {/* Clear Cache */}
                <button
                  onClick={handleClearCache}
                  className="flex flex-col items-center gap-2 rounded-lg border border-border/50 bg-card/50 p-4 transition-all duration-200 hover:bg-accent/30 hover:border-border"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
                    <Trash2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <span className="text-xs font-medium">Clear Cache</span>
                  <span className="text-[10px] text-muted-foreground text-center">Remove cached API responses and temporary data</span>
                </button>

                {/* Export Data */}
                <button
                  onClick={handleExportData}
                  className="flex flex-col items-center gap-2 rounded-lg border border-border/50 bg-card/50 p-4 transition-all duration-200 hover:bg-accent/30 hover:border-border"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600/10">
                    <Download className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <span className="text-xs font-medium">Export Settings</span>
                  <span className="text-[10px] text-muted-foreground text-center">Download current settings as JSON (keys masked)</span>
                </button>

                {/* Reset to Defaults */}
                <button
                  onClick={() => setResetDialogOpen(true)}
                  className="flex flex-col items-center gap-2 rounded-lg border border-red-600/20 bg-card/50 p-4 transition-all duration-200 hover:bg-red-600/5 hover:border-red-600/40"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-600/10">
                    <RotateCcw className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </div>
                  <span className="text-xs font-medium text-red-600 dark:text-red-400">Reset Defaults</span>
                  <span className="text-[10px] text-muted-foreground text-center">Restore all settings to factory defaults</span>
                </button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* ── Reset Confirmation Dialog ───────────────────────────── */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-600/15">
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <DialogTitle className="text-base">Reset All Settings</DialogTitle>
                <DialogDescription className="text-xs">
                  This action cannot be undone
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-xs text-muted-foreground">
              This will permanently delete all API keys, reset rate limits to defaults,
              restore notification preferences, and reset constitutional rules to factory values.
            </p>
            <div className="rounded-lg border border-red-600/20 bg-red-600/5 p-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                <span className="text-xs font-medium text-red-600 dark:text-red-400">
                  All API keys will be permanently deleted
                </span>
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" size="sm" onClick={() => setResetDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              className="gap-1.5"
              onClick={handleResetDefaults}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset All Settings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
