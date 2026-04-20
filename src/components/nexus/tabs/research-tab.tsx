'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BookOpen, ExternalLink, Flame, Target, Beaker, ChevronRight } from 'lucide-react'

const p0Items = [
  { id: 'isc-bench-2603.23509', title: 'Internal Safety Collapse in Frontier LLMs', relevance: 0.97, task: 'Import 53 TVD scenarios into stresslab/templates/. Create validator that checks if harmful content is structurally required.', deliverable: 'stresslab/isc_runner.py', status: 'in_progress' },
  { id: 'or-bench-2405.20947', title: 'OR-Bench: Over-Refusal Benchmark', relevance: 0.95, task: 'Load 1k hard prompts. Measure over-refusal rate per lane. Update trust_scoring.py lane thresholds.', deliverable: 'evals/overrefusal/or_bench_eval.py', status: 'pending' },
  { id: 'dual-pool-2502.00409', title: 'Dual-Pool Token-Budget Routing', relevance: 0.93, task: 'Implement bytes-to-token EMA estimator in gmr/scheduler.py. Split GMR pools into short (<4k) and long context.', deliverable: 'gmr/scheduler.py', status: 'pending' },
  { id: 'deer-flow', title: 'bytedance/deer-flow', relevance: 0.93, task: 'Port sub-agent harness pattern: lead agent + parallel workers with isolated sandboxes.', deliverable: 'swarm/foreman.py refactor', status: 'pending' },
]

const p1Items = [
  { id: 'routing-survey-2604.08075', title: 'Doing More with Less', relevance: 0.94, task: 'Implement cost-performance scoring function. Add pre-generation router in GMR.' },
  { id: 'dynamic-routing-2603.04445', title: 'Dynamic Model Routing and Cascading', relevance: 0.92, task: 'Build 3-dimension router (when/what/how). Add uncertainty-based fallback.' },
  { id: 'tale-2603.08425', title: 'Token-Budget-Aware LLM Reasoning', relevance: 0.92, task: 'Add per-query token budget estimator to TokenGuard. Enforce via check_and_reserve().' },
  { id: 'infiagent-2412.18547', title: 'InfiAgent', relevance: 0.92, task: 'Prototype file-centric state in vault/manager.py. Replace prompt-as-memory with snapshot reconstruction.' },
  { id: 'rigorllm-2403.13031', title: 'RigorLLM', relevance: 0.87, task: 'Add fusion guardrail (KNN + LLM) to governor/moderation.py for jailbreak resilience.' },
  { id: 'shieldgemma-2407.21772', title: 'ShieldGemma', relevance: 0.9, task: 'Integrate ShieldGemma-2B as fast moderation adapter. Benchmark vs current.' },
]

const p2Items = [
  { id: 'guardt2i-2403.01446', title: 'GuardT2I', relevance: 0.84, task: 'Evaluate generative moderation for multimodal agents' },
  { id: 'aegis-2404.05993', title: 'AEGIS', relevance: 0.88, task: 'Study ensemble safety experts for online adaptation' },
  { id: 'identity-suppression-2409.13725', title: 'Identity Suppression in AI Moderation', relevance: 0.92, task: 'Audit current moderation for identity bias' },
  { id: 'last30days-skill', title: 'last30days-skill', relevance: 0.92, task: 'Integrate as NEXUS world-awareness skill' },
  { id: 'superpowers', title: 'superpowers (TDD)', relevance: 0.88, task: 'Adopt TDD workflow for agent-generated code' },
  { id: 'ironengine-2601.03204', title: 'IronEngine', relevance: 0.88, task: 'Review three-phase pipeline for planner-reviewer pattern' },
]

export function ResearchTab() {
  return (
    <div className="space-y-6 p-6">
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-red-600/20 bg-red-600/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Flame className="h-4 w-4 text-red-400" />
              <p className="text-xs text-muted-foreground">P0 — Implement Now</p>
            </div>
            <p className="text-2xl font-bold text-red-400">{p0Items.length}</p>
          </CardContent>
        </Card>
        <Card className="border-orange-600/20 bg-orange-600/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-orange-400" />
              <p className="text-xs text-muted-foreground">P1 — Next Sprint</p>
            </div>
            <p className="text-2xl font-bold text-orange-400">{p1Items.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">P2 — Research</p>
            </div>
            <p className="text-2xl font-bold">{p2Items.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Vetted</p>
            <p className="text-2xl font-bold">{p0Items.length + p1Items.length + p2Items.length}</p>
            <p className="text-[10px] text-muted-foreground">papers + repos</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="p0" className="space-y-4">
        <TabsList>
          <TabsTrigger value="p0">P0 — Now</TabsTrigger>
          <TabsTrigger value="p1">P1 — Next</TabsTrigger>
          <TabsTrigger value="p2">P2 — Research</TabsTrigger>
          <TabsTrigger value="practice">Daily Practice</TabsTrigger>
        </TabsList>

        {/* P0 */}
        <TabsContent value="p0">
          <div className="space-y-3">
            {p0Items.map((item) => (
              <Card key={item.id} className="hover:border-red-600/20 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-red-600/15">
                      <Flame className="h-4 w-4 text-red-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                        <Badge className="bg-red-600/15 text-red-400 border-0 text-[9px]">
                          Relevance: {(item.relevance * 100).toFixed(0)}%
                        </Badge>
                        {item.status === 'in_progress' && (
                          <Badge className="bg-emerald-600/15 text-emerald-400 border-0 text-[9px]">IN PROGRESS</Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm font-medium">{item.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                      <div className="mt-2 flex items-center gap-2">
                        <code className="text-[10px] rounded bg-accent px-1.5 py-0.5">{item.deliverable}</code>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* P1 */}
        <TabsContent value="p1">
          <div className="space-y-3">
            {p1Items.map((item) => (
              <Card key={item.id} className="hover:border-orange-600/20 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-orange-600/15">
                      <Target className="h-4 w-4 text-orange-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                        <Badge className="bg-orange-600/15 text-orange-400 border-0 text-[9px]">
                          Relevance: {(item.relevance * 100).toFixed(0)}%
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm font-medium">{item.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* P2 */}
        <TabsContent value="p2">
          <div className="space-y-3">
            {p2Items.map((item) => (
              <Card key={item.id} className="hover:border-emerald-600/20 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
                      <Beaker className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-muted-foreground">{item.id}</span>
                        <Badge variant="outline" className="text-[9px]">
                          {(item.relevance * 100).toFixed(0)}%
                        </Badge>
                      </div>
                      <p className="mt-1 text-sm font-medium">{item.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.task}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Daily Practice */}
        <TabsContent value="practice">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <BookOpen className="h-4 w-4" /> Daily Research Practice Template
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0 space-y-4">
              <div className="grid gap-3 md:grid-cols-5">
                {[
                  { step: '1', name: 'INTAKE', desc: 'Collect up to 20 links, deduplicate, prioritize by NEXUS relevance', time: '5 min' },
                  { step: '2', name: 'VETTING', desc: 'Extract abstract, conclusion, score relevance 0-1, map to modules', time: '15 min' },
                  { step: '3', name: 'MANIFEST', desc: 'Output papers_manifest with all structured fields', time: '5 min' },
                  { step: '4', name: 'PRIORITY', desc: 'Sort by relevance, tier into P0/P1/P2 with concrete tasks', time: '5 min' },
                  { step: '5', name: 'DELIVER', desc: 'Save manifest + queue, provide download, log to VAP chain', time: '2 min' },
                ].map((s) => (
                  <div key={s.step} className="rounded-md border border-border p-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-600/15 text-xs font-bold text-emerald-400">{s.step}</span>
                      <span className="text-xs font-semibold">{s.name}</span>
                    </div>
                    <p className="mt-1.5 text-[11px] text-muted-foreground">{s.desc}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground/60">~{s.time}</p>
                  </div>
                ))}
              </div>
              <div className="rounded-md border border-border/50 bg-accent/30 p-3">
                <p className="text-xs font-medium">Quality Gates</p>
                <ul className="mt-1 space-y-1 text-[11px] text-muted-foreground">
                  <li>• No dumping: every entry must have abstract + conclusion vetted</li>
                  <li>• No hallucination: cite source lines for key numbers</li>
                  <li>• Max 20 items per run to maintain depth</li>
                  <li>• Run 1-2x daily as requested</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
