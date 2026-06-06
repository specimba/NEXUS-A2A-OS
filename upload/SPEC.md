# NEXUS OS — Zo Computer ModelRelay Gateway

## Special Usage Layer for Quota-Constrained Multi-Provider Routing

**Status**: PLANNING | **Date**: 2026-05-10 | **Author**: Zo(specimba)
**Purpose**: Create a Zo-space hosted model relay with active provider monitoring,
dynamic model switching, and strict MiniMax 2.7 quota management.

---

## 1. Problem Statement

Current state:

- GMR (Genius Model Rotator) exists in `/src/nexus_os/gmr/` with domain-based routing
- NEXUS OS has TokenGuard for token counting, but no unified model relay endpoint
- Zo Computer has MiniMax 2.7 free tier with strict message count limits (\~4-5 remaining)
- Multiple providers are configured in Settings but not actively managed for routing
- No active health monitoring, latency tracking, or automatic failover

Goal:

- Build a **Zo-space model relay** that routes LLM requests across configured providers
- Actively monitors provider health, latency, quota status, and cost
- Dynamically routes to best available model based on intent, budget, and conditions
- Integrates with existing GMR, TokenGuard, and NEXUS OS architecture
- Maximizes free tier value while maintaining reliability

---

## 2. Architecture Overview

```markdown
┌─────────────────────────────────────────────────────────────┐
│                    ZO COMPUTER (specimba)                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Zo.space ModelRelay Gateway              │   │
│  │                  (This Implementation)                │   │
│  │                                                       │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │  │ DynamicRouter│  │ ProviderMgr  │  │  QuotaGuard │  │   │
│  │  │             │  │              │  │            │  │   │
│  │  │ • Intent    │  │ • Health mon │  │ • MinMax   │  │   │
│  │  │ • Cascade   │  │ • Latency    │  │   tracking │  │   │
│  │  │ • Fallback │  │ • Quota poll │  │ • Budget   │  │   │
│  │  └─────────────┘  └──────────────┘  └────────────┘  │   │
│  │         │                │                │         │   │
│  │         └────────────────┼────────────────┘         │   │
│  │                          │                          │   │
│  │  ┌───────────────────────┼───────────────────────┐ │   │
│  │  │              RouteDecision Engine               │ │   │
│  │  │   (GMR-style scoring + health + quota aware)   │ │   │
│  │  └───────────────────────┼───────────────────────┘ │   │
│  └──────────────────────────┼──────────────────────────┘   │
│                             │                               │
│  ┌──────────────────────────┼──────────────────────────┐   │
│  │              Provider Layer                          │   │
│  │                                                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  │   │
│  │  │OpenRouter│ │ MiniMax │  │  Groq   │  │ Cerebras│  │   │
│  │  │         │  │   M2.7  │  │         │  │        │  │   │
│  │  │(primary)│  │(quota)  │  │(fallback│  │(fallback│  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘  │   │
│  │                                                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  │   │
│  │  │ Ollama  │  │ Together│  │DeepSeek │  │  Gemini│  │   │
│  │  │(local)  │  │         │  │         │  │        │  │   │
│  │  │(fast)   │  │(fallback│  │(fallback│  │(fallback│  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              NEXUS OS Integration                     │   │
│  │                                                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ │   │
│  │  │  TokenGuard │  │   GMR    │  │ Hermes  │  │Bridge │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 ProviderManager

- **Health monitoring**: Periodic pings to each provider endpoint
- **Latency tracking**: Rolling average latency per provider
- **Quota polling**: For providers with quota limits (MiniMax, Groq, etc.)
- **Status management**: UP/DEGRADED/DOWN/COOLDOWN states
- **Circuit breaker**: Opens after N consecutive failures, auto-resets after cooldown

### 3.2 QuotaGuard

- **Per-provider quota tracking**: Messages remaining, reset time
- **Budget enforcement**: Max cost per request, daily/monthly limits
- **Free tier optimization**: Prefer free models when available
- **Graceful degradation**: Switch providers when quota exhausted

### 3.3 DynamicRouter

- **Intent classification**: Maps request type to optimal model category
- **Cascade generation**: Build ordered list of fallback models
- **Scoring engine**: Combines cost, latency, quality, and availability
- **Real-time adaptation**: Updates scores based on provider health

### 3.4 RouteDecision Engine

- **Request classification**: Analyze prompt to determine intent
- **Model selection**: Choose optimal model from scored candidates
- **Fallback execution**: Try cascade in order on failure
- **Cost tracking**: Record tokens used, cost incurred

---

## 4. Routing Strategies (Priority Order)

### Strategy 1: QUOTA_AWARE (Default for free tier)

```markdown
1. Check MiniMax quota remaining
2. If quota > threshold: Use MiniMax M2.7 (best quality/free)
3. If quota exhausted: Route to OpenRouter free models
4. If OpenRouter exhausted: Use local Ollama models
5. If all fail: Return error with suggestions
```

### Strategy 2: COST_OPTIMIZED (For non-urgent tasks)

```markdown
1. Always prefer free local models (Ollama)
2. Fall back to OpenRouter free tier
3. Only use paid models if explicitly requested
```

### Strategy 3: QUALITY_FIRST (For complex reasoning tasks)

```markdown
1. Check provider status and latency
2. Select highest-tier available model within budget
3. Fall back to next-tier option
```

### Strategy 4: LATENCY_OPTIMIZED (For interactive use)

```markdown
1. Filter to models with latency < threshold
2. Sort by latency ascending
3. Use fastest available model
```

---

## 5. Provider Configuration

### Primary Providers (in priority order)

| Provider | Endpoint | Quota | Cost | Notes |
| --- | --- | --- | --- | --- |
| MiniMax M2.7 | api.minimax.io | \~5 msgs left | Free | Primary, quota almost exhausted |
| OpenRouter | openrouter.ai/api | Varies | Free/Paid | 500+ models, good fallback |
| Ollama (local) | localhost:11434 | Unlimited | Free | Fast, no external calls |
| Groq | api.groq.com | Free tier | Cheap | Good for fast inference |
| Cerebras | api.cerebras.ai | Free tier | Cheap | Low latency |
| Together AI | api.together.ai | Free tier | Cheap | Good quality |

### Status Monitoring Endpoints

- MiniMax: `POST /v1/text/chatcompletion_v2` → Check response
- OpenRouter: `GET /api/v1/models` → 200 = healthy
- Ollama: `GET /api/tags` → 200 = healthy
- Groq: `GET /v1/models` → 200 = healthy

---

## 6. API Endpoints (zo.space routes)

### POST /api/modelrelay/chat

Main chat completion endpoint with automatic provider routing.

**Request**:

```json
{
  "model": "auto",  // or specific model name
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "strategy": "quota_aware",  // quota_aware|cost_optimized|quality_first|latency
  "max_tokens": 4000,
  "temperature": 0.7
}
```

**Response**:

```json
{
  "id": "relay-xxx",
  "provider": "openrouter",
  "model": "nvidia/llama-3.3-nemotron-super-128k",
  "output": "...",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 200,
    "total_tokens": 300
  },
  "routing": {
    "candidates": 3,
    "attempts": 1,
    "latency_ms": 450
  }
}
```

### GET /api/modelrelay/status

Returns current status of all providers and quota remaining.

**Response**:

```json
{
  "providers": {
    "minimax": {"status": "degraded", "quota_remaining": 2, "latency_ms": 320},
    "openrouter": {"status": "up", "quota_remaining": "unlimited", "latency_ms": 180},
    "ollama": {"status": "up", "quota_remaining": "unlimited", "latency_ms": 45}
  },
  "active_strategy": "quota_aware",
  "total_requests_today": 47,
  "estimated_cost_today": 0.12
}
```

### GET /api/modelrelay/providers

List all configured providers with their current state.

### POST /api/modelrelay/route

Manual routing with custom parameters (for debugging).

---

## 7. Implementation Plan

### Phase 1: Core Relay (Current Implementation)

- [x] Design complete architecture

- [ ] Create `/api/modelrelay/chat` endpoint

- [ ] Implement ProviderManager with health checks

- [ ] Implement QuotaGuard for MiniMax tracking

- [ ] Integrate with existing GMR rotator

### Phase 2: Active Monitoring

- [ ] Add periodic health check scheduler

- [ ] Implement latency tracking

- [ ] Add quota polling for affected providers

- [ ] Build status dashboard endpoint

### Phase 3: Dynamic Adaptation

- [ ] Connect to NEXUS OS TokenGuard

- [ ] Add provider auto-switching on failures

- [ ] Implement cascade fallback logic

- [ ] Add cost tracking and reporting

### Phase 4: NEXUS OS Integration

- [ ] Wire to existing GMR domain_mapping

- [ ] Connect to Hermes skill adapter

- [ ] Add to Bridge for A2A compatibility

- [ ] Enable Slack bot status queries

---

## 8. Files to Create

```markdown
/home/workspace/src/nexus_os/modelrelay/
├── __init__.py
├── gateway.py          # Main relay service
├── provider_manager.py # Provider health & status
├── quota_guard.py      # Quota tracking & enforcement
├── dynamic_router.py   # Routing logic & scoring
├── models_registry.py  # Model capabilities & costs
├── telemetry.py         # Metrics collection
└── config.py            # Configuration

zo.space routes:
├── /api/modelrelay/chat      # POST - Main chat endpoint
├── /api/modelrelay/status    # GET - Provider status
├── /api/modelrelay/providers # GET - All providers
├── /api/modelrelay/route     # POST - Manual routing
└── /api/modelrelay/health   # GET - Gateway health
```

---

## 9. Key Design Decisions

1. **No external DB**: Use in-memory state + JSON files for simplicity
2. **OpenAI-compatible**: Use OpenAI SDK format for easy integration
3. **GMR integration**: Reuse existing domain_mapping and scoring logic
4. **Circuit breaker pattern**: Prevent cascading failures
5. **Graceful degradation**: Always have fallback options
6. **Telemetry light**: Minimize overhead, focus on actionable metrics

---

## 10. Testing Plan

1. **Unit tests**: ProviderManager, QuotaGuard, DynamicRouter
2. **Integration tests**: Full relay with mock providers
3. **Quota simulation**: Test behavior when MiniMax quota exhausted
4. **Failover tests**: Verify cascade fallback works correctly
5. **Load tests**: Verify no issues with concurrent requests

---

## 11. Rollout Checklist

- [ ] Review code with NEXUS OS team

- [ ] Test with MiniMax M2.7 (current primary)

- [ ] Verify OpenRouter fallback works

- [ ] Confirm Ollama local fallback operational

- [ ] Update AGENTS.md with new capability

- [ ] Document API in NEXUS OS wiki

- [ ] Schedule monitoring review after 1 week