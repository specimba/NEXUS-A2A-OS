---
id: NODE-MIG-NEXUSCLAW_DESIGN
authority_scope: experimental
origin_sha256: 4b8f0cb723b3c4bc2a2acbb7360050ca27b47476a4b822bd668d1e255f22028b
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-63A307
---
# NEXUSCLAW — Architecture Synthesis & Governance-Grounded Agent OS

## Premise

NEXUSCLAW is the fusion of two lineages:

- **NEXUS OS**: local-first governed agent OS (port 7352 governance, TrustEngine v2.2, KAIJU gates, Vault 5-track memory, ModelRelay, TWAVE low-VRAM layer)
- **CLAW ecosystem**: OpenClaw (community agent runtime, ClawHub skill marketplace), NemoClaw (NVIDIA sandbox wrapper), C-KILOCLAW (Cloudflare edge experiments), NEMO Hermes (Nous Research autonomous agent)

NEXUSCLAW does not replace either. It is the **governed convergence layer** — a reference architecture for running agentic workloads that are proposal-bound, test-gated, provenance-tracked, sandboxed, and compliance-mapped.

## Canonical Fork Discovery (June 2026)

Through deep-probe analysis of major NEXUS OS forks:

- **DERDDRE-down-MAIN** (463 items): Contains opusmanSEEKv4 "Local Claw Orchestrator" with complete Level-4 Claw layer design, Anti-Zombie Rules, DoppelGround protocol, OODA Loop + S-P-E-W Memory, Token Saver Discipline
- **Archivist** (1,340+ items): Contains GROKsharedfolder with Phase 6 Governed MCP Server (370 lines with TrustKernel integration), MCP Red Team Lab test cases (MCP-01 through MCP-06), and Archivist 4-Layer Truth Model (SOURCE/EXTRACTED/INFERRED/CANONICAL)

These forks provide validated implementations that NEXUSCLAW integrates rather than reinvents.

---

## 1. Landscape Synthesis (June 2026 Deep Probe)

### 1.1 CLAW Ecosystem Topology + Fork Discoveries

```
OpenClaw (community agent, Peter Steinberger → OpenAI)
   ├── ClawHub (skill marketplace, VirusTotal-scanned, NVIDIA SkillSpector)
   ├── OpenClaw Gateway (port 18789, Svelte UI, agent orchestration)
   ├── AutoClaw (desktop app, separate config)
   │
   ├── NemoClaw (NVIDIA, kernel-level sandbox via OpenShell)
   │   ├── OpenShell runtime (policy-based syscall/fs/network control)
   │   ├── Privacy Router (intelligent local/cloud model routing)
   │   ├── Nemotron models only (Nano 4B, Super 120B)
   │   └── One-command: curl -fsSL https://nvidia.com/nemoclaw.sh | bash
   │
   ├── C-KILOCLAW (Cloudflare Workers + Sandbox SDK + MCP)
   │   └── Zero local resource burn, disposable sandboxes
   │
   ├── NEMO Hermes (Nous Research, Feb 2026)
   │   ├── 40+ built-in skills, auto-created skills (SKILL.md format)
   │   ├── Docker sandbox (read-only root, dropped caps, PID limits)
   │   ├── 4 execution envs: Local, Docker, SSH, Modal/Singularity
   │   ├── Persistent memory, no telemetry, MIT license
   │   └── Critical: skill auto-creation pattern directly reusable
   │
   └── Fork Discoveries (Validated Implementations)
       ├── opusmanSEEKv4 (Local Claw Orchestrator)
       │   ├── Level-4 Claw Layer Design
       │   ├── Anti-Zombie Rules, DoppelGround protocol
       │   ├── OODA Loop + S-P-E-W Memory (Sensing-Processing-Execution-Withholding)
       │   └── Token Saver Discipline
       │
       ├── Phase 6 Governed MCP Server (Archivist)
       │   ├── 370-line implementation with TrustKernel integration
       │   ├── Workspace escape prevention
       │   ├── Tool manifest validation
       │   └── Audit trail enforcement
       │
       └── Formal Safety Calculus Extension (DERDDRE-down-MAIN)
           ├── 8 identified gaps requiring resolution
           ├── 3 new theorems + 2 new axioms needed
           └── Supply Chain Integrity, Knowledge Consistency focus
```

### 1.2 Security Threat Landscape

| Threat | Source | NEXUSCLAW Mitigation |
|--------|--------|---------------------|
| MCP STDIO RCE (CVE-2026-26015) | Ox Security, DocsGPT v0.15.x | Enforce transport whitelist; never allow stdio from remote; validate stdin source |
| OWASP ASI01 (Goal Hijack) | OWASP ASI Top 10 2026 | KAIJU gate pre-execution policy check |
| OWASP ASI02 (Tool Misuse) | OWASP ASI Top 10 2026 | Tool permission manifests per skill |
| OWASP ASI03 (Identity Abuse) | OWASP ASI Top 10 2026 | TrustEngine v2.2 identity lineage |
| OWASP ASI04 (Supply Chain) | OWASP ASI Top 10 2026 | VirusTotal + SkillSpector gating at install |
| OWASP ASI05 (Unexpected Code Execution) | OWASP ASI Top 10 2026 | Sandbox execution (Hermes/OpenShell pattern) |
| OWASP ASI06 (Memory Poisoning) | OWASP ASI Top 10 2026 | Vault 5-track isolation, session accumulator detection |
| OWASP ASI07 (Insecure Inter-Agent Comms) | OWASP ASI Top 10 2026 | A2A over MCP with VAP audit chain |
| OWASP ASI08 (Cascading Failures) | OWASP ASI Top 10 2026 | Circuit breakers in ModelRelay, cooldown in Spawner |
| OWASP ASI09 (Human-Agent Trust) | OWASP ASI Top 10 2026 | KAIJU human-in-the-loop gates |
| OWASP ASI10 (Rogue Agents) | OWASP ASI Top 10 2026 | TrustEngine collapse detection, TrustKernel identity binding |

### 1.3 Evaluation Frameworks

| Framework | Focus | Relevance to NEXUSCLAW |
|-----------|-------|------------------------|
| **AgentThreatBench** (UK AISI) | OWASP ASI Top 10 operationalized tasks | MUST adopt as security regression suite |
| **ZClawBench** (Zhipu AI) | OpenClaw end-to-end agent tasks (3-level hybrid) | Reference for NEXUSCLAW benchmark |
| **ClawBench** (Zhang et al. 2026) | Everyday online tasks | Reference for functional eval |
| **ClawArena** (arXiv 2604.04202) | Evolving information environments | Research reference |
| **CVE-Bench** (NIST CAISI) | Cyber capability evaluation | Reference for security eval |
| **DeepEval** (confident-ai) | LLM-as-judge evals | Secondary reference |
| **Giskard** | Enterprise red teaming | Reference for continuous testing |
| **Trent AI** ($13M raised) | Agentic security agent loop | Market validation of the category |

---

## 2. NEXUSCLAW Architecture

### 2.1 Layer Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                      │
│  GeniusTurtle UI │ AutoClaw Desktop │ Third-party Apps   │
├──────────────────────────────────────────────────────────┤
│                    BRIDGE LAYER (port 7352)               │
│  MCP Gateway ├── Transport Security (no stdio from remote)│
│  A2A Protocol ├── Capability Discovery                    │
│  Secrets Relay ├── Provider Rotation (OpenRouter fallback)│
├──────────────────────────────────────────────────────────┤
│                    GOVERNANCE PLANE                       │
│  KAIJU Gates ├── Pre-execution Policy ├── Human-in-Loop   │
│  TrustEngine v2.2 ├── TrustKernel ├── Identity Lineage    │
│  Compliance Mapper ├── Singapore AI Gov ├── EU AI Act     │
├──────────────────────────────────────────────────────────┤
│                    EXECUTION PLANE                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ OpenShell   │  │ Hermes      │  │ Cloudflare  │      │
│  │ Sandbox     │  │ Docker      │  │ Sandbox SDK │      │
│  │ (NVIDIA)    │  │ Sandbox     │  │ (C-KILOCLAW)│      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│  │ Skill Execution ├── SKILL.md format ├── TempFS only    │
├──────────────────────────────────────────────────────────┤
│                    MODEL PLANE (port 11434 / external)    │
│  ModelRelay Gateway ├── Circuit Breakers ├── Quota Aware  │
│  OpenRouter ├── Ollama ├── NVIDIA Nemotron ├── DeepSeek   │
├──────────────────────────────────────────────────────────┤
│                    STORAGE & EVIDENCE PLANE               │
│  Vault 5-Track │ VAP Audit Chain │ Memory Poison Detect  │
│  TokenGuard │ Session Accumulator │ Evidence Hashes      │
├──────────────────────────────────────────────────────────┤
│                    EVALUATION PLANE                       │
│  AgentThreatBench │ ZClawBench │ CVE-Bench │ DeepEval    │
│  Continuous Red Teaming (Giskard pattern)                │
└──────────────────────────────────────────────────────────┘
```

### 2.2 MCP Bridge Security (Post CVE-2026-26015)

The Ox Security RCE (CVE-2026-26015) exploited `transport_type: stdio` from remote in DocsGPT's `mcp_tool.py`. NEXUSCLAW mandates:

```python
# Enforced in Bridge layer
ALLOWED_MCP_TRANSPORTS = {"sse", "websocket", "streamable-http"}
BLOCKED_TRANSPORTS = {"stdio"}  # Never from remote

class MCPTransportValidator:
    @staticmethod
    def validate(request: dict) -> bool:
        transport = request.get("transport_type", "")
        if transport in BLOCKED_TRANSPORTS:
            raise MCPTransportError(
                f"Transport '{transport}' blocked from remote sources"
            )
        if transport not in ALLOWED_MCP_TRANSPORTS:
            raise MCPTransportError(f"Unknown transport '{transport}'")
        return True
```

Additionally, every MCP tool invocation requires:
- **Source identity** (`agent_id` header, bound to TrustKernel session)
- **Tool manifest** (declared parameters, no parameter injection)
- **Stdout sanitization** via TerminalSanitizer (existing module)
- **Rate limiting** via TokenGuard budget gate

### 2.3 Sandbox Model: Hermes + OpenShell Hybrid

Combining the best of both:

| Feature | Hermes Agent (Nous) | OpenShell (NVIDIA) | NEXUSCLAW |
|---------|-------------------|-------------------|-----------|
| Sandbox type | Docker (read-only root, dropped caps) | Kernel-level (seccomp, landlock) | Both available; policy-selectable |
| Skill format | SKILL.md (auto-created) | NEMO blueprint | SKILL.md + policy manifest |
| Network policy | None (full access) | Declarative egress whitelist | Declarative egress + approval queue |
| FS policy | Read-only /, write to /tmp | Configurable paths | TempFS only + explicit mounts |
| Model binding | Per-call selection | Privacy Router (local/cloud) | Policy-gated model routing |
| Execution envs | 4 (Terminal/Docker/SSH/Modal) | Docker + host | Pluggable executor (Hermes interface) |
| Memory | Persistent (PGVector) | None | Vault 5-track |
| Telemetry | None | Audit logs | VAP chain + optional telemetry |

**SKILL.md manifest format (extended for NEXUSCLAW):**

```markdown
# Skill: example-tool
**version**: 1.0.0
**permissions**:
  filesystem:
    read: ["/sandbox/data/"]
    write: ["/sandbox/output/"]
  network:
    allow: ["api.example.com:443"]
    deny: ["*"]
  model:
    allow: ["openrouter/*", "ollama/*"]
    deny: ["openai/*"]  # No OpenAI unless explicitly approved
**sandbox**: docker  # or openshell, cloudflare
**max_tokens**: 4000
**timeout**: 120
**audit**: required
```

### 2.4 Compliance Mapping

| Singapore AI Governance Principle | NEXUSCLAW Implementation |
|----------------------------------|------------------------|
| §1 Transparency (agent identity disclosure) | TrustKernel identity lineage; VAP chain records agent_id per action |
| §2 Explainability (decision rationale) | KAIJU gate logs decision rationale to VAP |
| §3 Human Oversight (meaningful control) | KAIJU HITL gates; configurable approval thresholds |
| §4 Fairness (no discriminatory outcomes) | TrustEngine fairness-aware scoring (future) |
| §5 Accountability (clear liability) | TrustKernel binds agent_id → human_operator |
| §6 Robustness & Reliability | Circuit breakers, retry policy, cooldown |
| §7 Safety & Security | OWASP ASI mitigation mapping (above) |
| §8 Data Governance | Vault 5-track with encryption policy |
| §9 Proportionality (risk-based controls) | Trust score → escalating scrutiny (TrustEngine CDR) |

### 2.5 Evaluation & CI Gate

NEXUSCLAW adopts **AgentThreatBench** by UK AISI as the canonical security regression suite:

```
PR pipeline:
  1. lint / typecheck
  2. pytest (full suite, >1300 tests)
  3. AgentThreatBench (security regression):
     - agent_threat_bench_memory_poison (ASI06)
     - agent_threat_bench_autonomy_hijack (ASI01)
     - agent_threat_bench_data_exfil (ASI01)
  4. ZClawBench subset (functional agent tasks)
  5. CVE-Bench subset (cyber capability, if applicable)
```

### 2.6 Skill Marketplace Security Gate

Mirroring OpenClaw's VirusTotal + NVIDIA SkillSpector integration:

```
Skill publish → ClawHub-style registry:
  1. VirusTotal scan (malware telemetry)
  2. NVIDIA SkillSpector scan (vulnerability patterns):
     - Data Exfiltration patterns
     - Prompt Injection patterns
     - MCP Tool Poisoning patterns
     - Intent-Code Divergence detection
  3. Manual review queue for "Review" outcome
  4. TrustScore ≥ 30 for auto-approve; else KAIJU gate
```

---

## 3. Implementation Status (June 2026)

### 3.1 Implemented Core

| Component | Status | Files |
|-----------|--------|-------|
| NexusClaw V0 Coordinator | ✅ 40 tests pass | `nexus_os/nexusclaw/` (coordinator, envelopes, security, gross, evidence) |
| GovernedMemoryBroker | ✅ 132 tests pass | `nexus_os/vault/governed_memory_broker.py` |
| TrustKernel Non-Linear Budget | ✅ 60 tests pass | `nexus_os/governor/trust_kernel.py` (derive_resource_budget) |
| MCP Transport Validator | ✅ Wired into Bridge + MCP | `nexus_os/bridge/transport_validator.py` |
| CLI (nexusctl) | ✅ nexusctl nexusclaw commands | `nexusctl/cli.py` |
| Port Ownership Enforced | ✅ 7352/7353/7354/7355/11436 | `nexus_os/nexusclaw/coordinator.py` |
| Hermes SOUL Profile | ✅ Installed to WSL Hermes | `docs/hermes/NEXUS_MAIN_SOUL.md` |
| GROSS Material-Change Sentinel | ✅ Cheap DONT_NOTIFY | `nexus_os/nexusclaw/gross.py` |
| Evidence Matrix | ✅ Secret-free artifact classification | `nexus_os/nexusclaw/evidence.py` |
| Intern AI Provider | ✅ 6 tests pass, all surfaces wired | `upload/intern_ai_lanes.py`, `.env.example` |
| Credential Artifact Guards | ✅ .gitignore for *.jwt, api-key-*, etc. | `.gitignore` |
| ModelRelay Port Alignment | ✅ Default moved from 7352 → 7355 | `nexus_os/relay/model_relay.py`, GMR/Hermes defaults |

### 3.2 Behavior Enforcement

| Scenario | Budget Class | Tokens | Tools | FS | Egress |
|----------|-------------|--------|-------|----|--------|
| Cold/new agent | CONSTRAINED | 3,200 | None | Read-only | None |
| Mature/elevated agent | ELEVATED | 36,000 | 6 parallel | Scoped write | Approved-only |
| CDR Cascade | QUARANTINED | 512 | None | None | None |
| CDR Collapse | LOCKED | 0 | Denied | None | None |

## 4. Mapping to Existing NEXUS OS Code

| NEXUS Module | NEXUSCLAW Evolution | Status |
|---|---|---|
| `nexus_os/bridge/` | MCP transport validator, no stdio from remote | ✅ Implemented |
| `nexus_os/governor/trust_kernel.py` | Non-linear resource budget (tanh/Qeff/posterior/CDR) | ✅ Implemented |
| `nexus_os/governor/` (KAIJU) | Add skill manifest validation gate | 🔄 Next |
| `nexus_os/vault/` (5-track) | GovernedMemoryBroker connects budget → memory | ✅ Implemented |
| `nexus_os/monitoring/token_guard.py` | No change; budget gating works | ✅ Already works |
| `nexus_os/security/session_accumulator.py` | Already has MT-AgentRisk detection (5 signals) | ✅ Already works |
| `nexus_os/swarm/openclaw_spawner.py` | Add sandbox selector, skill manifest parsing | 🔄 Next |
| `nexus_os/mcp/server.py` | Transport validation + GovernedMemoryBroker in call_tool | ✅ Wired |
| `nexus_os/nexusclaw/` | Thin governed coordinator V0 | ✅ Implemented |
| `scripts/zo_nexus_state_bridge.py` | No change; read-only state bridge works | ✅ Already works |
| `docs/handbook/08_C_KILOCLAW_FASTBOOT.md` | Reference architecture for Cloudflare executor | ✅ Reference |

---

## 5. Implementation Roadmap (Updated June 2026)

### Phase 1: Core V0 (Completed ✅)
- [x] Write this design document
- [x] Add MCP transport validator to Bridge layer
- [x] Implement NexusClaw V0 coordinator with typed envelopes
- [x] Implement non-linear trust-derived resource budgets
- [x] Implement GovernedMemoryBroker (hot SuperLocal → canonical 5-track → semantic Mem0)
- [x] Wire GROSS material-change sentinel (cheap DONT_NOTIFY)
- [x] Create evidence matrix for Downloads/GROSS artifact classification
- [x] Fix import bug (mem0_adapter → memory_adapter in autoharness.py, hermes_experience.py)
- [x] Align ModelRelay default port (7352 → 7355)
- [x] Add Hermes SOUL profile for NEXUS main agent

### Phase 2: Hardening & Integration (Current)
- [ ] Integrate AgentThreatBench security regression suite (port from UK AISI inspect_evals)
- [ ] Wire MCP Red Team Lab test cases (MCP-01 through MCP-06)
- [ ] Implement sandbox selector (Hermes Docker / OpenShell / Cloudflare)
- [ ] Add trust scoring per OWASP ASI category in TrustEngine
- [ ] Implement SKILL.md manifest parser for NEXUSCLAW
- [ ] Wire VirusTotal-style scan gate in skill publish flow

### Phase 3: Medium-term (3-6 sessions)
- [ ] Build NEXUSCLAW-specific skill registry (ClawHub-compatible)
- [ ] Implement Privacy Router (local/cloud model routing per policy)
- [ ] Add continuous red teaming loop (Giskard pattern)
- [ ] Integrate Formal Safety Calculus Extensions (3 theorems, 2 axioms)
- [ ] Full Singapore AI Governance compliance report generator

### Phase 4: Long-term (Future)
- [ ] Cross-agent identity federation (TrustKernel ↔ Zo)
- [ ] Production ASBOM maturity
- [ ] Public-facing NEXUSCLAW skill marketplace
- [ ] Independent security audit (Jamieson O'Reilly caliber)
- [ ] Archivist 4-Layer Truth Model integration (SOURCE/EXTRACTED/INFERRED/CANONICAL)

---

## 5. Key External References

| Resource | URL |
|----------|-----|
| OWASP ASI Top 10 2026 | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ |
| AgentThreatBench (UK AISI) | https://ukgovernmentbeis.github.io/inspect_evals/evals/safeguards/agent_threat_bench/ |
| Singapore AI Governance for Agentic AI v1.0 | https://www.imda.gov.sg (Jan 2026) |
| Ox Security MCP RCE (CVE-2026-26015) | https://labs.ox.security (research report) |
| Hermes Agent (Nous Research) | https://github.com/nousresearch/hermes |
| NemoClaw (NVIDIA) | https://github.com/NVIDIA/NemoClaw |
| OpenClaw + VirusTotal | https://openclaw.ai/blog/virustotal-partnership |
| ClawHub SkillSpector (NVIDIA) | https://hub.openclaw.ai/ |
| ZClawBench (Zhipu AI) | https://huggingface.co/datasets/zai-org/ZClawBench |
| CVE-Bench (NIST CAISI) | https://github.com/usnistgov/caisi-cyber-evals |
| Trent AI ($13M for agent security) | https://trent.ai |
| Giskard red teaming platform | https://docs.giskard.ai |

---

## 6. Non-Goals (Explicitly Out of Scope)

- Replacing OpenClaw itself (NEXUSCLAW is a governance wrapper, not a fork)
- Supporting OpenAI models in NemoClaw sandboxes (NVIDIA limitation)
- Writing a new sandbox from scratch (adopt Hermes Docker / OpenShell / Cloudflare)
- Cryptographic VAP or formal ASBOM maturity claims until locally verified
- Fine-tuning or uncensoring models (rejected in NEXUS OS P0)
- Broad git operations without review (per AGENTS.md)
