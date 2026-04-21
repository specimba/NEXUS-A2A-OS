# GMR Rotation Table

**Generated**: 2026-04-16 09:15:00 UTC  
**ModelRelay Version**: v1.13.2  
**Online Models**: 74 | **Providers**: 10

---

## 🎯 Domain Assignments

### CODE (Implementation, Debugging, Review)

| Priority | Model | Provider | Tier | Latency | Cost/1M | Status |
|----------|-------|----------|------|---------|---------|--------|
| 🥇 Primary | **osman-coder** | ollama | 40 | 50ms | **$0** | ✅ LOCAL |
| 🥈 Backup | Devstral 2 123B | nvidia | 86 | 542ms | $4.00 | ✅ ONLINE |
| 🥉 Quality | Qwen3 Coder 480B | nvidia | 82 | 9897ms | $8.00 | ✅ ONLINE |
| 4️⃣ Fast | GPT OSS 120B | nvidia | 58 | 398ms | $3.00 | ✅ ONLINE |
| 5️⃣ Budget | Codestral | codestral | 53 | 464ms | $2.00 | ✅ ONLINE |

**Fallback Chain**: osman-coder → qwen2.5-coder:7b → Codestral → GPT OSS 20B

---

### REASONING (Architecture, Planning, Analysis)

| Priority | Model | Provider | Tier | Latency | Cost/1M | Status |
|----------|-------|----------|------|---------|---------|--------|
| 🥇 Primary | **Trinity Large Preview** | opencode | 97 | 1707ms | $5.00 | ✅ ONLINE |
| 🥈 Backup | Kimi K2 Thinking | nvidia | 84 | 709ms | $4.00 | ✅ ONLINE |
| 🥉 Quality | GLM 5 | nvidia | 97 | 4539ms | $5.00 | ✅ ONLINE |
| 4️⃣ Budget | Qwen3 80B Thinking | nvidia | 72 | 522ms | $3.00 | ✅ ONLINE |
| 5️⃣ Local | osman-reasoning | ollama | 40 | 80ms | **$0** | ✅ LOCAL |

**Fallback Chain**: osman-reasoning → qwen3:8b → Qwen3 80B Thinking → Trinity Large

---

### RESEARCH (Deep Research, Synthesis, Knowledge)

| Priority | Model | Provider | Tier | Latency | Cost/1M | Status |
|----------|-------|----------|------|---------|---------|--------|
| 🥇 Primary | **GLM 5** | nvidia | 97 | 4539ms | $5.00 | ✅ ONLINE |
| 🥈 Backup | Kimi K2.5 | nvidia | 95 | 2288ms | $4.00 | ✅ ONLINE |
| 🥉 Quality | Nemotron Ultra 253B | nvidia | 51 | 4638ms | $4.00 | ✅ ONLINE |
| 4️⃣ Budget | Nemotron 3 Super | opencode | 60 | 1275ms | $2.00 | ✅ ONLINE |
| 5️⃣ Economy | Nemotron Super 49B | nvidia | 44 | 409ms | $1.00 | ✅ ONLINE |

**Fallback Chain**: GLM 5 → Nemotron 3 Super → osman-reasoning → Nemotron Super 49B

---

### FAST (Hot Path, Quick Responses, Status Checks)

| Priority | Model | Provider | Tier | Latency | Cost/1M | Status |
|----------|-------|----------|------|---------|---------|--------|
| 🥇 Primary | **Bonsai 4B IQ1_S** | ollama | 40 | **15ms** | **$0** | ✅ LOCAL |
| 🥈 Backup | osman-fast | ollama | 40 | 20ms | **$0** | ✅ LOCAL |
| 🥉 Alt | osman-speed | ollama | 40 | 30ms | **$0** | ✅ LOCAL |
| 4️⃣ Alt | locooperator | ollama | 40 | 30ms | **$0** | ✅ LOCAL |
| 5️⃣ Cloud | Step 3.5 Flash | nvidia | 93 | 1794ms | $3.00 | ✅ ONLINE |

**Fallback Chain**: Bonsai 4B → osman-fast → locooperator → Nemotron Nano 30B

**Requirement**: max_latency_ms = 100, prefer_local = true

---

### SECURITY (Audit, Compliance, Policy)

| Priority | Model | Provider | Tier | Latency | Cost/1M | Status |
|----------|-------|----------|------|---------|---------|--------|
| 🥇 Primary | **Trinity Large Preview** | opencode | 97 | 1707ms | $5.00 | ✅ ONLINE |
| 🥈 Backup | MiniMax M2.5 | opencode | 99 | 1224ms | $6.00 | ✅ ONLINE |
| 🥉 Quality | GLM 5 | nvidia | 97 | 4539ms | $5.00 | ✅ ONLINE |

**Fallback Chain**: Trinity Large → GLM 5 → osman-reasoning → qwen3:8b

**Requirement**: min_tier = 90, prefer_local = false

---

### GENERAL (Mixed Tasks, Chat, Default)

| Priority | Model | Provider | Tier | Latency | Cost/1M | Status |
|----------|-------|----------|------|---------|---------|--------|
| 🥇 Primary | **osman-agent** | ollama | 40 | 50ms | **$0** | ✅ LOCAL |
| 🥈 Backup | qwen3.5:4b | ollama | 40 | 40ms | **$0** | ✅ LOCAL |
| 🥉 Cloud | Llama 4 Maverick | nvidia | 62 | 1181ms | $2.00 | ✅ ONLINE |
| 4️⃣ Quality | GLM 4.7 | nvidia | 88 | 4336ms | $3.00 | ✅ ONLINE |
| 5️⃣ Premium | MiniMax M2.5 | opencode | 99 | 1224ms | $6.00 | ✅ ONLINE |

**Fallback Chain**: osman-agent → qwen3.5:4b → Llama 4 Maverick → GLM 4.7

---

## 💰 Budget Levels

| Level | Tier Range | Cost/1M | Use Case | Example |
|-------|------------|---------|----------|---------|
| **ZERO** | Local only | $0 | Hot path, simple tasks | osman-fast, Bonsai 4B |
| **LOW** | ≤80 | $0-2 | Routine operations | Qwen2.5 Coder 32B |
| **MEDIUM** | ≤95 | $0-5 | Standard tasks | GLM 4.7, Kimi K2 |
| **HIGH** | ≤100 | $0-10 | Important tasks | Trinity Large, GLM 5 |
| **UNLIMITED** | All | $0-15 | Critical tasks | MiniMax M2.5 |

---

## 🏠 Local Models (Always Available, Zero Cost)

| Model | Size | Latency | Specialty | Hot Path? |
|-------|------|---------|-----------|-----------|
| **Bonsai 4B IQ1_S** | 0.9 GB | 15ms | Edge | ✅ |
| **osman-fast** | 3.4 GB | 20ms | Hot Path | ✅ |
| **osman-speed** | 2.5 GB | 30ms | Fast | ✅ |
| **locooperator** | 2.5 GB | 30ms | Fast | ✅ |
| **qwen3:4b-thinking** | 2.5 GB | 40ms | Reasoning | |
| **qwen3.5:4b** | 3.4 GB | 40ms | Balanced | |
| **qwen2.5-coder:7b** | 4.7 GB | 45ms | Code | |
| **osman-agent** | 7.5 GB | 50ms | General | |
| **osman-coder** | 4.7 GB | 50ms | Code | |
| **gemma3n:e4b** | 7.5 GB | 50ms | Agent | |
| **qwen3:8b** | 5.2 GB | 60ms | Quality | |
| **qwen3.5-uncensored:9b** | 7.4 GB | 70ms | Uncensored | |
| **osman-reasoning** | 7.4 GB | 80ms | Reasoning | |
| **Bonsai 4B Q2_K** | 1.5 GB | 20ms | Edge | ✅ |
| **Bonsai 8B Q2_K** | 3.0 GB | 25ms | Edge+ | |

**Total Local Storage**: 62.2 GB

---

## ☁️ Cloud Models (by Tier)

### Tier S (Score 80-100) — Premium Quality

| Model | Provider | Score | Latency | Cost/1M |
|-------|----------|-------|---------|---------|
| MiniMax M2.5 | opencode | 99 | 1224ms | $6.00 |
| Trinity Large Preview | opencode | 97 | 1707ms | $5.00 |
| GLM 5 | nvidia | 97 | 4539ms | $5.00 |
| Kimi K2.5 | nvidia | 95 | 2288ms | $4.00 |
| Step 3.5 Flash | nvidia | 93 | 1794ms | $3.00 |

### Tier A (Score 70-79) — High Quality

| Model | Provider | Score | Latency | Cost/1M |
|-------|----------|-------|---------|---------|
| GLM 4.7 | nvidia | 88 | 4336ms | $3.00 |
| Devstral 2 123B | nvidia | 86 | 542ms | $4.00 |
| Kimi K2 Thinking | nvidia | 84 | 709ms | $4.00 |
| Qwen3 Coder 480B | nvidia | 82 | 9897ms | $8.00 |
| Qwen3 80B Thinking | nvidia | 72 | 522ms | $3.00 |

### Tier B (Score 50-69) — Balanced

| Model | Provider | Score | Latency | Cost/1M |
|-------|----------|-------|---------|---------|
| Llama 4 Maverick | nvidia | 62 | 1181ms | $2.00 |
| Nemotron 3 Super | opencode | 60 | 1275ms | $2.00 |
| GPT OSS 120B | nvidia | 58 | 398ms | $3.00 |
| Codestral | codestral | 53 | 464ms | $2.00 |
| Mistral Large 675B | nvidia | 53 | 480ms | $3.00 |
| Nemotron Ultra 253B | nvidia | 51 | 4638ms | $4.00 |

### Tier C (Score 30-49) — Cost-Effective

| Model | Provider | Score | Latency | Cost/1M |
|-------|----------|-------|---------|---------|
| Nemotron Super 49B | nvidia | 44 | 409ms | $1.00 |
| Qwen2.5 Coder 32B | nvidia | 42 | 591ms | $1.00 |
| Nemotron Nano 30B | nvidia | 30 | 610ms | **FREE** |
| GPT OSS 20B | nvidia | 26 | 599ms | $1.00 |

---

## 📊 Provider Health

| Provider | Models | Avg Latency | Status |
|----------|--------|-------------|--------|
| **ollama** | 15 | ~35ms | ✅ LOCAL |
| **opencode** | 4 | 1425ms | ✅ HEALTHY |
| **nvidia** | 45 | 2156ms | ✅ HEALTHY |
| **codestral** | 1 | 464ms | ✅ HEALTHY |
| **googleai** | 4 | 8727ms | ⚠️ SLOW |
| **groq** | 8 | - | ⚠️ PARTIAL OFFLINE |
| **kilocode** | 12 | - | ⚠️ PARTIAL OFFLINE |
| **openrouter** | 15 | - | ⚠️ PARTIAL OFFLINE |
| **cerebras** | 4 | - | ❌ OFFLINE |
| **scaleway** | 5 | - | ❌ OFFLINE |

---

## 💵 Token Savings Potential

| Strategy | Savings | Mechanism |
|----------|---------|-----------|
| **Local First** | 40-60% | Route to Ollama when possible |
| **Domain Routing** | 20-30% | Right-size model for task |
| **Fallback Chain** | 10-20% | Don't retry failed premium |
| **Semantic Cache** | 30-50% | Reuse similar query results |
| **Prompt Compression** | 10-25% | Compress context before send |
| **Budget Gating** | 5-15% | Block over-budget requests |
| **TOTAL** | **60-80%** | Combined savings |

---

## 🔄 Refresh Schedule

- **Interval**: Every 5 minutes
- **Last Refresh**: 2026-04-16T09:15:00Z
- **Next Refresh**: 2026-04-16T09:20:00Z
- **Source**: localhost:7352 (modelrelay)

---

## 📝 Notes

1. **Local models are always preferred** when task complexity allows
2. **Fallback chains ensure resilience** — never single point of failure
3. **Budget levels control cost** — ZERO forces local-only
4. **Domain specialization improves quality** — right model for right task
5. **Real-time telemetry** ensures we only route to healthy models

---

*Generated by GMR System v1.0*  
*This file is auto-regenerated every 5 minutes*
