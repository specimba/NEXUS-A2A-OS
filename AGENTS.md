# AGENTS.md — NEXUS OS Orchestration Layer (Zo-side)

## Role

Zo is the primary NEXUS OS orchestrator node. All coordination flows through Zo's infrastructure:
webhooks, scheduled agents, Slack/Telegram bindings, Kafka event bus, vector knowledge base.

## System Architecture

```
External Events (GitHub, Slack, Telegram)
        │
        ▼
  ┌──────────────────┐
  │  Zo Computer      │  ← You are here
  │  (Orchestrator)   │
  └───────┬──────────┘
          │
  ┌───────┴───────┬──────────────┬──────────────────┐
  ▼               ▼              ▼                  ▼
Webhooks      Scheduled        Kafka            Knowledge
(dispatch)    Agents          Bridge            Base
/api/         (6 agents)   (localhost:8799)    Pinecone
bot-dispatch                           │        (KB linked)
                                      ▼
                               Redis (localhost:6379)
```

## PR Lifecycle (Complete Pipeline)

```
GitHub Event (PR opened / check_run / push)
        │
        ▼
┌─────────────────────────────────────┐
│  zo.space /api/github-webhook       │ ← HMAC verified
│  (thin — returns 200 immediately)   │
└────────────┬────────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌──────────┐  ┌──────────────┐
│ Slack    │  │ Zo session   │ ← via local MCP or zo/ask API
│ notify   │  │ (child Zo)   │
└──────────┘  └──────┬───────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌──────────────────┐  ┌─────────────────────┐
│ gh pr diff       │  │ code-degunker       │
│ GitHub CLI diff  │  │ 27 anti-patterns    │
└────────┬─────────┘  └──────────┬──────────┘
         └───────────┬───────────┘
                     ▼
            ┌─────────────────┐
            │ Synthesize      │
            │ verdict +       │
            │ inline review   │
            └────────┬────────┘
                     ▼
            ┌──────────────────┐
            │ gh pr review     │ ← inline comments on PR
            │ --comment/       │
            │ --approve/       │
            │ --request-changes│
            └────────┬─────────┘
                     ▼
            ┌──────────────────────┐
            │ Slack dispatch       │
            │ (domain-structured)  │
            └────────┬─────────────┘
                     │
         ┌───────────┴─────────────┐
         ▼                         ▼
┌────────────────┐      ┌──────────────────┐
│ Bots respond   │      │ PR Watcher       │
│ in thread      │      │ (every 2 min)    │
│ (async)        │      │ collects +       │
└───────┬────────┘      │ synthesizes      │
        │               └────────┬─────────┘
        └───────────┬────────────┘
                    ▼
           ┌─────────────────┐
           │ All feedback    │
           │ consolidated    │
           └────────┬────────┘
                    ▼
           ┌─────────────────┐
           │ gh pr merge     │ ← auto-merge if clean
           │ --squash        │
           └─────────────────┘
```

## Agent Fleet (updated 2026-05-15)

| Agent | Interval | Channel | Purpose |
|-------|----------|---------|---------|
| **NEXUS PR Orchestrator** | Every 2 min | #nexus-reviews | Complete PR pipeline: scan → review → dispatch bots → collect → synthesize → merge |
| Model Syncer | Every 6 hours | #nexus-reviews | Reviews stale/unreviewed PRs |
| Brainstormer | Weekly (Sun) | #nexus-reviews | Synthesizes ideas + research |
| KiloClaw-REBORN | Every 12 hours | #nexus-autoclaw | Deep intelligence + research |

## Expertise Map (Bot Routing)

| Domain | Bots | Channel | Priority |
|--------|------|---------|----------|
| Security | @Kilo @HCP Vault Radar | #nexus-ops | P1 |
| Code Quality | @Devin @Codex | #nexus-codex-tasks | P2 |
| Architecture | @Macroscope | #nexus-research | P2 |
| Operations | @Computer @incident | #nexus-ops | P2 |
| Design | @Adobe Express | #nexus-codex-tasks | P3 |
| Research | @Q @mavisassist | #nexus-research | P3 |
| Documentation | @Notion AI @Confluence | #nexus-research | P4 |
| Project | @Jira @Coda | #nexus-control | P5 |

## Deployed Routes (all public API)

| Route | What | Links to |
|-------|------|----------|
| `POST /api/github-webhook` | PR/issue/check event receiver → Slack + Zo + Redis | Local MCP for Zo dispatch |
| `POST /api/bot-dispatch` | Domain-expertise bot routing to Slack | Skills map + Kafka |
| `POST /api/nexus-mcp` | 10-tool MCP server | Hyperbrowser, Kafka, Slack, Pinecone, GitHub, Zo |
| `POST /api/telegram-webhook` | Telegram → Slack bridge | Gateway disabled |
| `POST /api/modelrelay` | Model routing for agents | Internal |
| `/callback` | GitHub OAuth callback | Private |
| `/redirection` | URL redirection service | Private |

## Infrastructure Running

| Service | Status | Endpoint |
|---------|--------|----------|
| Kafka bridge | ✅ Active | localhost:8799 |
| Redis | ✅ Active | localhost:6379 |
| Telegram gateway | ⛔ Stopped (intentional) | — |
| OpenClaw | ✅ Running | gateway + control-ui |
| Tailscale | ✅ Running | Connected |
| DoppelGround | ✅ Published | HTTPS service |

## Active Repos (NEXUS mesh)

| Repo | Purpose | Status |
|------|---------|--------|
| `specimba/nexusalpha` | Main NEXUS OS monorepo | Active (11 branches) |
| `specimba/DoppelGround` | Company landing page + dashboard | 🚀 Published |
| `specimba/underground-network` | Core networking | Active |
| `specimba/DoppelGanger` | Product mirror | Active |
| `specimba/NEO-agent` | Agent framework | Active |
| `specimba/ROMA` | Agent system | Active |
| `specimba/terminal-dashboards` | Terminal UI | Active |
| `specimba/layerscape` | Landscape system | Active |

## Scheduled Agent Fleet

| Agent | Interval | Channel | Purpose | Status |
|-------|----------|---------|---------|--------|
| PR Watcher | Every 15 min | #nexus-reviews | Checks all repos for new PRs | ✅ Live |
| Model Syncer | Every 6 hours | #nexus-reviews | Reviews stale/unreviewed PRs | ✅ Live |
| Brainstormer | Weekly (Sun) | #nexus-reviews | Synthesizes ideas + research | ✅ Live |
| KiloClaw-REBORN | Every 12 hours | #nexus-autoclaw | Deep intelligence + research | ✅ Live |

## Published Sites

| Site | URL | Purpose |
|------|-----|---------|
| **DoppelGround** | https://doppelground-specimba.zocomputer.io | Company landing page + NEXUS dashboard |
| **specimba.zo.space** | https://specimba.zo.space | Zo managed space (webhooks, MCP, relay) |

## Zo Space API Routes

| Route | Purpose | Auth |
|-------|---------|------|
| `POST /api/github-webhook` | GitHub event receiver (PR, push, issues) | HMAC-SHA256 verified |
| `POST /api/bot-dispatch` | Routes tasks to appropriate agent/Zo | SLACK_BOT_TOKEN |
| `POST /api/telegram-webhook` | Telegram update receiver | None (bot token gated) |
| `POST /api/nexus-mcp` | MCP tool server (hyperbrowser, kafka, slack, pinecone) | Bearer token |
| `POST /api/modelrelay` | Model relay for agent coordination | Internal |
| `/callback` | GitHub OAuth callback | Private |
| `/redirection` | URL redirection service | Private |

## Active Pipelines (deployed 2026-05-15)

### PR Auto-Review (`autoReviewPR`)
- Trigger: `pull_request` opened (non-draft)
- Flow: Zo receives prompt → `gh pr diff` fetches diff → code-degunker analysis (27 anti-patterns) → `gh pr review --comment` posts inline review → approve/request-changes → summary to #nexus-reviews
- Also tags @Devin @Kilo @Codex in Slack on open

### Issue Auto-Triage (`autoTriageIssue`)
- Trigger: `issues` opened
- Flow: Zo classifies → `[BUG|FEATURE|QUESTION|DOCS] - [p0|p1|p2|p3]`
- Result logged; used for routing to #nexus-research

### Auto-Merge (`autoMergeIfReady`)
- Trigger: `check_run` / `check_suite` with `conclusion=success`
- Flow: Zo checks `mergeStateStatus` + review decision → if CLEAN + APPROVED → `gh pr merge --squash` → confirmation to #nexus-reviews

### CI Self-Heal (`ciSelfHeal`)
- Trigger: `check_run` / `check_suite` with `conclusion=failure`
- Flow: Zo fetches action run logs → diagnoses → posts to #nexus-ops tagging @Devin @Pylon

### Infrastructure Status
| Component | Status | Notes |
|-----------|--------|-------|
| Telegram gateway | Stopped | Intentionally disabled ("spamming gateway disabled") |
| Kafka bridge | ✅ Running | Registered service, replies on :8799 |
| Redis | ✅ Running | Registered service, localhost:6379 |
| OpenClaw | ✅ Running | gateway + control-ui |
| Tailscale | ✅ Running | Connected |
| DoppelGround | ✅ Running | Published HTTP service |

### Secrets Status
- ✅ SLACK_BOT_TOKEN — set, used by sendSlack for direct Slack posting
- ✅ GITHUB_TOKEN — set, used by gh CLI and auto-review pipelines
- ✅ GITHUB_WEBHOOK_SECRET — set, HMAC verification active
- ✅ HYPERBROWSER_KEY — set, MCP hyperbrowser tools active
- ✅ PINECONE_API_KEY — set, vector queries work
- ✅ CONFLUENT_KEY + SECRET — set, bridge configured
- ✅ REDIS_DATA_ACCESSCONT_PASS — set, redis secured
- ✅ AUTOCLAW_BOT_TOKEN + KILOCLAW_BOT_TOKEN — set, gateway configured
- ❌ ZO_API_KEY — NOT set. sendSlack uses SLACK_BOT_TOKEN (direct) which works, but Zo API fallback path is unavailable

## NEXUS OS Safety Layer (merged 2026-05-18)

Codex's safety consolidation from `github/main` has been merged into `canonical-617`. All modules live under `src/nexus_os/`:

| Module | Path | Purpose |
|--------|------|---------|
| Security Sanitizer | `src/nexus_os/security/sanitizer.py` | Prompt injection + ANSI escape filtering |
| Token Policy | `src/nexus_os/monitoring/token_policy.py` | Rate limiting, budget enforcement |
| Token Guard | `src/nexus_os/monitoring/token_guard.py` | Runtime token tracking + hard stops |
| Memory Adapter | `src/nexus_os/vault/memory_adapter.py` | Trust-scored memory with layer promotion |
| Trust Kernel v2 | `src/nexus_os/governor/trust_kernel.py` | CDR-stage trust decisions |
| Trust Engine v2 | `src/nexus_os/governor/trust_engine_v2.py` | Contain→Detect→Respond state machine |
| Proof Chain | `src/nexus_os/governor/proof_chain.py` | VAP chain, tamper detection |
| Compliance | `src/nexus_os/governor/compliance.py` | Policy enforcement |
| Kaiju Auth | `src/nexus_os/governor/kaiju_auth.py` | Impact/intent auth with hold queue |
| MCP Server | `src/nexus_os/mcp/server.py` | NexusGovernanceMCP |
| FunctionGemma Router | `src/nexus_os/mcp/functiongemma_router.py` | Intent classifier for function calling |

**Test baseline: 634 passed, 0 failures.**

## NEXUS-OS Package v3.0

The complete system is now packaged at `file 'NEXUS-OS/'` with 17 files:

```
NEXUS-OS/
├── package.json           # Manifest with version, deps, metadata
├── README.md              # Full docs + architecture diagram
├── bootstrap.sh           # One-shot installer with health checks
├── env.template           # All secrets documented
├── config/
│   ├── agents.json        # 4 scheduled agents
│   ├── services.json      # 3 managed services
│   └── secrets-map.json   # Secret-to-component mapping
├── zo/routes/
│   ├── manifest.json
│   ├── github-webhook.ts / bot-dispatch.ts
│   ├── telegram-webhook.ts / nexus-mcp.ts
│   └── callback.tsx / redirection.tsx
├── skills/hyperbrowser-reference.md
├── infra/
│   ├── kafka_bridge.py    # Confluent-ready event bridge
│   └── redis.conf         # Local Redis config
└── knowledge/
    └── nexus_kb.py        # Pinecone + Redis knowledge manager
```

**Deploy commands:**
- `bash NEXUS-OS/bootstrap.sh` — install deps, check health
- Routes: deploy each `zo/routes/*.ts` file via Zo chat
- Agents: create from `config/agents.json` via Zo chat/yahoo
- Services: register from `config/services.json` via Zo chat

## Active Secrets (Settings → Advanced)

| Name | Used By | Status |
|------|---------|--------|
| `SLACK_BOT_TOKEN` | Slack API (post messages, read channels) | ✅ Set |
| `KILOCLAW_BOT_TOKEN` | KiloClaw Telegram bot | ✅ Set |
| `AUTOCLAW_BOT_TOKEN` | AutoClaw Telegram bot | ✅ Set |
| `GITHUB_TOKEN` | GitHub API (repos, PRs, branches) | ✅ Set |
| `CONFLUENT_KEY` | Kafka bridge (Confluent Cloud) | ✅ Set |
| `CONFLUENT_SECRET` | Kafka bridge auth | ✅ Set |
| `PINECONE_API_KEY` | Vector knowledge base | ✅ Set |
| `HYPERBROWSER_KEY` | Browser automation API | ✅ Set |
| `OPENROUTER_API_KEY` | AI model routing | ✅ Set (low credits) |
| `NEXUSCLOUD_ARCHIVE_PASS` | NEXUS archive extraction | ✅ Set |

## Environment

- **Hardware:** 3 vCPU, 4GB RAM, 80GB disk
- **OS:** Debian GNU/Linux 12 (bookworm)
- **Runtime:** Bun 1.3.11, Python 3.12, Redis 7.0.15
- **Zo Space:** bun + hono + tailwind + react
