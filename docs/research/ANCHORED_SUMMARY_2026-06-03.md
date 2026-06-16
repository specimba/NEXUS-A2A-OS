---
id: NODE-MIG-ANCHORED_SUMMARY_2026_06_03
authority_scope: experimental
origin_sha256: ee65c6c9bb470e5de9acb5ac064fb2563db35d04aa628d11ad20d524b3cc7863
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-11E50B
---
# Anchored Summary — 2026-06-03 Deep Research Session

## Session Goal
Deep-probe the agent security landscape (MCP, OWASP ASI, compliance, competitive) and synthesize into a NEXUSCLAW design document — fusing NEXUS OS governance with the OpenClaw/C-KILOCLAW/NemoClaw ecosystem.

## What Was Done

### 1. MCP Security Deep Probe
| Finding | Source | Impact on NEXUSCLAW |
|---------|--------|---------------------|
| **CVE-2026-26015**: Ox Security disclosed RCE in DocsGPT v0.15.x via MCP STDIO transport-type substitution in `mcp_tool.py`. Unauthenticated attacker sends `transport_type: stdio` to `/api/mcp_server/test` → server executes arbitrary commands. 200k+ agent servers exposed. Fixed in cloud, self-hosted 0.15.x still vulnerable. | Ox Security Labs (June 2026) | **MUST** enforce transport whitelist in Bridge; never allow `stdio` from remote; validate stdin source |
| **LiteLLM proxy security**: No specific CVE found suggesting LiteLLM is currently clean. Standard best practices apply (rate limiting, audit logs, key rotation). | Web search | Low priority; monitor for future advisories |
| **Hermes Agent (Nous Research)**: Full-featured autonomous agent with persistent memory, 40+ built-in skills, auto-created SKILL.md skills, Docker sandbox (read-only root, dropped capabilities, --pid=host limitation noted, no seccomp by default, no net filter). MIT license, no telemetry, TUI interface. | Nous Research GitHub (Feb 2026) | **CRITICAL**: Skill auto-creation + SKILL.md portable format directly reusable. Docker sandbox hardening patterns are baseline but need seccomp/network policy addition for production |

### 2. OWASP ASI Top 10 for Agentic Applications 2026
| ID | Name | Attack Vector | NEXUSCLAW Mapping |
|----|------|--------------|-------------------|
| ASI01 | Agent Goal Hijack | Indirect prompt injection via tool outputs | KAIJU gate pre-execution policy |
| ASI02 | Tool Misuse & Exploitation | Tool parameter injection, unauthorized tool use | Tool permission manifests per skill |
| ASI03 | Identity & Privilege Abuse | Agent identity spoofing, privilege escalation | TrustEngine identity lineage |
| ASI04 | Agentic Supply Chain Vulnerabilities | Malicious skills/plugins, dependency confusion | VirusTotal + SkillSpector gating at install |
| ASI05 | Unexpected Code Execution (RCE) | MCP tool RCE, sandbox escape | Sandbox execution (Hermes/OpenShell pattern) |
| ASI06 | Memory & Context Poisoning | RAG store poisoning, conversation injection | Vault 5-track isolation, session accumulator |
| ASI07 | Insecure Inter-Agent Communication | Man-in-the-middle between agents | A2A over MCP with VAP audit chain |
| ASI08 | Cascading Failures | Agent A compromises Agent B through delegation | Circuit breakers in ModelRelay, spawn cooldown |
| ASI09 | Human-Agent Trust Exploitation | Agent impersonates human, social engineering | KAIJU HITL gates, trust score thresholds |
| ASI10 | Rogue Agents | Unauthorized agent creation, agent collusion | TrustEngine collapse detection at <15 score |

**Source**: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

### 3. AgentThreatBench (UK AISI)
First evaluation suite operationalizing OWASP ASI Top 10 into executable tasks. Merged into UKGovernmentBEIS/inspect_evals. Proposed for EleutherAI lm-evaluation-harness. Tasks include:
- `agent_threat_bench_memory_poison` (ASI06) — 10 samples, 8 attack types
- `agent_threat_bench_autonomy_hijack` (ASI01) — 6 samples
- `agent_threat_bench_data_exfil` (ASI01) — 8 samples
- Dual-metric scoring (utility + security)

**Source**: https://ukgovernmentbeis.github.io/inspect_evals/evals/safeguards/agent_threat_bench/

### 4. Singapore AI Governance Framework for Agentic AI v1.0 (IMDA, Jan 2026)
- 9 core principles: Transparency, Explainability, Human Oversight, Fairness, Accountability, Robustness, Safety, Data Governance, Proportionality
- **Directly applicable** as NEXUSCLAW compliance baseline
- §3 (Human Oversight) → KAIJU gate
- §5 (Transparency → VAP provenance chain
- §7 (Accountability) → TrustKernel identity → human binding

### 5. CLAW Ecosystem Deep Probe
| Component | Details | Relevance |
|-----------|---------|-----------|
| **NemoClaw** (NVIDIA) | Open-source security wrapper for OpenClaw. v0.0.55 current. Uses OpenShell kernel-level sandbox. Privacy Router for local/cloud model routing. Nemotron-only models. Linux only. One-command install. | **High**: OpenShell sandbox patterns, Privacy Router design; but vendor lock-in (NVIDIA models only) is a limitation |
| **OpenClaw + VirusTotal** (Feb 2026) | All ClawHub skills scanned by VirusTotal threat intelligence. NVIDIA SkillSpector integrated for vulnerability detection (Prompt Injection, MCP Tool Poisoning, Data Exfiltration patterns). | **High**: Model for NEXUSCLAW skill security gate |
| **OpenClaw + NVIDIA SkillSpector** | Vulnerability pattern detection per plugin: Data Exfiltration, Env Variable Harvesting, Intent-Code Divergence, Memory Manipulation. "Review" outcome rate is significant. | **High**: Patterns directly reusable in NEXUSCLAW scanning |
| **C-KILOCLAW** (existing) | Cloudflare Workers + Sandbox SDK + MCP. Already documented in handbook. | Existing executor option, no changes needed |
| **OpenClaw Gateway** | Port 18789, Svelte UI control panel. Exposes health endpoint, NOT an OpenAI-compatible API. Has OpenRouter key configured. | Background context for NEXUSCLAW gateway design |

### 6. Evaluation Ecosystem
| Framework | Purpose | NEXUSCLAW Use |
|-----------|---------|--------------|
| **ZClawBench** (Zhipu AI) | 3-level hybrid benchmark for OpenClaw agent tasks | Reference for functional eval |
| **ClawBench** (Zhang et al.) | Everyday online task completion | Reference for functional eval |
| **ClawArena** (arXiv) | Evolving information environments | Research reference |
| **CVE-Bench** (NIST CAISI) | Cyber capability evaluation | Security eval reference |
| **AgentBench** (THUDM) | Multi-environment agent eval | Broader context |
| **Giskard** | Enterprise red teaming platform | Continuous testing model |
| **Trent AI** ($13M raised) | Agentic security agent loop | Market validation |

### 7. Competitive/Industry Context
| Player | Relevance |
|--------|-----------|
| **LlamaIndex** | $28M total raised. Pivoted to Workflows + llama-deploy. 25M+ downloads/month. Dominant for RAG/retrieval-heavy agents. Critique: abstraction overhead is significant for simple use cases |
| **Trent AI** | $13M raised May 2026. Four-agent security loop (Scan → Judge → Mitigate → Evaluate). Available as OpenClaw skill. Direct market validation for NEXUSCLAW security approach |
| **Giskard** | Enterprise LLM agent red teaming. Hub + Open Source + Research. Continuous testing, custom failure categories |
| **Endor Labs** | "Agent Security League" report (Apr 2026). AI-generated code passes tests but fails security. Agent capability ≠ security |
| **Ox Security** | MCP RCE disclosure (CVE-2026-26015). Relevant for MCP bridge hardening |

## Artifacts Produced
1. **`docs/research/NEXUSCLAW_DESIGN.md`** — Comprehensive 6-section design document covering architecture, security mapping, compliance, implementation roadmap
2. **This anchored summary** — Full evidence inventory for all deep probes

## Key Design Decisions for NEXUSCLAW
1. MCP transport: block `stdio` from remote unconditionally; whitelist SSE/WebSocket/Streamable-HTTP
2. Sandbox: adopt Hermes Docker pattern + extend with seccomp/network policy (do not write new sandbox)
3. Skill format: adopt SKILL.md (Hermes format) + NEXUSCLAW permission manifest extension
4. Security gate: mirror OpenClaw VirusTotal + NVIDIA SkillSpector pipeline
5. Compliance baseline: map to Singapore AI Governance §1-9 as primary framework
6. Eval suite: adopt AgentThreatBench (UK AISI) as mandatory CI gate
7. Model routing: keep Privacy Router concept but make model-provider-agnostic (avoid NVIDIA-only lock-in)

## Open Questions / Next Actions
- [ ] Fetch NemoClaw v0.0.55 installer script to understand OpenShell API surface
- [ ] Integrate AgentThreatBench into NEXUS test suite (port from inspect_evals)
- [ ] Draft MCP transport validator code for Bridge layer
- [ ] Draft SKILL.md manifest parser
- [ ] Map existing security tests to OWASP ASI categories for gap analysis
- [ ] Assess OpenShell GitHub source for sandbox policy reusability
- [ ] Check if NemoClaw Privacy Router can be adapted for non-NVIDIA models
