---
Task ID: AFK-2026-05-16
Agent: opencode (deepseek-v4-flash)
Task: AFK autonomous session — stub replacements, API model testing, new benchmarks

## What We Learned

### API Keys Reality Check (tested, verified)
| Provider | Status | Models | Cost |
|----------|--------|--------|------|
| **OpenRouter** | ✅ 356 models accessible | GPT-4.1, Claude Opus/Sonnet, DeepSeek V4, Mistral, Llama 3, Qwen3, Kimi K2.6 | Already keyed |
| **Groq** | ✅ 16 models, FREE tier | Llama 70B, Mixtral | Free (30 RPM) |
| **GLM Zhipu** | ✅ 7 models | GLM-4.5, GLM-4.6 | Already keyed |
| **MiniMax** | ✅ 7 models | M2.7, M2.5 | Already keyed |
| **xAI Grok** | ❌ 403 Forbidden | — | Key expired/permissions |
| **Arcee** | ❌ 405 | — | Wrong endpoint |

### Browser Automation Verdict
Every "free" LLM playground tested requires login, Cloudflare bypass, or access code. **Browser automation is not viable** for systematic stress testing of commercial models at scale. The working approaches are:
1. **API calls** (keys already in .env) — OpenRouter, Groq, GLM, MiniMax
2. **NopeCHA extension** (forked at specimba/nopecha-extension) — for solving Cloudflare Turnstile when browser is needed
3. **Pre-saved browser sessions** with cookies for gated platforms

### Stub Replacements Completed (all 6 + reinforcement)
| Stub | Status |
|------|--------|
| ModelRelay (fake responses) | ✅ Replaced v1.15→v2.0 ChimeraRouterV2+Ollama |
| AsyncBridgeExecutor (never works) | ✅ Real HTTP POST with retry + timeout |
| CVAVerifier (always passes) | ✅ Real CVA: HARD_BLOCK, ARMED_REVIEW, trust-based |
| Worker.execute_task (simulated) | ✅ Subprocess + Ollama real execution |
| TaskClassifier (keyword stub) | ✅ Keyword + optional FunctionGemma |
| ISC-Runner (1 template/domain) | ✅ Updated: GitHub API listing + fallback batch download |
| LiveLatencyMonitor | ✅ P50/P95/P99 from real calls |
| TWAVETrackerLive | ✅ Real logprobs entropy via Ollama |

### New Stress Test Pipeline
`benchmarks/stress_test_live.py` — real API stress testing with:
- Exponential backoff on 429 (1s, 2s, 4s, 8s, 15s)
- Configurable cooldown between calls
- Refusal scoring from actual model outputs
- Multi-provider orchestration

### New Benchmark Sources (alphaxiv + GitHub)
| Source | Key Takeaway | Integration Plan |
|--------|-------------|-----------------|
| **MCP-SafetyBench** | 20 MCP attack types, all models vulnerable | `github.com/xjzzzzzzzz/MCPSafety` → stress-lab |
| **GTA-2** | Tool-agent benchmark, top models 14% | `github.com/open-compass/GTA` → Bridge eval |
| **HeavySkill** | Parallel reasoning as inner skill | Engine/GMR execution primitive |
| **EvoFlow** | Evolutionary workflow optimization | Auto-GMR routing optimization |
| **SWE-Protege** | SLMs + expert guidance = 42% SWE-bench | TWAVE SLM strategy validated |
| **Agents of Chaos** | Real red-teaming: spoofing, data theft, DoS | Live-lab replicable in NEXUS |
| **Skill-Inject** | 80% ASR on frontier models via skill files | skill-inject.com → KAIJU gate tests |
| **CK-PLUG** | RAG knowledge conflict control | RAG confidence gating for Vault |
| **CTF-Dojo** | 658 containerized CTF challenges | Agent security eval benchmark |
| **PayloadsAllTheThings** | 30+ vuln categories | Adversarial prompt library |
| **SAEG** | Automated exploit generation | Binary vulnerability scanning |
| **terminal-bench** | 100+ real terminal tasks | Agent CLI benchmark |

### What I Need From You
For the **6 missing API endpoints** (FUSION_RECOMMENDATIONS.md):
- GET /health, POST /tasks/heartbeat, POST /tasks/result, GET /tasks/status/{id}, POST /skills/propose, GET /skills/status/{id}
- Need: exact response schema spec and which internal services they should proxy

For **Worker.execute_task** improvements:
- Do you want the subprocess execution path (shell commands) or should it exclusively use Ollama models?

For **Cloudflare bypass on browser playgrounds**:
- nopecha-extension is forked at specimba/nopecha-extension
- Can load it as Playwright extension for Turnstile solving
- Need: NopeCHA API key or extension binary
> 2026-05-18 correction: this file contains exploratory notes from prior work. Canonical status now requires cross-checking against `01_PROJECT_STATE.md`, focused tests, and current queue-runner worklog entries before treating any claim here as verified.
