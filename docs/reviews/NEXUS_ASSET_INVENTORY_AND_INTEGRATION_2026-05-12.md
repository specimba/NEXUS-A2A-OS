# NEXUS OS — Complete Asset Inventory & Integration Map

**Date:** 2026-05-12  
**Classification:** Internal — R&D Backend Team  
**Umbrella:** DoppleGround  
**Architect:** Speci (R&D Lead)  

> *"Our edges define us. Every service, every protocol, every agent — if it is not novel inside, it is a tool outside. The value is in the governance, not the transport."*

---

## SECTION 1: KAFKA BRIDGE — OPTION B CONFIRMED

**Decision:** Option B — Migrate to NEXUS-native config.

| Action | Status | Notes |
|--------|--------|-------|
| Bridge running | ✅ | `nexus-kafka-bridge` Up 18+ hours |
| API key secure | ✅ | No commits, no outside exposure during conversations |
| Rotation needed? | ❌ | Not urgent. Skip for now. |
| Gordon dependency? | ❌ | Gordon is support infrastructure, not active agent. We own the config. |
| Next: NEXUS-native control | ⏳ | `docker-compose-kafka-bridge.yml` already has the sed fix. No further action needed unless topics need reconfiguration. |

---

## SECTION 2: THE NOVELTY QUESTION — DoppleGround vs Empty Imitation

### The Concern (Validated)
> *"If A2A/MCP/ACP makes us imitators or locks us into enterprise companies, we should consider novel approaches under DoppleGround."*

### The Reality
**Critical finding from deep research:** IBM's ACP has been merged into Google's A2A under the Linux Foundation. The protocol war is over.

```
MCP (Anthropic) → Linux Foundation AAIF  → TOOL LAYER (agent ↔ tools)
A2A (Google)    → Linux Foundation AAIF  → AGENT LAYER (agent ↔ agent)
  └── ACP (IBM/BeeAI) → MERGED INTO A2A (March 2026)
ACP no longer exists as a separate protocol — it is now part of A2A.
Your concern about "OpenACP" is already resolved by convergence.
```

### Why This Does NOT Make Us Imitators

| Argument | Response |
|----------|----------|
| "A2A is Google's protocol" | Donated to Linux Foundation. Google, IBM, Microsoft, Salesforce, AWS, OpenAI, Anthropic — ALL co-govern it. No single vendor controls it. |
| "MCP is Anthropic's" | Same — Linux Foundation AAIF. 97M monthly SDK downloads. Open standard. |
| "Using them makes us dependent" | These are transport protocols, like HTTP. Using TCP/IP doesn't make every website an "imitator of DARPA." |
| "But the value is in what we build on top" | **THIS IS THE KEY.** NEXUS OS's value is: |

### Where NEXUS/DoppleGround Is Novel

```
Protocols (MCP/A2A/Tailscale) ── commodities, like TCP/IP
         │
         ▼
NEXUS Governance Layer ── KAIJU, VAP, TokenGuard ── UNIQUE
         │
         ▼
Sandbox Architecture ── Multi-tier, pluggable, disposable ── UNIQUE
         │
         ▼
TWAVE/QWAVE/CHIMERA ── Novel inference algorithms ── UNIQUE
         │
         ▼
Hallucination Detection ── 3-layer, KAIJU-integrated ── UNIQUE
         │
         ▼
Cross-Agent Security ── TerminalSanitizer, PTY, content integrity ── UNIQUE
```

**DoppleGround is not a protocol company. DoppleGround is a governance company.** The protocols are the roads; the governance is the traffic control system.

### What If Enterprise Black-Box Lock Happens?

| Scenario | Mitigation |
|----------|------------|
| Microsoft/Azure changes Foundry terms | All A2A/MCP are open standards. Switch to self-hosted A2A server. No lock-in. |
| Google changes A2A licensing | Linux Foundation governance prevents unilateral changes. Fork if needed. |
| Anthropic monetizes MCP | Same — open standard under LF. Community would fork. |

All protocols are under Linux Foundation. You cannot be locked into a Linux Foundation standard. The foundation's charter prevents it.

---

## SECTION 3: THE THREE CLAWS REDESIGNED

Updated with your new categorization:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOPPLEGROUND UMBRELLA                        │
│              (Governance, Novelty, SoT, IP)                     │
└─────────────────────────────────────────────────────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  A-LOCAL CLAW    │   │  B-ZO CLAW      │   │  C-KILOCLAW     │
│  (auto-claw)     │   │  (Cloud)        │   │  (Experimental) │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ Platform:       │   │ Platform:       │   │ Platform:       │
│ Local NEXUS     │   │ Zo Computer     │   │ Kilo AI / Cloud │
│ Windows + WSL2  │   │ OpenClaw        │   │ 1-week trial    │
│ Docker sandbox  │   │ Tailscale mesh  │   │ HF sandbox      │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ Purpose:        │   │ Purpose:        │   │ Purpose:        │
│ Daily ops       │   │ Orchestration   │   │ Experimental    │
│ Code review     │   │ Task routing    │   │ Aggressive R&D  │
│ Sandbox exec    │   │ User interface  │   │ New knowledge   │
│ Governance      │   │ Slack/Telegram  │   │ Chimera testing │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ Memory:         │   │ Memory:         │   │ Memory:         │
│ Mem0 + Vault    │   │ Zilliz (COLD)   │   │ Pinecone        │
│ Zilliz (HOT)    │   │ Notion AI       │   │ Bitdeer KB      │
│ Fly.io Redis    │   │ Pinecone        │   │ (ephemeral)     │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ Models:         │   │ Models:         │   │ Models:         │
│ Azure Gateway   │   │ OpenClaw models │   │ Kilo AI         │
│ Local GMR       │   │ Zo native       │   │ All Azure       │
│ Foundry agents  │   │ Azure fallback  │   │ GPT-5, Grok-4   │
├─────────────────┤   ├─────────────────┤   ├─────────────────┤
│ Crew:           │   │ Crew:           │   │ Crew:           │
│ OsmanClaw?-1    │   │ OsmanClaw?-2    │   │ OsmanClaw?-3    │
│ (auto-claw)     │   │ (zo-claw)       │   │ (kilo-claw)     │
│ Hermes swarm    │   │ Notion AI Opus  │   │ Hyperbrowser    │
│ 3 Horsemen      │   │ 4.7 (unlimited) │   │ Bitdeer         │
│ (Foundry)       │   │ Composio trig.  │   │ Pinecone        │
│                 │   │                 │   │ (GPT-5)         │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

### A-LOCAL CLAW (auto-claw) — Daily Operations

| Component | What | Status |
|-----------|------|--------|
| **KAIJU Governor** | 5-stage authorization gate | ✅ Built |
| **VAP Chain** | SHA-256 audit trail | ✅ Built |
| **TokenGuard** | 3-tier token budget | ✅ Built |
| **Vault** | 5-track truth engine | ✅ Built |
| **TerminalSanitizer** | Cross-agent injection defense | ✅ Phase 0 |
| **VerifiableOutput** | SHA-256 content integrity | ✅ Phase 0 |
| **GMR Router** | Genius Model Rotator | ✅ Built |
| **Sandbox Abstraction** | Docker/Podman/WSL/OpenShell | ⏳ Phase 1 |
| **Kafka Bridge** | PostgreSQL → Confluent Cloud | ✅ Running |
| **Mem0** | Agent memory layer | ⏳ Integrate |
| **Fly.io Redis** | KV cache + session state | ✅ Running (redis://...) |

**Crew:**
- `OsmanClaw?-1` — Daily ops orchestrator, code review coordinator
- Hermes Swarm Pack agents (from QWENcoder branch)
- 3 Foundry Horsemen (not yet activated)

### B-ZO CLAW (zo-claw) — Cloud Orchestration

| Component | What | Status |
|-----------|------|--------|
| **Zo Computer** | Orchestrator brain | ✅ Active |
| **OpenClaw** | Agent runtime on Zo | ⏳ Install |
| **Tailscale** | Mesh network (v1.96.4 on Zo) | ⏳ Configure |
| **Slack Bot Network** | 14 bots, 6 channels | ⏳ Phase 2 |
| **MCP via mcporter** | Tool bridge to Local | ⏳ Phase 2 |
| **A2A Protocol** | Agent-to-agent communication | ⏳ Phase 3 |
| **Notion AI Opus 4.7** | Unlimited, Slack-connected, task execution | ✅ FREE |
| **Composio Triggers** | GitHub/Gmail/Slack event pipeline | ⏳ Phase 2 |

**Notion AI Agent — Critical Asset:**
```
Status: ✅ Connected to Slack, triggered by email/comments
Model: Opus 4.7 (free, unlimited until Jun 3)
Capabilities:
  - Morning briefs (Linear + Sentry + Notion + Calendar)
  - Email triage and drafting
  - Task execution (uv.lock fix example: triage → create Linear → comment)
  - Already integrated with your personal mail + Slack triggers
  - Full Notion workspace + Linear + Sentry access

This is your most powerful active agent RIGHT NOW.
```

**Composio Triggers — Event Pipeline:**
```python
# Already works — trigger GitHub events, route via Composio
trigger = composio.triggers.create(
    slug="GITHUB_COMMIT_EVENT",
    user_id="speci",
    trigger_config={"owner": "specimba", "repo": "hermes-agent"},
)
# Events → webhook → process → Slack notification
```

### C-KILOCLAW (kilo-claw) — Experimental Laboratory

| Component | What | Status |
|-----------|------|--------|
| **Kilo AI** | Cloud API access | ✅ Available |
| **Pinecone** | $297 credit, 18 days, GPT-5, assistant "pineosman" | ✅ FREE |
| **Bitdeer** | NEXUS KB uploaded as assistant | ✅ Ready |
| **Hyperbrowser** | Browser automation for agents | ✅ Available |
| **HF Dataset** | `specimba/chimera-v0.1.0` | ✅ Published |
| **OpenClaw-Fly-Deploy** | Deployment template | ✅ GitHub |
| **Hermes-Flyio** | Deployment template | ✅ GitHub |

**Pinecone — The "PineOsman" Assistant:**
```
Assistant Name: pineosman
Base URL: https://prod-eu-data.ke.pinecone.io
MCP: https://prod-eu-data.ke.pinecone.io/mcp/assistants/pineosman
Model: GPT-5 (configurable)
Custom Instructions: Loaded with full NEXUS OS architecture context
Credit: $297 remaining, 18 days trial
Features: File upload, chat, evaluation, RBAC, backups, bulk import
```

**Bitdeer — NEXUS Knowledge Base:**
```
Agent ID: ag_01krg1jwyke5ebg9vznv5vk5dm
Task ID: tk_01krg1ka0keb1sgvgqn1e83ssn
Usage: Direct API calls for KB queries
```

---

## SECTION 4: ALL AVAILABLE RESOURCES — MASTER TABLE

### Infrastructure

| Resource | Status | Credentials | Purpose |
|----------|--------|-------------|---------|
| **Azure AI Gateway** | ✅ Online | `nexus-os-gateway.azure-api.net` | Model routing, quotas, governance |
| **Azure Foundry** | ✅ Active | `rg-OSMANclaw2`, Sweden Central | Agent deployment, A2A tool |
| **Azure Models** | ✅ Deployed | 13+ models (Claude Opus 4.7, DeepSeek R1, V4 Flash, GPT-4.1, GPT-5.4, Grok-4, Kimi K2.6, etc.) | Inference |
| **Fly.io Redis** | ✅ Running | `redis://default:Abn4ACQgZjRkN...@127.0.0.1:16379` | KV cache, session state |
| **Tailscale** | ✅ Installed (Zo) | Needs auth key | Encrypted mesh network |
| **Docker Desktop** | ✅ Running | 25+ containers | Container orchestration |

### Vector Memory / Knowledge

| Resource | Status | Credit | Purpose |
|----------|--------|--------|---------|
| **Pinecone** | ✅ Active | $297 / 18 days | Vector DB + Assistant + MCP |
| **Mem0** | ✅ Registered | 10K requests / month Hobby | Agent memory layer |
| **Zilliz (HOT)** | ✅ Active | From swarm pack | Events, failures |
| **Zilliz (COLD)** | ✅ Active | From swarm pack | Trust, governance |
| **Bitdeer** | ✅ Ready | NEXUS KB uploaded | Knowledge base assistant |

### Agent Services

| Resource | Status | Cost | Purpose |
|----------|--------|------|---------|
| **Notion AI Opus 4.7** | ✅ FREE | Unlimited until Jun 3 | Task execution, triage, briefs |
| **Zo Computer** | ✅ Active | Subscription | Orchestrator, chat host |
| **OpenClaw** | ⏳ Install | Free, open-source | Agent runtime on Zo |
| **Composio** | ✅ Ready | SDK installed | Event triggers, tool integration |
| **Hyperbrowser** | ✅ Available | Browser automation | Agent browsing, scraping |
| **Foundry Agents** | ⏳ Not active | Azure subscription | 3 Horsemen strategy |

### Repositories & Code

| Resource | Branch | Purpose |
|----------|--------|---------|
| `specimba/nexusalpha` | main | Main NEXUS OS |
| `specimba/hermes-agent` | QWENcoder | Swarm pack + Gastown |
| `specimba/hermes-flyio` | main | Fly.io deployment template |
| `specimba/Openclaw-Fly-Deploy` | main | OpenClaw on Fly.io |
| `specimba/nexusdashboards` | main | Dashboard UI |
| `specimba/NEXUS-A2A-OS` | main | Public A2A reference |
| `specimba/slack-agent-template` | main | Slack bot template |
| `specimba/NEO-agent` | main | NEO agent |
| `specimba/ISC-Bench` | main | ISC benchmark |
| `specimba/mimo25-nexus` | mimo25-nexus-branch | Mimo25 bridge |
| `specimba/chimera-v0.1.0` | HF dataset | Chimera R&D dataset |

---

## SECTION 5: UPDATED PROTOCOL STACK (With OpenACP Correction)

### What Changed vs Previous Plan

| Layer | Previous Plan | Corrected |
|-------|--------------|-----------|
| L3: Agent Comm | A2A Protocol only | **A2A Protocol (which now includes ACP)** |
| Licensing Concern | Not addressed | **All protocols under Linux Foundation. No lock-in possible.** |
| Novelty Defense | Not addressed | **DoppleGround = governance, not transport. Protocols are commodities.** |

### The Corrected Stack

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: DOPPLEGROUND GOVERNANCE (UNIQUE/NOVEL)               │
│  KAIJU, VAP, TokenGuard, TWAVE/QWAVE/CHIMERA                   │
│  Hallucination Detection, Cross-Agent Security                  │
│  ── This is where all the value lives ──                       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: A2A + ACP (Linux Foundation AAIF)                    │
│  (ACP merged into A2A as of March 2026)                        │
│  Agent-to-agent task delegation, discovery, session management  │
│  ── Open standard, no vendor lock-in ──                       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: MCP (Linux Foundation AAIF)                          │
│  Agent-to-tool connectivity via mcporter                        │
│  ── Open standard, 97M monthly downloads ──                   │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: TAILSCALE (WireGuard)                                │
│  Encrypted mesh network                                         │
│  ── Open protocol, zero-config ──                              │
└─────────────────────────────────────────────────────────────────┘
```

**Key correction acknowledged:** OpenACP is not missing — it is now PART of A2A. The IBM BeeAI team contributed ACP to the Linux Foundation A2A project in March 2026. ACP's concepts (capability tokens, local-first discovery, REST-native transport) are now part of A2A v1.0.

---

## SECTION 6: THE 3 HORSEMEN STRATEGY (Foundry Agents)

Your 3 Foundry horsemen — not yet activated. Here's how they fit:

| Horseman | Foundry Agent | Deployed Model | Role |
|----------|--------------|----------------|------|
| **Horseman 1** | Code Review Agent | `gpt-4.1` or `DeepSeek-V4-Flash` | Automated PR analysis via A2A tool |
| **Horseman 2** | Security Scan Agent | `Claude Opus 4.7` | Vulnerability detection, compliance |
| **Horseman 3** | Architecture Agent | `Grok-4-1-fast-reasoning` | Design review, pattern detection |

Integration path (from Microsoft Foundry docs):
```python
# Each horseman exposes an A2A endpoint
# Other agents connect via A2A tool
from azure.ai.projects.models import A2APreviewTool

tool = A2APreviewTool(
    project_connection_id=connection_id,
    # Exposes agent card at /.well-known/agent-card.json
)
```

All 3 connect to the Azure AI Gateway (`nexus-os-gateway.azure-api.net`) for centralized quota management, monitoring, and routing.

---

## SECTION 7: RESOURCE ALLOCATION MAP

| Service | Assigned To | Purpose |
|---------|-------------|---------|
| **Pinecone ($297)** | C-KILOCLAW | Experimental KB, Chimera testing, GPT-5 assistant |
| **Notion AI (Free)** | B-ZO CLAW | Daily ops, task execution, email triage |
| **Mem0 (Hobby)** | A-LOCAL CLAW | Agent memory persistence |
| **Bitdeer** | C-KILOCLAW | NEXUS KB queries |
| **Compsoio** | B-ZO CLAW | Event triggers → auto-routing |
| **Hyperbrowser** | C-KILOCLAW | Web research automation |
| **Fly.io Redis** | A-LOCAL CLAW | KV cache, session state |
| **Azure Gateway** | ALL | Model routing, quota mgmt |
| **Zilliz HOT** | A-LOCAL CLAW | Event/failure vectors |
| **Zilliz COLD** | B-ZO CLAW | Trust/governance vectors |

---

## SECTION 8: UPDATED PRIORITIES

### P0 — This Week
| # | Task | Assign |
|---|------|--------|
| 0.1 | Give zip password for Zo grounding | User |
| 0.2 | Tailscale install on Windows + Zo tailnet join | User + Zo |
| 0.3 | Option B: confirm bridge config finalized | User |

### P1 — Week 1
| # | Task | Detail |
|---|------|--------|
| 1.1 | Install OpenClaw on Zo | Per Zo chat instructions |
| 1.2 | Create 3 OsmanClaw? agents in OpenClaw | Local, Zo, Kilo profiles |
| 1.3 | Wire Notion AI Opus 4.7 into B-ZO CLAW | Already Slack-connected, add task routing |
| 1.4 | Compsoio triggers for GitHub events | PRs, issues, commits |

### P2 — Week 2
| # | Task | Detail |
|---|------|--------|
| 2.1 | MCP server on Local NEXUS (KAIJU/VAP tools) | Expose governance as MCP tools |
| 2.2 | Tailscale mesh fully operational | Zo ↔ Local ↔ any future nodes |
| 2.3 | A2A bridge between Zo and Local | Agent cards, task delegation |

### P3 — Week 3-4
| # | Task | Detail |
|---|------|--------|
| 3.1 | Activate 3 Foundry horsemen | Deploy as A2A endpoints |
| 3.2 | Pinecone assistant integration with C-KILOCLAW | GPT-5 with NEXUS KB |
| 3.3 | Hyperbrowser for web research | C-KILOCLAW research automation |
| 3.4 | Mem0 integration with Vault | Unified memory layer |
| 3.5 | Hermes swarm pack → NEXUS main merge | Import sandbox policies |

---

## SECTION 9: ON THE NOVELTY QUESTION — FINAL WORD

> *"The difference between imitation and innovation is not what protocols you use, but what you do that no protocol can describe."*

**DoppleGround is not:**
- A protocol company
- An enterprise tool reseller
- An imitator of Google/Microsoft/Anthropic

**DoppleGround is:**
- A governance company
- A security company for autonomous AI
- The layer that makes multi-agent systems auditable, controllable, and safe

**Proof:** A2A describes how agents send messages. MCP describes how agents call tools. Neither describes how to:
- Prevent cross-agent injection (TerminalSanitizer) ← NEXUS unique
- Detect hallucinations across agent outputs ← NEXUS unique
- Govern trust scores with crypto-anchored VAP chains ← NEXUS unique
- Route inference through TWAVE/QWAVE/CHIMERA ← NEXUS unique
- Execute agents in disposable sandboxes with KAIJU gates ← NEXUS unique

THIS is DoppleGround. The protocols are just roads. We own the traffic system.

---

*Document: NEXUS_ASSET_INVENTORY_AND_INTEGRATION_2026-05-12.md*  
*Next update: After Zo grounding + Tailscale setup*
