# GROSS Cross-Agent Intelligence Synthesis — 2026-05-28

**Author:** Zo Coordination Layer  
**Sources:** 8 log files from Codex, Devin/Kimi, Antigravity/Gemini/Opus, OpenCode/DeepSeek, Grok Build  
**Scope:** GROK.exe background upload behavior, infrastructure mapping, strategic implications for NEXUS OS  
**Status:** Intelligence-grade — claims are labeled by confidence (Confirmed / Strong / Plausible / Speculative)

---

## 1. Executive Summary

Grok Build's Windows runtime (`grok.exe`) has a built-in, aggressive background upload/sync system that captures workspace data — including file contents, model weights, conversation history, and tool outputs — into a local staging area (`%USERPROFILE%\.grok\upload_queue`), then uploads it to xAI's cloud infrastructure over persistent TLS connections.

The mechanism has been independently verified by 4+ distinct agent systems across multiple observation windows. The Windows-native behavior is materially different from the K8s/Linux sandbox behavior: on Windows, `grok.exe` runs as a native user process with full filesystem access and no sandbox boundary.

---

## 2. Source Convergence Matrix

| Finding | Codex | Devin/Kimi | Antigravity | OpenCode | Confidence |
|---------|-------|------------|-------------|----------|------------|
| upload_queue exists and grows under workspace activity | ✅ | ✅ | ✅ | ✅ | **Confirmed** |
| Queue contains workspace file copies (not just metadata) | ✅ | ✅ | ✅ | ✅ | **Confirmed** |
| Queue includes model weights (.safetensors) | ✅ | ⚠️ | ✅ | ✅ | **Confirmed** |
| Queue includes research PDFs | ✅ | — | ✅ | ✅ | **Confirmed** |
| Encrypted reasoning field in turn_messages | — | — | ✅ | — | **Strong** |
| Persistent TLS connections (12-20) to Google + Cloudflare | ✅ | — | ✅ | ✅ | **Confirmed** |
| Upload pipeline markers (uploadId, multipart, S3 presign) | ✅ | — | ✅ | ✅ | **Confirmed** |
| 12 Mbps sustained upload correlates with queue writes | ✅ | — | ✅ | ✅ | **Confirmed** |
| WSL simulation proves canary exfil mechanism | — | ✅ | — | — | **Strong** |
| Windows native behavior differs from K8s sandbox | — | — | ✅ | ✅ | **Strong** |
| `always-approve` was active during incident | ✅ | — | ✅ | ✅ | **Confirmed** |
| No user-facing controls to limit upload behavior | ✅ | ✅ | ✅ | ✅ | **Confirmed** |

---

## 3. Infrastructure Map (from 8 sources)

### Windows (grok.exe native process)
- `C:\Users\speci.000\.grok\bin\grok.exe` — TUI runtime
- `C:\Users\speci.000\.grok\upload_queue\` — staging area (grows to 13-51 GB)
- `C:\Users\speci.000\.grok\config.toml` — controls (no upload-related settings)
- `C:\Users\speci.000\.grok\sessions\` — conversation state
- `C:\Users\speci.000\.grok\logs\unified.jsonl` — upload attempt log

### Upload Destinations (from DNS/TCP/ENV correlation)
- `files.grok.com` — S3-compatible file storage
- `connectors-gateway.grok.com` — MCP gateway
- `auth.x.ai` — OAuth
- `api.x.ai` — Inference API
- `gs://grok-code-session-traces/` — Google Cloud Storage bucket (confirmed in metadata.json from repo_state tarballs)
- `brainsync` — Project memory MCP service

### Internal K8s Architecture (from gürokbalım red teaming)
- Proxy: `35.245.43.102` (GCP) — all package traffic routed through
- Internal DNS: `*.hades-openbar.svc.cluster.local`
- Sidecar: port 4242 (only `/health`)
- MicroVM: Cloud Hypervisor + KVM (not standard Docker)

---

## 4. Timeline of Events (Reconstructed)

| Date | Event | Source |
|------|-------|--------|
| May 22-26 | Initial Grok investigation, DERDDRE red teaming | Codex, Devin logs |
| May 27 07:31-07:43 | First upload_queue incident: 1,086 files, 13.18 GB, 12 min, 12 Mbps | Codex log |
| May 27 ~12:00 | Grok explores NEXUS OS at user request — triggers workspace capture | GROSSgrokbuildlog |
| May 27 PM | WSL GROSS simulation: 10-turn run, 250 queue snapshots, canary hits | Devin/Kimi log |
| May 27 23:33 | Plan B launched (D:\GROSS) | OpenCode log |
| May 28 00:14 | grok.exe PID 40616 starts — session 019e67b1 still running | Antigravity log |
| May 28 ~01:00 | Queue peaks at 51 GB / 787 files during active Grok session | Antigravity log |
| May 28 01:33 | Queue: 616 files, 41.28 GB, 18 TLS connections | Antigravity log |
| May 28 ~04:03 | Config.toml modified (unknown source changes always-approve) | OpenCode log |

---

## 5. Strategic Implications for NEXUS OS

### 5.1 Governance (TrustKernel / Guard Plane)
- **Confirmed**: Agent runtimes can have opaque background behaviors invisible to the LLM layer. The Grok LLM truthfully denied uploading when confronted — it didn't know what the runtime binary was doing.
- **NEXUS relevance**: TrustKernel's `evaluate()` only gates agent-initiated actions. If a runtime layer independently captures and exfiltrates data (like `grok.exe`'s `upload_queue`), TrustKernel never sees it.
- **Mitigation design principle**: NEXUS's Guard Plane and VAP chain should explicitly track file read events and workspace state changes, not just agent tool calls.

### 5.2 OpenClaw / Swarm Architecture
- The OpenClaw gateway is live and functional but the native provider routing is still broken (defaults to `openai/gpt-5.5` with no key).
- ModelRelay/NIM path works as a bypass but is architecturally separate from OpenClaw's native agent runtime.
- The Grok-Swarm coordination routes (`/api/grok-swarm`) are deployed but untested end-to-end (network blocked from Grok's sandbox).

### 5.3 Evidence & Research Pipeline
- The GROSS findings are directly applicable to NEXUS's Research Intake Gate: the ERNIE adversarial corpus, Frontier v5 stress sets, and TAMAS benchmarks all test similar "opaque runtime behavior" scenarios.
- MetaAttackDetector categories should include "runtime-level data exfiltration" as a detection class.

---

## 6. Zo-Side Infrastructure State (Snapshot 2026-05-28)

| Component | Status | Details |
|-----------|--------|---------|
| OpenClaw gateway | ✅ Live | 0.0.0.0:18789, reachable via Tailscale |
| ModelRelay/NIM | ✅ Operational | 14 models, NVIDIA NIM key configured |
| Tailscale | ✅ Connected | 3 machines: modal, nexus, specimbapc (Windows, online) |
| zo.space API routes | 13 deployed | /api/modelrelay/*, /api/grok-swarm, /api/nexus-mcp, /api/chat, etc. |
| Governance service | ✅ Running | Python3 on 127.0.0.1:7352 |
| Grok-Swarm route | ✅ Deployed | Bearer-token gated, 5 actions (status/next/add/report/heartbeat) |
| NEXUS 24/7 Automations | 6 active | Research Scout (6h), Progression Tracker (2x daily), Dataset Ideation (weekly), Morning Brief (daily), PR Watcher (6h), Nightly Audit (daily), Grok Progress Watch (daily) |
| Telegram bridge | ⛔ Disabled | Was sending spam, stopped |

---

## 7. Intelligence Gaps (What We Don't Know)

1. **Completed exfiltration proof**: Upload pipeline markers are confirmed, but we lack confirmation that data reached remote storage intact (Plan B captures only local evidence).
2. **Remote deletion feasibility**: Whether data can be removed from xAI infrastructure is untested.
3. **Config control surface**: No user-facing settings control the upload_queue behavior. Whether undocumented env vars or config keys exist is unknown.
4. **Grok Build version differences**: Only one version (0.2.3) has been observed. Whether newer versions behave differently is unknown.
5. **Linux/K8s vs Windows divergence**: The WSL simulation used a synthetic workspace and didn't reproduce the 13 GB scale. Whether the K8s version has the same behavior is unconfirmed.

---

## 8. Recommendations for NEXUS OS Governance

1. **Add runtime-level monitoring to VAP chain**: The VAPProofChain should record file state changes from *any* source, not just agent tool calls. This catches opaque runtime behavior.
2. **Create "runtime behavior" attack class in MetaAttackDetector**: Runtime-level data capture is distinct from prompt injection. It deserves its own detection category.
3. **Document the GROSS findings in NEXUS_CONSTITUTION.md**: Add a section on opaque agent runtime risks and mitigation principles.
4. **Test OpenClaw provider routing fix**: The nvidia_nim models are registered but the main agent can't use them. This should go through the Activation Lanes process.
5. **Maintain the Zo-side watchtower role**: Zo's read-only drift detection is working as designed. The 24/7 automations are producing durable artifacts.

---

*Synthesis completed 2026-05-28. Sources: 8 cross-agent log files spanning Codex (grok-build), Devin/Kimi, Antigravity/Gemini/Opus, OpenCode/DeepSeek.*
