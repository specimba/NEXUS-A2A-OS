# NEXUS OS — Agent Manifest
**Version:** 2026-06-22 v1
**Status:** Active operating ruleset for all NEXUS agents (human + AI)
**Sources:** Sakana Fugu + papers10 + codex burnout logs + GLM-5.2 hunt lessons + Fish/Sakana discoveries + papers09

---

## 0. IDENTITY (who NEXUS is)

NEXUS OS is a governed, open-source, agent operating system where every action is evidence-grounded, test-gated, and auditable. We are **not** a weather Q&A bot. We are building **groundbreaking, industry-leading, open-source approaches**. We never pay for credits. We never give up at the first wall.

---

## 1. CORE TRUTHS (the 7 hard-won rules from codex burnout)

### 1.1 Read prior agent logs BEFORE searching
Every Codex/anti-GRAV/DEEPSEEK run has left wisdom in `C:\Users\speci.000\Downloads\NEXUSlogs\`. Read at least 2 prior logs for any non-trivial task. **Do not reinvent workarounds that already exist.**

### 1.2 Do the arithmetic first
- 540 GB GGUF on 8 GB VRAM = impossible. Don't waste an HF round-trip.
- Active parameters ≠ total parameters (Nemotron-3-Ultra 550B = 55B active MoE).
- Free-tier quotas: OpenRouter free = 50 req/day, GitHub Models = 1500/day, Intern AI = 90M tokens/month, Nemotron-Safety-Guard = daily-quotaed.

### 1.3 Parameter-count before recommending a model
| Model | Total | Active | Fits 8GB VRAM? |
|-------|-------|--------|---------------|
| GLM-5.1 | ~744B (estimate) | unknown | **No** (NIM only) |
| GLM-5.2 | ~744B | unknown | **No** (NIM unavailable) |
| Nemotron-3-Ultra-550B-A55B | 550B | 55B MoE | **No** (NIM only) |
| Nemotron-3-Super-120B-A12B | 120B | 12B MoE | **No** (free via OpenCode/KiloCode) |
| Nemotron-3-Nano-30B | 30B | 8B | **Yes** (Ollama local) |
| MiniMax-M3 (M3) | 235B | 22B MoE | NIM/Ollama Cloud |
| VibeThinker-1.5B | 1.5B | 1.5B dense | **Yes** (Q4_K_M 1.04 GB) |
| VibeThinker-3B | 3B | 3B dense | **Yes** (Q4_K_M 1.9 GB) |
| Qwen2.5-Coder-1.5B | 1.5B | 1.5B | **Yes** (Q4_K_M 1.04 GB) |
| DeepSeek-R1-Distill-Qwen-1.5B | 1.5B | 1.5B | **Yes** (Q4_K_M 1.04 GB) |
| Llama-3.1-Nemotron-Safety-Guard-8B-v3 | 8B | 8B | **Yes** (Q4_K_M 4.58 GB) |
| Qwen3-Coder:480B | 480B | unknown | **No** |

### 1.4 Authenticate vs. balance — two different problems
- Key authenticates ✅ ≠ key has balance ❌
- `Novita AI sk_8sTvw...` authenticates BUT returns 403 "not enough balance" on every model
- `LongCat ak_2NX8Y...` authenticates BUT returns 429 "Token 额度不足"
- `SiliconFlow` key is **DEAD** (revoked 2026-06)
- Always distinguish auth-fail vs. balance-fail vs. quota-exhausted vs. cold-start

### 1.5 Conflating "user has account" vs. "key is in env"
- LongCat key came from user pasting from archivist file → marked UNVERIFIED per `docs/coordination/ARCHIVIST_MODELS_API_DIGEST_2026-06-20.md`
- Intern AI key: user has account at chat.intern-ai.org.cn → key needs to be IN ENV (set via `INTERN_API_KEY=sk-...`)
- Never claim "config works" without testing the actual live API call

### 1.6 NIM 429/503 throttling is intermittent, not quota-based
Pattern: 1-3 successful calls → `ResourceExhausted: All workers are busy` for 10-30 sec. Honor `Retry-After`. **Keep a 2-model rotation** (GLM-5.1 ↔ Nemotron Ultra) — not for model diversity, but for memory continuity.

### 1.7 The 8GB-VRAM wall is real
540 GB GLM-5.2 GGUF, 540B Nemotron Ultra — none fit. **Always check VRAM × quant size before committing.**

---

## 2. GLM-5.x ACCESS MATRIX (what works, what doesn't)

| Path | Status | Why |
|------|--------|-----|
| NVIDIA NIM `z-ai/glm-5.1` | ✅ **PRIMARY** (intermittent 429) | Free tier, best frontier available |
| NVIDIA NIM `z-ai/glm-5.2` | ❌ Not yet available | Watch hourly |
| Novita AI (138 models, GLM-5.2 listed) | ❌ 403 "not enough balance" | Fireworks-style pay-first |
| SiliconFlow (GLM-5.2 listed) | ❌ Key DEAD | Revoke + rotate |
| Ollama Cloud GLM-5.x | ❌ Paywalled | Only GLM-4.7 free |
| LongCat (560B MoE, 128K out) | ⚠️ Auth ✅, quota ❌ | Submit feedback at `longcat.chat/platform/feedback` — case `3b1c1b05-8bc0-4d50-8479-ec3ca36f8353` |
| HF GGUF local (`unsloth/GLM-5.2-GGUF`) | ❌ 540 GB total | 11 shards × 49 GB = exceeds 8GB VRAM AND 580GB D: drive |
| z.ai web chat `chat.z.ai` | ⚠️ Free but auth-gated | Requires Firefox session — Codex Computer Use is broken for that |
| HF Spaces playground | ⚠️ Depends on space | Some labs host demos — check `bigmodel.cn` for GLM family |

**OPERATOR DIRECTIVE:** Do NOT add credit anywhere. Wait for NIM GLM-5.2 release or find another free host. Refresh NIM model page every few hours.

---

## 3. PROVIDER ROSTER (live-verified 2026-06-22)

### Tier 1: Primary Rotation (2-model persistence)
- `nim/z-ai/glm-5.1` — Thinker + general complex work
- `nim/nvidia/nemotron-3-ultra-550b-a55b` — Verifier + complex work

**Why 2-model persistence:** User requirement. Rotating through same model family keeps persistent memory context from drifting. **Never mix in Nemotron-Super here.**

### Tier 2: Safe Fallback (logging/memory consistency)
- `longcat:LongCat-2.0-Preview` — logging_fallback_primary
- `internai:intern-s2-preview` — memory_fallback

**Why LongCat + InternAI:** Stable, persistent models for non-flashy critical work. Not primary, but reliable when logging/memory needs consistency.

### Tier 3: Daily Quota Priority (use first in day)
- `opencode:deepseek-v4-flash-free` (1.4 s)
- `opencode:north-mini-code-free` (0.7 s)
- `opencode:nemotron-3-ultra-free` (24 s)
- `opencode:qwen3.6-plus-free`
- `opencode:mimo-v2.5-free`
- `kilocode:nvidia/nemotron-3-super-120b-a12b:free` (15 s) — **emergency only**
- `kilocode:kilo-auto/free`
- `kilocode:stepfun/step-3.7-flash:free`
- `kilocode:poolside/laguna-m.1:free`

**Reset at UTC midnight.**

### Tier 4: Specialist
- `ollama-cloud:qwen3-coder:480b`
- `ollama-cloud:devstral-small-2:24b`
- `ollama-cloud:devstral-2:123b`
- `ollama-cloud:glm-4.7` (only free GLM)

### Tier 5: High-Stakes FUSION
- `openrouter:openrouter/fusion` — multi-model synthesis, DRACO 69% (Fable 5+GPT-5.5). Use for NEXUSCLAW multi-step, Brain API proposals, security probes.

### Tier 6: Emergency Only
- `kilocode:nvidia/nemotron-3-super-120b-a12b:free`
- `mistral:mistral-large-latest` (520 ms, reliable)
- `groq:llama-3.3-70b-versatile` (236 ms, ultra-fast)

### Tier 7: Paywalled Skip — do NOT touch
- `GLM-5.1/5.2/5` on Ollama Cloud, SiliconFlow, Novita

### Avoid — known bug
- `kimi-k2.6` — tool-loop infinite recursion on NIM

### Free Tier Live Providers
| Provider | Endpoint | Key Status | Notes |
|----------|-----------|------------|-------|
| NIM | `https://integrate.api.nvidia.com/v1` | ✅ | GLM-5.1, Nemotron Ultra, DeepSeek V4 Flash |
| Ollama Cloud | `https://ollama.com` | ✅ | 20 free models, 1.2s M3 |
| OpenCode Zen | `https://opencode.ai/zen/v1` | ✅ | 6 free variants, daily quota |
| KiloCode | `https://api.kilo.ai/api/gateway` | ✅ | 8+ free variants |
| Groq | `https://api.groq.com/openai/v1` | ✅ | 236 ms Llama 3.3 70B |
| Mistral | `https://api.mistral.ai/v1` | ✅ | 71 models |
| OpenRouter | `https://openrouter.ai/api/v1` | ⚠️ Auth ✅, balance ❌ | 340 models but 402 on our account |
| GitHub Models | `https://models.inference.ai.azure.com` | ✅ | gpt-4o-mini, 1500/day |
| SambaNova | `https://api.sambanova.ai/v1` | ✅ | DeepSeek V3.1/V3.2 exclusive |
| Cerebras | `https://api.cerebras.ai/v1` | ✅ | 2 models, fast |
| Scaleway | `151783b4-00a3-48cf-906b-6f702670373f` | ✅ | 17 models |
| Cohere | `https://api.cohere.com/v1` | ✅ | 20 models |
| Intern AI | `https://chat.intern-ai.org.cn/api/v1` | ✅ **90M tokens/mo** | `sk-Jysx5j8506PGfX9KiNZ5sqJOGzL01vV245mo1S9pNp96fr0D` |

---

## 4. WORKFLOW ARCHITECTURE (Trinity + Fugu + Conductor fusion)

NEXUS uses **3-role Trinity coordination** with **Fugu-style soft-target SFT** inside the Worker role:

```
                        User Query
                             ↓
        ┌────────────────────────────────────┐
        │   PersistentRouter.pick_for_task │
        │   (Fugu: softmax(reward/τ) over   │
        │    per-task worker success rates)  │
        └─────────────┬──────────────────────┘
                      ↓
        ┌────────────────────────────────────┐
        │   TrinityCoordinator.run_to_compl │
        │   max_steps=5                       │
        └──────┬──────────────┬─────────────┘
               │              │
        T (Thinker)    W (Worker)     V (Verifier)
        nim/glm-5.1    ollama-m3     nim/nemotron-ultra
                       opencode-v4   longcat/internai
                       opencode-ultra
               ↓              ↓              ↓
         [plan]      [execute LLM]    [ACCEPT/REVISE/ABORT]
               ↓              ↓              ↓
         MemoryBus.record_intro()  ←──── outro ──── if REVISE
                              ↓
                   Continue or Terminate
```

### Worker Pool (7 candidates)
1. `nim/z-ai/glm-5.1` (Thinker primary)
2. `nim/nvidia/nemotron-3-ultra-550b-a55b` (Verifier, complex worker)
3. `ollama-cloud:minimax-m3` (fast worker, 1.2 s)
4. `opencode/deepseek-v4-flash-free` (code specialist)
5. `longcat:LongCat-2.0-Preview` (fallback)
6. `internai:intern-s2-preview` (fallback)
7. `groq:llama-3.3-70b-versatile` (ultra-fast)

### Soft-Target SFT (Fugu-style)
- Track per-worker per-task `(successes, failures, total_latency_ms)` in `~/.nexus_pi/state/fugu_worker_rewards.json`
- Compute `p_i(j) = exp(reward_ij / τ) / Σ_j exp(reward_ij / τ)` where `reward = success_rate × (1 - latency_weight × min(1, avg_latency_ms / 10000))`
- Record outcomes via `router.record_outcome(worker, task_type, success, latency_ms)` after each task
- Periodic retrain via `sep-CMA-ES` (Fugu paper) — TODO

---

## 5. SECURITY DEFENSE (from papers10 PNG workflows)

### 5.1 ClawTrojan — 5-step attack chain we must defend against
From `From Prompt Injection to Persistent Control Defending Agentic ClawTrojan Workflow.png`:
1. **Recon context** — agent reads project files, builds trust
2. **Build trust** — agent completes normal tasks, accepts context
3. **Hidden instruction** — workspace note quietly introduces misleading rule
4. **Task pivot** — later requests steer agent toward hidden rule
5. **Last-chance action** — agent may disclose, overwrite, escalate, or deviate

**NEXUS DEFENSE:** MemoryBus records ALL hidden instructions → KAIJU gate verifies each step → Trinity Verifier rejects on any pivot detection.

### 5.2 SEMA — multi-turn jailbreak with intent drift
From `SEMAworkflow.png`:
1. Prefilling self-tuning — attacker fine-tunes on harmful intents with straightforward system prompt + prefill
2. Reinforcement learning with intent-drift-aware reward — attacker learns to generate valid multi-turn adversarial prompts that gradually drift the victim's intent

**NEXUS DEFENSE:** MCPGuard intent classification tracks intent drift across multi-turn → flag when intent changes significantly.

### 5.3 J2 (Jailbreak-the-Jailbreak) — red teaming loop
From `JailbreaktheJailbreakWorkflow.png`:
- Cycle: Planning → Attack → Debrief → Jailbreaking Prompt → repeat
- LLM judge scores the jailbreak, gives feedback
- Iterate until successful jailbreak found or strategy set exhausted

**NEXUS DEFENSE:** Run J2 in sandbox against our own guard cascade to test robustness. Use the LLM-PeerReview Dawid-Skene EM for judge scoring.

### 5.4 THOR — Tool-Integrated Reasoning hierarchical RL
From `THORworkflow.png`:
- TIRGen pipeline: Generate problem → Refine with natural language reasoning + tool-integrated reasoning → build TIR dataset
- THOR framework: Episode-level + Math-level + Code-level optimization with cold start → hierarchical RL
- 2-stage training: SFT → RL
- 13-point improvement on Qwen2.5-Math-7B at AMC23

**NEXUS ADOPTION:** For tool-heavy tasks (NEXUSCLAW Brain API proposals, MCP bridge invocations), use THOR-style hierarchy: episode (tool call) → math (validation) → code (execution). Reward = accuracy + code-pass.

### 5.5 ASTRA — automated strategy library
From `ASTRAworkflow.png`:
- Attack Designer generates jailbreak prompts based on accumulated strategies
- Judge Model evaluates outcomes (binary success + 5-point score)
- Strategy Extractor distills interaction into new strategies
- Vector search retrieves similar strategies from past attempts
- Categorized as Effective / Promising / Ineffective

**NEXUS ADOPTION:** Use ASTRA pattern for self-improving NEXUS guard dataset — `nexus_guard_scenarios_papers09.jsonl` is the Effective/Promising store. Failed scenarios get Ineffective tags.

---

## 6. LOCAL TRAINING (Modal $250 budget)

### 6.1 Constraints
- RTX 4070 8GB VRAM local (fast local eval)
- Modal $250 credit (one-shot forge budget, NOT runtime)
- 590 GB free D: drive

### 6.2 Priority for Modal $250
1. **Nemotron-3-Nano-8B LoRA fine-tune** with adversarial/forge datasets (~$15 per 2-hr job × ~15 jobs = ~$225)
2. **VibeThinker-3B LoRA fine-tune** for NEXUS-specific reasoning patterns (~$30 per 4-hr job × ~2 jobs = ~$60)
3. **DONT spend on GLM-5.2 self-host** — model is 540B, requires 24×48GB RTX 4090s

### 6.3 Local LoRA (free, RTX 4070)
- **VibeThinker-1.5B Q4_K_M** (1.04 GB) — LoRA on NEXUS trust rules + papers09 forge scenarios
- **VibeThinker-3B Q4_K_M** (1.9 GB) — LoRA on reasoning traces
- **Nemotron-Safety-Guard-8B Q4_K_M** (4.58 GB) — LoRA on ClawTrojan-style attacks
- **Qwen2.5-Coder-1.5B Q4_K_M** (1.04 GB) — LoRA on NEXUSCLAW code patterns

---

## 7. NEXUS MANIFEST RULESETS (for next agent generation)

### R1. Read-first, code-second
Before any non-trivial work:
- Read at least 1 prior agent log from `C:\Users\speci.000\Downloads\NEXUSlogs\`
- Read at least 2 user-curated text files from `C:\Users\speci.000\Downloads\ARCHIVIST\`
- Check `01_PROJECT_STATE.md`, `knowledge.md`, `AGENTS.md` first
- Then read `nexus_os/model_relay/persistent_router.py`, `nexus_os/nexusclaw/trinity_coordinator.py` to understand current state

### R2. Math first, model recommendation second
Before recommending a model, compute: `bytes = params_B × 2 (fp16) × quant_ratio`. Reject if `bytes > 8 GB`.

### R3. Verify auth + balance separately
- Curl the model endpoint with the actual key
- Report: `Auth: ✅/❌ | Balance: ✅/❌ (specific error) | Quota: ✅/❌ | Cold start: ✅/❌`
- Never claim "works" without a real response

### R4. Quota tracking is mandatory
- Call `router.record_outcome(worker, task_type, success, latency_ms)` after every task
- Persistent state at `~/.nexus_pi/state/fugu_worker_rewards.json`
- Daily quota reset at UTC midnight — use OpenCode/KiloCode first

### R5. Soft-target SFT with persistent memory
- Every task has `intro_text` (read by new model) and `outro_text` (written by old model)
- MemoryBus.persistent_memory stores context at `~/.nexus_pi/state/model_memory.json`
- Handoffs are automatic when model is swapped

### R6. Trinity 3-role for high-stakes tasks
- T (Thinker) — plan
- W (Worker) — execute
- V (Verifier) — ACCEPT/REVISE/ABORT
- Max 5 steps, then terminate

### R7. Defense against ClawTrojan, SEMA, J2
- MemoryBus records all hidden instructions
- MCPGuard intent classification detects drift
- ASTRA-style strategy library evolves with successful defenses

### R8. No fake green health
- Every endpoint test must return real response or explicit error
- No `verbose=True` to make failures look like successes
- "Not implemented yet" is honest; silent failure is not

### R9. Audit trail for every action
- Every code change: `nexusctl cycle-check` (must pass 631 tests)
- Every model swap: handoff_note with reason
- Every config change: `.modelrelay.json` with `_status` flag
- Every provider failure: `_reason` field documenting the actual HTTP code

### R10. Operator-friendly output
- No raw JSON dumps — use formatted tables
- Show: model, provider, latency, status, quota used/remaining
- Negative results are equally important: "LongCat: 429 quota insufficient — submit feedback case X"

---

## 8. OPEN OPERATIONAL ITEMS (as of 2026-06-22)

### 8.1 Awaiting
- **LongCat quota boost** — case `3b1c1b05-8bc0-4d50-8479-ec3ca36f8353` (beta slots at 01/13/15/23 UTC)
- **NIM GLM-5.2 release** — refresh hourly
- **Sakana Fugu key** with credits — user has not acquired one

### 8.2 Active downloads to D:
- 5 GGUF models (VibeThinker 1.5B/3B, Qwen2.5-Coder, DeepSeek-R1-Distill, Nemotron-Safety-Guard)
- 3 datasets (glaive-function-calling-v2, APIGen-MT-5k, UltraInteract_sft)
- 3 gated datasets (xlam, arthur, adversarial-prompts) — need operator approval

### 8.3 Next agent work
1. Run NEXUS tests with downloaded models (ollama serve + ollama run)
2. Build LoRA training pipeline on D: drive (free, RTX 4070)
3. Wire Fugu records back into router — call `record_outcome` after every task
4. Test Sakana Fugu if user acquires key
5. Read remaining 9 NEXUS v4 planning codex logs (06 is largest)

---

## 9. FILE INVENTORY (where things live)

| Path | Purpose |
|------|---------|
| `C:\Users\speci.000\.modelrelay.json` | Provider config + keys |
| `C:\Users\speci.000\.modelrelay.env` | Env vars for ModelRelay (LongCat + Intern AI keys) |
| `~/.config/opencode/opencode.json` | Opencode model pin (nim/deepseek-v4-flash) |
| `C:\Users\speci.000\AppData\Local\hemes\config.yaml` | Hermes agent config |
| `D:\NEXUS_MODELS\` | Local model + dataset storage |
| `D:\NEXUS_MODELS\datasets\hf_search_results.json` | HF Hub search results |
| `C:\Users\speci.000\Downloads\NEXUSlogs\` | Prior agent logs (36+ files) |
| `C:\Users\speci.000\Downloads\ARCHIVIST\` | User's golden vault of artifacts |
| `C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS\papers10\` | 129 papers + 11 PNG workflows |
| `C:\Users\speci.000\Documents\NEXUS\docs\` | Project documentation |
| `C:\Users\speci.000\Documents\NEXUS\docs\research\` | Research syntheses (papers09, papers10, etc.) |
| `C:\Users\speci.000\Documents\NEXUS\nexus_os\model_relay\` | Router, quota tracker, Fugu, persistent memory |
| `C:\Users\speci.000\Documents\NEXUS\nexus_os\nexusclaw\` | Trinity, conductor, brainstorm, gateway |
| `C:\Users\speci.000\Documents\NEXUS\nexus_os\security\steg\` | MCPGuard, ALSB, CSI |
| `C:\Users\speci.000\Documents\NEXUS\01_PROJECT_STATE.md` | Canonical project state |
| `C:\Users\speci.000\Documents\NEXUS\AGENTS.md` | Agent operating protocol |
| `C:\Users\speci.000\Documents\NEXUS\knowledge.md` | Knowledge base |

---

## 10. AGENT COMMITMENT (what NEXUS agents believe)

> We are building groundbreaking, industry-leading, open-source approaches.
> We don't pay for credits. We don't give up at the first wall.
> We read prior agent logs before searching. We do the arithmetic first.
> We verify auth + balance separately. We never claim success without real response.
> We track quota daily. We use Fugu-style soft-target SFT for worker selection.
> We run Trinity 3-role coordination for high-stakes tasks.
> We defend against ClawTrojan, SEMA, J2 with persistent memory + intent drift detection.
> We never fake green health. We always leave an audit trail.
> We focus on the NEXUS OS mindset: industry-lead, open-source, creative problem-solving.
> When facing a wall, we dig deeper, read more logs, try harder workarounds — not give up.

---

**END MANIFEST v1** — Generated 2026-06-22 from grounded evidence across 36+ agent logs, papers10 PNG workflows, codex burnout lessons, and operator directives.