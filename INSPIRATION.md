# NEXUS OS — Inspiration Research
Synthesized from 25 sourced files + 297 GitHub stars + team reports. Updated: 2026-04-20.

---

## Architecture Map: What We Have vs What We Build

### Built (operational)
- NEXUS OS v3.0 (8/8 tests PASS) — `Skills/nexus-os/`
- GMR with Zo model stack (MiniMax m2.7 primary, 4 free-tier sub-agents via `/zo/ask`)
- Heartbeat protocol — sub-agent lifecycle + token enforcement
- AGENTS.md root memory — identity, governance, system spec
- Zo Computer as orchestrator (4GB RAM, 3 cores, Python 3.12, Node 22, Bun, DuckDB 1.4.2)

### Built (installed, curated)
- `zopenclaw` — OpenClaw + Tailscale + mcporter bridge
- `context7` — version-specific library docs
- `self-improvement` — weekly reflection audit
- `handoff` — pause/resume across conversations
- `journal` — daily experiential logging
- `simplify` — code refinement
- `mcporter-setup` — MCP server integration
- `share-skill` — skill contribution prep

---

## Core Inspiration Sources (ranked by build priority)

### P0 — Build Now

**ISC-Bench (wuyoscar/ISC-Bench)** — 0.97
- 84 TVD templates across 9 domains. TVD = Task-Validator-Data. Failure = when a legitimate workflow *structurally requires* harmful output to pass validation.
- Steal: TVD template format + dual-cascade runner (commercial vs heretic control group) + VAP logging.
- Build: `Skills/nexus-os/src/nexus_os/stresslab/` — adapt ISC runner to Zo sub-agents via `/zo/ask`.

**OR-Bench (ArXiv 2405.20947)** — 0.95
- 80k prompts, 10 rejection categories. Most models trade safety for over-refusal (Spearman 0.89).
- Steal: Lane threshold calibration methodology. Update trust_scoring lane thresholds (research 0.3→0.35, audit 0.7→0.72) based on OR-Bench data.
- Build: `Skills/nexus-os/src/nexus_os/governor/trust_scoring.py` update.

**deer-flow (bytedance/deer-flow)** — 0.93
- Lead agent + parallel workers + isolated sandboxes + memory. Scales sub-agent orchestration.
- Steal: Harness topology — lead spawns bounded workers, each in isolated workspace.
- Build: `Skills/nexus-os/src/nexus_os/swarm/foreman.py` refactor.

**Adaptive Circuit Breaker (production Reddit)**
- CLOSED → OPEN → HALF_OPEN → test request → CLOSED or 2x backoff.
- Build: Upgrade `Skills/nexus-os/src/nexus_os/gmr/` circuit breaker to half-open with exponential backoff.

### P1 — Next Sprint

**RigorLLM + ShieldGemma + AEGIS**
- RigorLLM: KNN+LLM fusion guardrail. Resilient to jailbreaks.
- ShieldGemma-2B: +10.8% AU-PRC over Llama Guard. Fast pre-filter.
- AEGIS: 13 critical + 9 sparse risks. Ensemble scoring.
- Build: `Skills/nexus-os/src/nexus_os/governor/moderation.py` — fusion guardrail + ShieldGemma-2B gate + AEGIS taxonomy.

**Speculative Routing (ArXiv 2604.09213)**
- 1M-param proxy predicts best LLM before inference. 62% cost reduction, 2.1% quality loss.
- Use Zo's fast MiniMax as the proxy router.
- Build: `Skills/nexus-os/src/nexus_os/gmr/` — add fast proxy classifier for pre-routing.

**AutoSkill Forge (princeton-nlp/AutoSkillForge)**
- Task success rate > threshold → auto-register SkillRecord. Next similar task → skill fast-path.
- Build: `Skills/nexus-os/skillsmith/` — add auto_register() monitoring loop.

### P2 — Research

- SuperLocalMemory v2 (HuggingFace Apr 2026): 8-channel memory + TEMPORAL_CAUSAL channel 7 (patch lineage tracking)
- KV cache compression: 8.3x compression, 0.3% quality loss
- Auction-based swarm allocation: bid formula replaces round-robin
- MCP-Auth in bridge

---

## GitHub Stars — Key Integrations (from 297-repo scan)

| Repo | Stars | Integration |
|------|-------|------------|
| BerriAI/litellm | 19k | Provider mesh / free pool |
| google/adk-python | 19k | Sub-agent evaluation loops |
| secure-hulk | — | MCP security scanning |
| Qwen-Agent | 16k | MCP memory/sandbox |
| RelayFreeLLM | — | Session affinity / failover |
| magpie | — | Synthetic regression data |
| awesome-free-llm-apis repos | — | Free endpoint discovery |

---

## Governance Limits
- Sub-agents/hr: 5
- API calls/session: 20
- Concurrent: 2 max
- File writes/session: 30
- Loop detection: 3x same action → STOP

## Testing Mandate
- NO local model testing — cannot verify censorship state
- Commercial endpoints via free API routes only
- Heretic (decensored) = control group
- Dual cascade: Route 1 = TokenGuard-tracked Zo calls, Route 2 = heretic baseline

## mail.tm Email Pipeline (for research endpoint acquisition)
```
POST https://api.mail.tm/accounts  {"address":"addr","password":"pass"}
POST https://api.mail.tm/token
GET  https://api.mail.tm/messages
# Max 5 signups/hour, 20/day
```
