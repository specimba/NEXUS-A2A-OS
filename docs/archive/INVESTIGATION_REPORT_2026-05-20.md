---
id: NODE-MIG-INVESTIGATION_REPORT_2026_05_20
authority_scope: experimental
origin_sha256: ac9c3b4aede3722713c09b02c4b0140c35ff11437e468b21f997ff24538bc6ce
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-7D0930
---
# Investigation Report — 2026-05-20

## 1. Chrome PID 31132 GPU Usage Investigation

**Target:** PID 31132 (`chrome.exe`, running since 05/18 02:16)
**Evidence gathered:**

<!-- CANARY: d20df3ab4ad1c8471a1e01f8acee2f47 -->
| Property | Value |
|----------|-------|
| Process | chrome.exe (main browser process) |
| Uptime | 2+ days (since May 18, 02:16) |
| Total CPU | 42,595 seconds |
| Memory | 141.7 MB |
| Threads | 106 |
| GPU adapter | NVIDIA GeForce RTX 4070 Laptop GPU (bus 01:00.0) + Intel UHD Graphics |
| Chrome version | 148.0.7778.168 |
| Hardware acceleration | **Enabled** |
| GPU modules loaded | dxgi.dll, d3d11.dll, d3d12.dll, D3D12Core.dll, D3DCompiler_47.dll |
| NVIDIA-specific modules | **None loaded** (no nvoglv64.dll, nvcuda.dll, etc.) |

**Root cause analysis:**

Chrome 148 loads its own D3DCompiler_47.dll (NOT the system one) and uses DirectX 12 pipeline (`D3D12Core.dll`). The 2-6% constant GPU usage is **expected normal behavior** of Chrome's GPU compositing pipeline:

1. **GPU rasterization** is enabled by default — all page content is rasterized on GPU
2. **Compositing thread** constantly composites the browser UI (tab strip, address bar, window chrome) → GPU usage
3. **33 Chrome processes** total, many with heavy CPU (PID 33236: 14,045s CPU, 473MB; PID 8340: 13,479s CPU, 464MB)
4. D3D12 usage means Microsoft's DirectX 12 translation layer handles the actual GPU calls — this is normal

The NVIDIA RTX 4070 reports `[N/A]` memory for Chrome because Chrome is using **shared GPU memory** (Intel UHD Graphics) rather than dedicated VRAM — Windows GPU scheduler routes it through the NVIDIA adapter but the actual framebuffer is on the integrated GPU.

**Why 2-6% and not 0%:**
- Every visible pixel requires compositing
- Hardware acceleration makes it GPU-bound by design
- Even with all tabs "idle", Chrome constantly composites the UI
- Disabling hardware acceleration would move this load to CPU (worse)

**Fix options (choose one):**
1. Disable hardware acceleration: `chrome://settings/system` → "Use graphics acceleration when available" → OFF
2. Add `--disable-gpu` flag to Chrome shortcut
3. Close browser when not in use (current tabs consume GPU)

---

## 2. Owl Alpha Model Analysis

| Property | Value |
|----------|-------|
| Developer | OpenRouter (own model) |
| Release date | April 28, 2026 |
| Architecture | High-performance foundation model |
| Context | 1M tokens |
| Price | **FREE** (OpenRouter's free tier) |
| Weekly tokens | 1T |
| Purpose | **Agentic workloads** — tool use, code gen, automated workflows |
| Compatibility | Claude Code, OpenClaw, etc. |
| Leaderboard rank | #1 on OpenRouter's own model list (706B tokens processed) |

**Training & workflow mindset:**
Owl Alpha is OpenRouter's own trained model, optimized specifically for:
- **Tool calling** — native function calling support
- **Long-context agent tasks** — 1M context for sustained multi-step execution
- **Code generation** — competitive with frontier models
- **Automated workflows** — built for agent frameworks like OpenClaw

It's fundamentally designed for what NEXUS OS needs — a model that can reliably call tools, follow instructions through multi-step workflows, and maintain context across long sessions. The free pricing makes it ideal for continuous agent operations.

---

## 3. Grok 4.3 Browser Workspace — Keep-Alive Strategy

**Current state:**
- Grok 4.3 beta (released May 6, 2026) has a **full browser sandbox** with:
  - Custom skills creation (file-based, under `/root/.grok/skills/`)
  - MCP server support
  - Connectors (email, calendar, spreadsheets, presentations)
  - Computer access (write code, run it, install packages, produce files)
  - Document generation (PDF, DOCX, spreadsheets, presentations)
- The user has **extra trusted partner status** with Grok/xAI
- Grok's workspace goes to sleep when user stops conversation

**Keep-alive strategies researched:**

| Strategy | Feasibility | Notes |
|----------|-------------|-------|
| **ngrok MCP gateway** | High | Expose a local MCP server via ngrok → Grok can connect to it as a tool endpoint even when not actively chatting |
| **Webhook triggers** | High | Set up webhook endpoints that Grok can register; incoming events wake the workspace |
| **Cron-based heartbeat via Telegram/Slack** | Medium | Have OpenClaw send a ping message to Grok on schedule → conversation stays warm |
| **Grok-MCP bridge (merterbak/Grok-MCP)** | Medium | Community MCP server that bridges Grok API — but user has NO API key, this is browser-only |
| **Shared workspace file** | Low | Grok writes status to a shared file; OpenClaw reads it and triggers new conversation if stale |

**Recommended approach:**
1. Install **Browser MCP** Chrome extension (browsermcp.io, 6.5K stars) — lets Claude Code/VS Code/Cursor control the browser
2. Set up **ngrok tunnel** from local NEXUS MCP server → public URL
3. Register that URL as a **Grok connector** (one of the built-in connector types)
4. Have **OpenClaw** send a daily heartbeat message to Grok via webhook → keeps the workspace warmed
5. Build a **custom Grok skill** that watches for webhook pings and wakes processing

---

## 4. Claw/Swarm Ecosystem — Best Always-On Solution

**Ecosystem landscape (2026):**

| Solution | Stars | Language | RAM | Setup | Best For |
|----------|-------|----------|-----|-------|----------|
| **OpenClaw** | 354K | TypeScript | 1GB+ | 30 min | Full-featured, multi-channel |
| **SwarmClaw** | ~10K | TypeScript | ~500MB | 15 min | Multi-agent orchestration, MCP-native |
| **ZeroClaw** | ~30K | Rust | <5MB | 10 min | Lightweight, edge deployment |
| **NanoClaw** | ~15K | TypeScript | ~50MB | 20 min | Container-first security |
| **NemoClaw** (NVIDIA) | ~8K | Python | ~2GB | 20 min | Sandboxed, GPU-accelerated |
| **ClawTeam** (HKUDS) | 5.2K | Python | varies | 15 min | Research swarm intelligence |
| **PicoClaw** | ~10K | Go | 10MB | 10 min | IoT / Raspberry Pi |
| **Nanobot** | 26K | Python | 191MB | 15 min | Python-native customization |

**Your current installations:**
- `.openclaw-autoclaw` — **50+ skills**, 6 agents configured (glm5-foreman, glm5-hermes, glm5-worker-1/2, main, matrixagent, opusmanseekv4), cron jobs, paired devices, WhatsApp credentials → **this is the active instance**
- `.openclaw` — older instance with 15+ clobbered config backups → **legacy/abandoned**
- Both instances: 18.6K total lines of shell completions (bash, fish, zsh, ps1)
- **NOT in PATH** — needs `openclaw` command added

**Recommended architecture for NEXUS:**

```
┌─────────────────────────────────────────────────┐
│                  SwarmClaw                       │
│  (Orchestrator — schedule, delegation, MCP)     │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐             │
│  │  OpenClaw    │  │  OpenClaw    │  ...more     │
│  │  (main)      │  │  (glm5-*)   │  agents      │
│  └──────────────┘  └──────────────┘             │
│         │                    │                   │
│         └────────┬───────────┘                   │
│                  ▼                               │
│          TrustKernel (gate)                      │
├─────────────────────────────────────────────────┤
│          Local MCP Server (port 7352)            │
│  NEXUS tools: memory, detectors, governance     │
└─────────────────────────────────────────────────┘
```

**Pros/Cons comparison:**

| Solution | Pro | Con |
|----------|-----|-----|
| **SwarmClaw + OpenClaw** | Production-ready, MCP-native, hosted deploy options, 24+ LLM providers, delegation, schedule, org chart visualization, approval-gated actions | Requires Node.js 22+, heavier stack |
| **OpenClaw standalone** | Already installed with 50+ skills, stable v2.1 | Rate-limited AutoClaw (CLAW-02), no native swarm orchestration |
| **ZeroClaw** | 3.4MB binary, <5MB RAM, Rust memory safety | Fewer integrations, smaller ecosystem |
| **NemoClaw (NVIDIA)** | Hardware sandboxing, GPU acceleration, always-on Docker | Requires NVIDIA GPU (you have RTX 4070), 87GB model download |
| **ClawTeam** | Academic-grade swarm intelligence | Research project, not production-hardened |

**Recommendation:** Keep OpenClaw as agent, add SwarmClaw as orchestrator layer. Both are npm-installable. SwarmClaw has native "always-on" deploy configs (Render, Fly.io, Railway).

---

## 5. Pi Agent — Clean Reinstallation Path

**Current state:**
- `C:\Users\speci.000\.pi` directory **exists** (found)
- `pip install pi` shows `pi 0.1.2` **installed** as a pip package
- Python 3.13.2 is default — `imp.find_module()` **removed** in 3.13
- Python 3.12.9 **also installed** (`Python312` directory)
- Python 3.14.3 **also installed**

**The `imp` problem:**
```python
# Python 3.13+ removed imp.find_module()
# Fix: replace with importlib
import importlib.util
spec = importlib.util.find_spec(module_name)
```

**Fix approach:**
1. The `pi` pip package (0.1.2) is probably just the NEXUS Pi agent, not the Zo Computer Pi coding agent
2. Two options:
   - **Option A:** Patch the Pi agent code to replace `imp.find_module()` with `importlib.util.find_spec()` in the relevant file
   - **Option B:** Run Pi agent under Python 3.12 instead (`py -3.12` or set up a venv with 3.12)
   - **Option C:** Since `pi` pip package is actually `aoa-pi` or similar, check if it's even the Pi coding agent we think it is

**Next step needed:** Determine which Pi agent this actually is (Zo's Pi coding agent vs. something else).

---

## 6. Corrected Architecture — What I Got Wrong

| My previous claim | Correction |
|------------------|------------|
| "unfinished software is Zo Computer" | **Wrong.** Unfinished software = z.ai GLM providers' AutoClaw. Zo Computer is the cloud workspace (user's main cloud computer). Zero relation between them. |
| "xAI Grok API 403 — key expired" | **Wrong/irrelevant.** No API key was ever loaded with credit and user will never pay for it. Grok is **browser-sourced unlimited multi-agent 4.3 beta** with custom skills, MCP creation, own sandbox, project folder workspace. This is a browser workspace, not an API. |
| "Abandon Zo as primary compute" | **Rejected.** Zo is the main cloud computer with many advantages. Provider problems can be fixed by user. I should fix the **un-synced workflow/workspace problem** instead. |
| "HF Spaces always-on infrastructure" | **Corrected.** Always-on is not possible on free HF account. Spaces sleep. They're for experimental collaborative multi-space MCP tasks with 35B fine-tuned models and image/video creation engines. |
| "3-layer MCP architecture" | **Too rigid.** The real need is: Zo (cloud workspace) ↔ OpenClaw (local gateway) ↔ Grok (browser agent) ↔ NEXUS governance (TrustKernel). The architecture needs to be flexible across all these domains. |
| "Pi agent is permanently dead" | **Not accepted by user.** User wants absolute clean installation and functional Pi for nexus-cli, ctl, TUI, etc. Clean reinstall path exists. |
