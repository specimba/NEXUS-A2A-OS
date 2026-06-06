'use client'

import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Settings,
  Palette,
  Bell,
  Shield,
  Database,
  Cpu,
  Clock,
  Zap,
  Globe,
  RefreshCw,
} from 'lucide-react'
import { useTheme } from 'next-themes'

interface SettingsPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SettingsPanel({ open, onOpenChange }: SettingsPanelProps) {
  const { theme, setTheme } = useTheme()
  const [refreshInterval, setRefreshInterval] = useState('15')
  const [notificationsEnabled, setNotificationsEnabled] = useState(true)
  const [soundEnabled, setSoundEnabled] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [compactMode, setCompactMode] = useState(false)
  const [defaultModel, setDefaultModel] = useState('glm-4-7-nim')
  const [maxTokens, setMaxTokens] = useState('100000')
  const [language, setLanguage] = useState('en')

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[420px] sm:w-[540px] p-0 bg-card overflow-y-auto">
        <SheetHeader className="px-6 py-4 border-b border-border/50">
          <SheetTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            System Settings
          </SheetTitle>
        </SheetHeader>

        <div className="px-6 py-4 space-y-6">
          {/* Appearance */}
          <section>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <Palette className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Appearance
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Theme</Label>
                  <p className="text-[11px] text-muted-foreground">Toggle between light and dark mode</p>
                </div>
                <Select value={theme} onValueChange={setTheme}>
                  <SelectTrigger className="w-32 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="system">System</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Compact Mode</Label>
                  <p className="text-[11px] text-muted-foreground">Reduce padding and spacing</p>
                </div>
                <Switch checked={compactMode} onCheckedChange={setCompactMode} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Language</Label>
                  <p className="text-[11px] text-muted-foreground">Interface language</p>
                </div>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger className="w-32 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="tr">Türkçe</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          <Separator />

          {/* Notifications */}
          <section>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <Bell className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Notifications
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Push Notifications</Label>
                  <p className="text-[11px] text-muted-foreground">Receive alerts for critical events</p>
                </div>
                <Switch checked={notificationsEnabled} onCheckedChange={setNotificationsEnabled} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Sound Alerts</Label>
                  <p className="text-[11px] text-muted-foreground">Audio notification for errors</p>
                </div>
                <Switch checked={soundEnabled} onCheckedChange={setSoundEnabled} />
              </div>
            </div>
          </section>

          <Separator />

          {/* Data & Refresh */}
          <section>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <RefreshCw className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Data & Refresh
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Auto Refresh</Label>
                  <p className="text-[11px] text-muted-foreground">Automatically update dashboard data</p>
                </div>
                <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Refresh Interval</Label>
                  <p className="text-[11px] text-muted-foreground">How often to poll for updates</p>
                </div>
                <Select value={refreshInterval} onValueChange={setRefreshInterval}>
                  <SelectTrigger className="w-32 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">5 seconds</SelectItem>
                    <SelectItem value="15">15 seconds</SelectItem>
                    <SelectItem value="30">30 seconds</SelectItem>
                    <SelectItem value="60">1 minute</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          <Separator />

          {/* AI Configuration */}
          <section>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <Cpu className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              AI Configuration
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Default Model</Label>
                  <p className="text-[11px] text-muted-foreground">Model used for AI assistant</p>
                </div>
                <Select value={defaultModel} onValueChange={setDefaultModel}>
                  <SelectTrigger className="w-40 h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="glm-4-7-nim">GLM-4.7 (z-ai)</SelectItem>
                    <SelectItem value="deepseek-r1-or">DeepSeek R1 (OpenRouter)</SelectItem>
                    <SelectItem value="llama-3.3-70b-cerebras">Llama 3.3 70B (Cerebras)</SelectItem>
                    <SelectItem value="llama-3.3-70b-groq">Llama 3.3 70B (Groq)</SelectItem>
                    <SelectItem value="qwen3-coder-or">Qwen3 Coder (OpenRouter)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-sm">Token Budget</Label>
                  <p className="text-[11px] text-muted-foreground">Max tokens per session</p>
                </div>
                <Input
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(e.target.value)}
                  className="w-32 h-8 text-xs text-right font-mono"
                />
              </div>
            </div>
          </section>

          <Separator />

          {/* Governor Settings */}
          <section>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Governor & Safety
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <div>
                    <span className="text-sm font-medium">Constitution Enforcement</span>
                    <p className="text-[10px] text-muted-foreground">Block dangerous actions automatically</p>
                  </div>
                </div>
                <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-emerald-600/20 text-emerald-600 dark:text-emerald-400 border-0">
                  Active
                </Badge>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <div>
                    <span className="text-sm font-medium">Trust Score Threshold</span>
                    <p className="text-[10px] text-muted-foreground">Minimum trust score for agent operations</p>
                  </div>
                </div>
                <span className="text-sm font-mono font-bold">0.50</span>
              </div>
            </div>
          </section>

          <Separator />

          {/* System Info */}
          <section>
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-3">
              <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              System Information
            </h3>
            <div className="space-y-2 p-3 rounded-lg bg-muted/30 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version</span>
                <span className="font-mono">NEXUS OS v3.1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">SDK</span>
                <span className="font-mono">z-ai-web-dev-sdk</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Database</span>
                <span className="font-mono">SQLite (Prisma)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Providers</span>
                <span className="font-mono">14 configured</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Runtime</span>
                <span className="font-mono">Next.js 16 + Bun</span>
              </div>
            </div>
          </section>

          {/* Bottom spacer */}
          <div className="h-4" />
        </div>
      </SheetContent>
    </Sheet>
  )
}
