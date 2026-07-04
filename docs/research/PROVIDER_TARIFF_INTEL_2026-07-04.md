# Provider Tariff & Discovery Intelligence — 2026-07-04

**Source:** provider-frontier scout (web-verified, expert-team session
2026-07-04; full cited report preserved in `~/.nexus/recovery/ledger.jsonl`
kind=agent_report). Reference data for the FI-D/FI-Q workstreams in
`docs/plans/NEXUS_FRONTIER_INTELLIGENCE_PLAN_2026-07-04.md`.
Every number below carries the scout's confidence tag; re-verify
LOW/MEDIUM at build time.

## 1. The Owl Alpha case study (first-access proof)

"Owl Alpha" = stealth alias of **Meituan LongCat-2.0-Preview** on
OpenRouter: appeared in the raw `/models` JSON 2026-04-28, unmasked
2026-06-29/30 — a **~9-week anonymous window** during which it reached #1
by token volume (~10.1T tok/mo). 1.6T-param MoE (33-56B active), 1M
context, MIT, trained on ~50k domestic ASICs. Same org ships
LongCat-Image (6B), LongCat-Video (13.6B DiT), LongCat-Video-Avatar-1.5,
LongCat-Next (native multimodal). Correction to folklore: "owl alpha" is
the ALIAS, not a training methodology. Detection rule that would have
caught it day one: **flag any OpenRouter model ID without a known lab
prefix**. Stealth-listing precedents: Quasar Alpha, Cypher Alpha,
Horizon Alpha/Beta.

## 2. Discovery signal sources (ranked, automate top-down)

| # | Source | Endpoint | Auth | Cadence | Note |
|---|---|---|---|---|---|
| 1 | OpenRouter models | `GET https://openrouter.ai/api/v1/models` | none | 15 min | + unknown-prefix stealth rule; polling needs NO credits |
| 2 | OpenRouter rankings | `/api/v1/datasets/rankings-daily` | none | daily | quiet risers |
| 3 | HF org watcher | `huggingface.co/api/models?author={org}` for zai-org, moonshotai, meituan-longcat, MiniMaxAI, deepseek-ai, Qwen, XiaomiMiMo, internlm | none | 30 min | weights sometimes precede announcements |
| 4 | GitHub releases | `api.github.com/repos/{org}/{repo}/releases` same labs | none | hourly | |
| 5 | Cloudflare WAI models | `ai-cloudflare-com.pages.dev/api/models` | none | daily | syncs nightly |
| 6 | Groq | `api.groq.com/openai/v1/models` + changelog page | key/none | hourly/daily | |
| 7 | SiliconFlow | `api.siliconflow.cn/v1/models` | key | hourly | fastest on Chinese releases |
| 8 | Ollama library | `ollama.com/library` HTML (`-cloud` tags) | none | hourly | |
| 9 | NVIDIA NIM catalog | `build.nvidia.com/models` HTML | none | daily | where strong models become FREE (DeepSeek V4 Pro 2026-05-31 precedent) |
| 10 | OpenRouter changelog | `openrouter.ai/docs/changelog/*` | none | daily | |
| 11 | Baseten | `baseten.co/library/` + changelog | none | daily | |
| 12 | LMArena / ArtificialAnalysis | HTML | none | daily | CONFIRMATION-ONLY (24-48h lag) |

Noise suppression: persist normalized `{provider, model_id, first_seen,
context_len, pricing}`; ignore price/metadata-only diffs unless context
length changes; removed row → check provider alias/deprecation page first
(Cloudflare auto-aliased kimi-k2.5→k2.6 on 2026-05-30 — rename, not
removal).

## 3. Free-tier quota/tariff table (as of 2026-07-04)

| Provider | Limits | Confidence | Gotchas |
|---|---|---|---|
| NVIDIA NIM | ~40 RPM free key; ~200 RPM by manual request; credits system phased out early 2025 | MEDIUM (community-sourced; NO official page) | 429/burst undocumented; treat as non-contractual; DeepSeek V4 Pro free @40 RPM, no daily token cap |
| OpenRouter `:free` | 20 req/min; 50 req/DAY if never bought ≥$10 credits, 1000/day once you have (permanent) | HIGH (official) | negative balance → 402 even on free models; Cloudflare DDoS layer blocks independently |
| SiliconFlow | free models $0; L0-L5 tiers by monthly consumption | HIGH (official tiers) | "50/day→1000/day after ¥10" is SECONDARY-sourced; ¥14 signup credit LOW confidence |
| Groq | per-model org limits, e.g. 8b-instant 30 RPM/6K TPM/14.4K RPD/500K TPD; 70b 30 RPM/12K TPM/1K RPD/100K TPD | HIGH (official) | build per-model tables; cached tokens don't count; retry-after honored |
| Cerebras | official: 5 RPM/30K TPM/1M TPH/1M TPD (3 trial models) | CONFLICTED (aggregators say 30 RPM) | re-verify at build; token-bucket refill |
| DashScope intl | ~1M tokens/model free, 90 days validity | HIGH (official) | hard stop `AllocationQuota.FreeTierOnly`; free quota only SG/FRA/HK regions, NOT us-virginia (MEDIUM) |
| Cloudflare WAI | 10,000 neurons/day reset 00:00 UTC | HIGH (official) | model-specific neuron burn (70B ≈ 204,805/M out — a few calls/day); hard-fail on exhaustion |
| GMI Cloud | perpetual free Tier 1: 1M TPM at $0; tiers rise with cumulative spend | HIGH (official) | 429 hard-fail; notable standing free lane |
| Ollama Cloud | free/Pro $20/Max $100; GPU-time weight classes L1-L4; 5h session + weekly resets | MEDIUM | opaque metering, no numeric caps published |
| Baseten | $30 trial; unverified 15 RPM/100K TPM; verified 120 RPM/500K TPM | HIGH (official) | **silent-degrade**: "non-enforced" budgets notify but keep charging; post-trial behavior undocumented |
| Novita | $0.50 one-time trial credit | LOW | text-LLM limits (~60 RPM) unverified; 429 hard-fail |
| Zhipu/z.ai | ~1000 req/day free, Flash models fully free, 1 concurrent | LOW (primary docs unfetchable) | MOST VOLATILE (free limits changed 2× in 12mo); registration may need CN phone |
| Moonshot/Kimi | **NO $0 API tier** — $1 min recharge; Tier 0: 1 concurrent/3 RPM/500K TPM/1.5M TPD | HIGH (official) | aggregator "1000 free req/day" is the CHAT APP, not API; dynamic under-load throttling |
| LongCat/Meituan | no free tier; $0.75/$2.95 per M (promo $0.30/$1.20); context-cache hits FREE; 1B-token packs ~$60 | MEDIUM | OpenAI+Anthropic-compat endpoints; also via OpenRouter |

**Silent-degradation watchlist** (soak-harness priority): NVIDIA NIM
(undocumented behavior), Baseten (non-enforced budgets), Moonshot
(dynamic throttling), Ollama Cloud (opaque GPU-time metering).
Clean hard-failers: OpenRouter, Groq, Cerebras, SiliconFlow, Cloudflare,
GMI, Novita, DashScope.

## 4. Verified post-cutoff model facts (grounding)

GLM-5.2 (2026-06-13, open-weight MIT ~1wk after Coding-Plan debut),
DeepSeek V4 Pro (2026-04-24; FREE on NIM since 05-31 @40 RPM),
Kimi K2.7-Code, Qwen 3.7 Max, MiniMax M3, MiMo V2.5 Pro, LongCat-2.0,
GPT-5.5, Gemini 3.5 Flash (free; Pro delayed to July), Claude Fable 5 /
Mythos 5 — all verified real.
