# NEXUS Model Arena — Intelligence Score & Quality × Health Matrix Guide

## What is the "Intell Score"?

The **Intelligence Score (Intell)** is a **normalized 0-100 ranking** that represents a model's estimated capability relative to the current frontier.

### How it's calculated:
- **Real benchmarks** (where available): MMLU (knowledge), SWE-bench (coding), Chatbot Arena Elo (human preference), GPQA (reasoning)
- **Estimated scores** (marked with `*`): Derived from model architecture, parameter count, training data size, and provider positioning
- **Scale**:
  - **85-100%** = Frontier (Claude Sonnet 4.5, Gemini 2.5 Pro, GPT-4o, DeepSeek V4 Pro)
  - **75-84%** = Strong (Mistral Large, Kimi K2.6, Qwen3.5 397B, Gemma 4)
  - **60-74%** = Capable (Llama 3.3 70B, Codestral, GPT OSS 120B, Mistral Small)
  - **Below 60%** = Basic (small models, older architectures)

### Important notes:
- `*` next to a score means it's **estimated**, not directly benchmarked
- The score is **provider-agnostic** — the same model (e.g., GPT OSS 120B) has the same score regardless of whether it's on Cloudflare, Scaleway, or Fireworks
- The score is **relative to the current state of AI** — it shifts as new models are released

---

## The Quality × Health Matrix (Our Biggest Advantage)

This is the **core innovation** of the NEXUS dashboard. Instead of just listing models, we plot them on a 2D matrix:

### X-Axis: Intelligence Score (Quality)
- Higher = smarter model
- Measures: reasoning, coding, knowledge, creativity

### Y-Axis: Health Status (Availability)
- Higher = model is online and responsive
- Measures: actual ping responses, latency, error rates

### Quadrants:

```
|                      |                      |
|  HIGH QUALITY        |  HIGH QUALITY        |
|  + HEALTHY           |  + DOWN              |
|  (Use these!)        |  (Want these back)   |
|                      |                      |
|----------------------|----------------------|
|                      |                      |
|  LOW QUALITY         |  LOW QUALITY         |
|  + HEALTHY           |  + DOWN              |
|  (Fallback option)   |  (Ignore)            |
|                      |                      |
```

### Dot size = Context Window
- Larger dots = can handle longer conversations/documents
- Helps you choose models for long-context tasks (1M+ tokens)

### Color = Health
- **Green** = online, working, low latency
- **Red** = offline, rate-limited, broken
- **Yellow** = authentication issues

---

## Why This Matters (The "So What?")

### Traditional approach:
- You manually test models one by one
- You don't know which ones work right now
- You waste time on broken providers
- You overpay for premium models when free ones work fine

### NEXUS approach:
1. **Instantly see** the best working model (top-right quadrant)
2. **Auto-fallback** to next-best if the first fails
3. **Route by task**: coding → Codestral, long context → 1M ctx models, speed → low-latency models
4. **Monitor health** in real-time — providers go down, you see it immediately

---

## Current Top Models (Live Snapshot)

| Rank | Model | Intell | Provider | Status | Latency | Context |
|------|-------|--------|----------|--------|---------|---------|
| 1 | DeepSeek V4 Pro | 83% | Fireworks | ✅ UP | ~1300ms | 1M |
| 2 | DeepSeek V4 Flash | 81% | OpenCode | ✅ UP | ~1800ms | 128k |
| 3 | Mistral Large 2512 | 77% | Mistral | ✅ UP | ~1600ms | 128k |
| 4 | Kimi K2p6 | 76% | Fireworks | ✅ UP | ~2000ms | 262k |
| 5 | Qwen3.5 400B | 76% | NVIDIA | ✅ UP | ~1700ms | 128k |
| 6 | Mistral Medium 3.5 | 66% | Mistral | ✅ UP | ~1700ms | 128k |
| 7 | Codestral | 67% | Mistral | ✅ UP | ~1000ms | 128k |
| 8 | GPT OSS 120B | 62% | NVIDIA/Groq | ✅ UP | ~500-1000ms | 128k |
| 9 | Claude Sonnet 4.5 | 88% | Kiro | ❌ DOWN | -- | 200k |
| 10 | Gemini 2.5 Pro | 86% | Google AI | ❌ DOWN | -- | 1M |

---

## God Mode Proxy Profiles

The proxy uses this matrix to automatically route requests:

| Profile | Purpose | Prioritizes |
|---------|---------|-------------|
| `god-smart` | Highest quality | Intell 80%+, tolerates latency |
| `god-mode` | Balanced | Mix of quality + speed + health |
| `god-fast` | Speed | Low latency, good enough quality |
| `god-code` | Coding | Code models, 128k+ context |
| `god-1m` | Long context | 1M+ context window required |
| `god-reason` | Reasoning | Chain-of-thought models |
| `auto` | Default | Same as `god-mode` |

---

## How to Use

1. **Open dashboard**: `http://localhost:7356/`
2. **See the matrix**: Green dots in top-right = best working models
3. **Filter**: Use "Online Only" to hide broken providers
4. **Set profile**: In opencode config, set `model: god-smart` or `model: god-fast`
5. **Auto-fallback**: If a model fails, proxy automatically tries the next best

---

## Provider Health Tiers

| Tier | Providers | Reliability | Notes |
|------|-----------|-------------|-------|
| ⭐⭐⭐ | Cloudflare, Mistral, KiloCode | Very reliable | 100% uptime, generous limits |
| ⭐⭐ | Groq, NVIDIA, Codestral | Reliable | Occasional rate limits |
| ⭐ | OpenRouter, Fireworks | Trial credits | Limited free tier |
| ❌ | Google AI, GitHub, Cerebras | Currently down | Rate limits or paywalled |

---

*Last updated: Auto-refresh every 30 seconds*
