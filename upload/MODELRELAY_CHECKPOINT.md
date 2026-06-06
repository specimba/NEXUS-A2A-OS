# ModelRelay Checkpoint — Zo Computer Integration
## Status: ACTIVE | Date: 2026-05-10

---

## What Was Built

Created a complete **ModelRelay Gateway** system for Zo Computer specimba, tailored for strict MiniMax M2.7 quota management:

### Core Components (in `/home/workspace/src/nexus_os/modelrelay/`)

| File | Purpose |
|------|---------|
| `gateway.py` | Main relay service — coordinates all components, exposes status/execute methods |
| `provider_manager.py` | Health monitoring, latency tracking, circuit breaker pattern |
| `quota_guard.py` | Per-provider quota tracking, budget enforcement, free-tier optimization |
| `dynamic_router.py` | Intent classification, cascade generation, model scoring (GMR-style) |
| `models_registry.py` | Model capabilities, costs, provider mapping |
| `config.py` | Provider endpoints, routing strategies, fallback chains |
| `__init__.py` | Package exports |
| `SPEC.md` | Full architecture spec with diagrams |

### zo.space API Routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/modelrelay/chat` | POST | Main chat completion with automatic provider routing |
| `/api/modelrelay/status` | GET | Provider status + quota remaining + statistics |
| `/api/modelrelay/providers` | GET | All configured providers |
| `/api/modelrelay/health` | GET | Gateway health check |
| `/api/modelrelay/route` | POST | Manual routing for debugging |
| `/api/modelrelay/models` | GET | All available models in registry |

---

## Key Design Features

### 1. Quota-Aware Routing (QUOTA_AWARE strategy, default)
- MiniMax M2.7 is primary but has ~5 messages remaining
- When MiniMax exhausted → falls back to OpenRouter free models
- When OpenRouter exhausted → falls back to local Ollama
- Always have fallback path

### 2. Provider Priority Order
```
1. MiniMax M2.7 (primary, quota almost exhausted)
2. OpenRouter (free tier, many models)
3. Ollama local (unlimited, fast)
4. Groq (cheap, fast)
5. Cerebras (cheap, low latency)
6. Together AI, DeepSeek (fallbacks)
```

### 3. Routing Strategies
- `quota_aware` — Prioritize free tier, switch when quota exhausted (DEFAULT)
- `cost_optimized` — Always prefer cheapest option
- `quality_first` — Use best available model within budget
- `latency` — Minimize response time

### 4. Circuit Breaker Pattern
- Opens after 3 consecutive failures
- Auto-resets after 60 seconds cooldown
- Prevents cascading failures

### 5. Intent Classification (GMR-style)
- CODE → osman-coder (local) or Codestral
- REASONING → Trinity Large / Kimi K2 Thinking
- RESEARCH → GLM-5 / Kimi K2.5
- SPEED → osman-fast / Bonsai 4B (local)
- SECURITY → Trinity Large Preview / MiniMax M2.5
- GENERAL → osman-agent (local) or MiniMax M2.5

---

## Integration Points with NEXUS OS

### GMR Integration
The `DynamicRouter` uses the same **IntentClassifier** and **fallback chain** logic from NEXUS OS GMR:

```python
# Reuses GMR-style keywords for intent classification
# Falls back to domain_mapping chains from GMR
# Scoring weights: cost(0.25) + latency(0.30) + quality(0.30) + availability(0.15)
```

### TokenGuard Integration
- `quota_guard.record_request()` is called after each successful request
- Tracks tokens used per provider for budget enforcement

### Hermes Integration
- `gateway.route_request()` returns execution plan with cascade
- `gateway.execute_request()` runs the cascade with fallback on failure
- Compatible with Hermes skill adapter interface

---

## Provider Keys Needed

Add these to **Zo Computer Settings > Advanced** (Secrets):

| Secret Name | Provider | Purpose |
|-------------|----------|---------|
| `OPENROUTER_API_KEY` | OpenRouter | Primary free-tier fallback |
| `MINIMAX_API_KEY` | MiniMax | Current primary (quota limited) |
| `GROQ_API_KEY` | Groq | Cheap fast inference |
| `DEEPSEEK_API_KEY` | DeepSeek | Low-cost fallback |
| `CEREBRAS_API_KEY` | Cerebras | Fast, cheap |
| `TOGETHER_API_KEY` | Together AI | Quality fallback |

---

## Testing the Gateway

### Check Gateway Health
```bash
curl https://specimba.zo.space/api/modelrelay/health
```

### Get All Providers
```bash
curl https://specimba.zo.space/api/modelrelay/providers
```

### Get Provider Status + Quota
```bash
curl https://specimba.zo.space/api/modelrelay/status
```

### Test Routing (manual)
```bash
curl -X POST https://specimba.zo.space/api/modelrelay/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "write a python function to sort a list", "strategy": "quota_aware"}'
```

### Test Chat Completion
```bash
curl -X POST https://specimba.zo.space/api/modelrelay/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello, explain quantum computing"}],
    "strategy": "quota_aware"
  }'
```

---

## Next Steps (Pending)

1. **Add API keys to Zo Settings** — Without keys, provider calls will fail
2. **Test with MiniMax M2.7** — Verify quota tracking works
3. **Verify Ollama local** — Ensure osman-coder, osman-fast, osman-reasoning are running
4. **Connect to NEXUS OS TokenGuard** — Wire quota_guard into existing TokenGuard
5. **Monitor cascade behavior** — Confirm fallback works when primary fails
6. **Update AGENTS.md** — Document new capability for Zo

---

## Architecture Diagram

```
User Request → /api/modelrelay/chat
                    ↓
              DynamicRouter
              (intent classify + score models)
                    ↓
              RoutePlan (cascade + provider)
                    ↓
              QuotaGuard (check quotas)
                    ↓
              ProviderManager (check health)
                    ↓
              Execute with Fallback
                    ↓
              Response + Statistics
```

---

## References

- Original GMR: `/home/workspace/src/nexus_os/gmr/rotator.py`
- GMR domain_mapping: `/home/workspace/src/nexus_os/gmr/domain_mapping.py`
- Open-source references:
  - LiteLLM (open-source proxy)
  - OmniRoute (multi-provider gateway)
  - Routerly (policy-based routing)
  - RouteLLM (cost-aware routing)
  - OpenRouter (unified API layer)