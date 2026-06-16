---
id: NODE-MIG-NEXUS_CONNECTIVITY_REPORT
authority_scope: experimental
origin_sha256: 12bb0174944785e6161d8347a0a88906f7f06bda55cbba1060f5449cda738b03
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-456872
---
# NEXUS OS Connectivity & Multi-Agent MCP Strategy

**Date:** 2026-05-20
**Status:** Deep analysis complete

<!-- CANARY: a634098c2d13156a78b13b9c80d8f63f -->
---

## 1. Zo Computer MCP Analysis

Zo's MCP is **agent-native** — skills in `~/.grok/skills/` act as instruction layers, connectors (Notion, GitHub, Linear, ZAPII) are pre-built. Their Gradio 6.11.0 has native MCP server support (`gradio[mcp]==6.11.0`). 

**Problem:** "Our providers not working at there right now correctly" — your API keys configured on Zo are failing due to Zo's own auth/rate-limit layer.

**Zo can do:** Lightweight coordination MCP, skill orchestration, diagnostics
**Zo cannot do:** Heavy compute, reliable provider routing

---

## 2. Devin/Codex Corrections

**Got right:** TrustKernel (631 lines, real code), MCP auth scaffold, test monkeypatch fix, merge push to github/main

**Needs correction:**
1. Claimed "678 tests" — real count is **670** full suite
2. Pushed to github/main but it was a **skeleton branch** (only LICENSE + README), not the real code
3. Left dirty worktree (14 files uncommitted) — ground reports, handoff docs, pycache
4. PR `codex/specimba/1805mainSpeci → release/v3.1-dashboard` (+6354 -77) never reviewed
5. Grok skills are **instruction-only** — reference TrustKernel but have zero runtime connection
6. github/main is **NOT ahead** — it's behind. The real canonical branch is `codex/specimba/1805mainSpeci`

---

## 3. Always-Online MCP Server Recommendation

**Winner: HuggingFace Spaces** (not Zo, not local Docker alone)

| Option | Always-on? | GPU | MCP Native | Cost |
|--------|-----------|-----|-----------|------|
| Zo Computer | Yes | Unknown | Partial | Free |
| Local Docker | No (PC sleep) | RTX 4090 | Full control | Free |
| **HF Spaces** | **Yes** | **ZeroGPU free / T4 $0.40/hr** | **Gradio 6.11 built-in** | **Free CPU** |

**Hybrid 3-layer architecture:**
- Layer 1: **HF Space** (always-on MCP gateway — TrustKernel, memory, orchestrator tools)
- Layer 2: **Zo Computer** (coordination MCP — skills, connectors, diagnostics)
- Layer 3: **Local Docker** (heavy compute — Ollama, detectors, datasets)

---

## 4. Communication Layer Strategy

Six platforms, one bridge:

| Platform | Priority | Strategy |
|----------|----------|----------|
| **Slack** | P0 | Already have app + webhooks — wire to HF Space MCP |
| **Telegram** | P0 | Fix gateway spam, add MCP tool interface via `composio/telegram-mcp` |
| **ML-intern Kimi 2.6** | P1 | HF Inference API + Space sandbox — secret research power |
| **Notion/Claude Opus 4.7** | P1 | Currently wasted — expose action sandbox via Notion API + HF Space |
| **ChatGPT 5.5** | P2 | Share MCP spec, use as additional provider |
| **Meta Spark/OpenClaw** | P2 | Skill workaround until MCP support lands |

---

## 5. HF Space Goldmine

**You already have:**
- `specimba/sandbox-ef149183` (private, secrets set, Gradio MCP ready)
- `build-small-hackathon/GRM-2.6-Opus` (cloned with ZeroGPU access, 55GB model loads in 83s)
- `HF_TOKEN=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` (read+write)
- `nexus-os-v2/nexus_os_v2/` (26 real detector files, 4700 lines — NOT wired yet)
- `openenv/coding_env`, `terminus_env`, `tbench2` (free agentic environments)
- Community GPU grant available ("Apply for a community GPU grant" in Space settings)

**Every Gradio 6.11+ Space is an MCP server** — `GRADIO_MCP_SERVER=true` or `.launch(mcp_server=True)`.

---

## 6. Immediate Action Plan

### This Week
1. Commit/archive dirty worktree (14 files)
2. Merge PR: `codex/specimba/1805mainSpeci → release/v3.1-dashboard`, then `integration/new-main-2026-05-20`
3. Wire `nexus-os-v2` real detectors into main codebase (replace stubs)
4. Apply exponential backoff to AutoClaw (CLAW-02 rate limit fix)
5. Deploy HF Space MCP gateway with TrustKernel tools

### Next Week
6. Connect Slack app → HF Space MCP
7. Fix Telegram gateway → MCP protocol
8. Notion/Claude Opus action sandbox via HF Space

### Ongoing
9. HF Community GPU Grant application
10. OpenEnv hackathon ($10K HF credits)
11. ML-intern Kimi 2.6 bridge via HF Inference API
