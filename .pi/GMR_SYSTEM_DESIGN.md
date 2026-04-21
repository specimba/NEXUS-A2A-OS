# GMR — Genius Model Rotator System

**Version**: 1.0.0  
**Created**: 2026-04-16 09:15 UTC  
**Author**: Pi Agent  
**Status**: DESIGN & IMPLEMENTATION SPECIFICATION

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Model Arsenal Registry](#3-model-arsenal-registry)
4. [Dynamic Telemetry Integration](#4-dynamic-telemetry-integration)
5. [Rotation Engine Design](#5-rotation-engine-design)
6. [Token Optimization Strategy](#6-token-optimization-strategy)
7. [Implementation Specification](#7-implementation-specification)
8. [File Outputs](#8-file-outputs)

---

## 1. Executive Summary

### Problem Statement

Current modelrelay dashboard shows **74 models online** across **10 providers**, but:
- No automated selection based on task purpose
- No token-aware routing
- No dynamic fallback chains
- No real-time quality/cost optimization

### Solution: GMR (Genius Model Rotator)

A **V12 engine for AI** — zero fuel cost, maximum output:

```
┌─────────────────────────────────────────────────────────────┐
│                    GMR SYSTEM v1.0                           │
│                    "V12 for AI"                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   │
│   │ CYL 1   │   │ CYL 2   │   │ CYL 3   │   │ CYL 4   │   │
│   │ Local   │   │ Cloud   │   │ Fallback│   │ Cache   │   │
│   │ Fast    │   │ Quality │   │ Safety  │   │ Layer   │   │
│   └─────────┘   └─────────┘   └─────────┘   └─────────┘   │
│                                                              │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   │
│   │ CYL 5   │   │ CYL 6   │   │ CYL 7   │   │ CYL 8   │   │
│   │ Code    │   │ Reason  │   │ Research│   │ Security│   │
│   │ Domain  │   │ Domain  │   │ Domain  │   │ Domain  │   │
│   └─────────┘   └─────────┘   └─────────┘   └─────────┘   │
│                                                              │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   │
│   │ CYL 9   │   │ CYL 10  │   │ CYL 11  │   │ CYL 12  │   │
│   │ Token   │   │ Latency │   │ Quality │   │ Cost    │   │
│   │ Monitor │   │ Optim   │   │ Gate    │   │ Optim   │   │
│   └─────────┘   └─────────┘   └─────────┘   └─────────┘   │
│                                                              │
│   OUTPUT: Best Model for Task + Context + Budget            │
│   ZERO TOKEN COST for routing decisions                     │
│   REAL-TIME rotation based on live telemetry                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    GMR ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  TELEMETRY INGEST                      │ │
│  │                                                        │ │
│  │  localhost:7352 (modelrelay) ─────┐                   │ │
│  │                                    │                   │ │
│  │  ┌────────────────────────────────▼─────────────────┐ │ │
│  │  │              TELEMETRY PARSER                    │ │ │
│  │  │  • Parse modelrelay JSON output                  │ │ │
│  │  │  • Extract: name, provider, tier, latency, status│ │ │
│  │  │  • Calculate quality score (tier + uptime)       │ │ │
│  │  │  • Timestamp each reading                        │ │ │
│  │  └──────────────────────────────────────────────────┘ │ │
│  │                         │                             │ │
│  └─────────────────────────┼─────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              DYNAMIC MODEL REGISTRY                    │ │
│  │                                                        │ │
│  │  ┌─────────────────────────────────────────────────┐  │ │
│  │  │  MODELS.JSON (regenerated every 5 min)          │  │ │
│  │  │                                                 │  │ │
│  │  │  {                                              │  │ │
│  │  │    "timestamp": "2026-04-16T09:15:00Z",        │  │ │
│  │  │    "online_count": 74,                         │  │ │
│  │  │    "providers": 10,                            │  │ │
│  │  │    "models": {                                 │  │ │
│  │  │      "code": [...],                            │  │ │
│  │  │      "reasoning": [...],                       │  │ │
│  │  │      "research": [...],                        │  │ │
│  │  │      "fast": [...],                            │  │ │
│  │  │      "security": [...]                         │  │ │
│  │  │    }                                           │  │ │
│  │  │  }                                              │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              ROTATION ENGINE                           │ │
│  │                                                        │ │
│  │  ┌─────────────────────────────────────────────────┐  │ │
│  │  │  select_model(task_type, budget, requirements)  │  │ │
│  │  │                                                 │  │ │
│  │  │  1. Filter by domain capability                 │  │ │
│  │  │  2. Filter by budget availability               │  │ │
│  │  │  3. Filter by latency requirement               │  │ │
│  │  │  4. Rank by quality/cost ratio                  │  │ │
│  │  │  5. Check fallback chain                        │  │ │
│  │  │  6. Return best match + alternatives            │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────┘ │
│                            │                                │
│                            ▼                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              OUTPUT FILES                              │ │
│  │                                                        │ │
│  │  • models.json        — Full registry                 │ │
│  │  • rotation_table.md  — Human-readable table          │ │
│  │  • fallback_chains.json — Domain fallbacks            │ │
│  │  • token_savings.json — Daily savings report          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Model Arsenal Registry

### Full Model Arsenal (from modelrelay 2026-04-16 09:15 UTC)

#### Tier S (Score 80-100) — Premium Quality

| Model | Provider | Score | Latency | Purpose | Token Cost | Status |
|-------|----------|-------|---------|---------|------------|--------|
| **MiniMax M2.5** | opencode | 99 | 1224ms | General Premium | $$$$$ | ✅ ONLINE |
| **Trinity Large Preview** | opencode | 97 | 1707ms | Reasoning | $$$$ | ✅ ONLINE |
| **GLM 5** | nvidia | 97 | 4539ms | Research | $$$$ | ✅ ONLINE |
| **Kimi K2.5** | nvidia | 95 | 2288ms | Analysis | $$$$ | ✅ ONLINE |
| **Step 3.5 Flash** | nvidia | 93 | 1794ms | Fast Premium | $$$ | ✅ ONLINE |

#### Tier A (Score 70-79) — High Quality

| Model | Provider | Score | Latency | Purpose | Token Cost | Status |
|-------|----------|-------|---------|---------|------------|--------|
| **GLM 4.7** | nvidia | 88 | 4336ms | General | $$$ | ✅ ONLINE |
| **Devstral 2 123B** | nvidia | 86 | 542ms | Code Heavy | $$$$ | ✅ ONLINE |
| **Kimi K2 Thinking** | nvidia | 84 | 709ms | Deep Reasoning | $$$$ | ✅ ONLINE |
| **Qwen3 Coder 480B** | nvidia | 82 | 9897ms | Code Premium | $$$$$ | ✅ ONLINE |
| **Qwen3 80B Thinking** | nvidia | 72 | 522ms | Reasoning | $$$ | ✅ ONLINE |
| **Llama 4 Maverick** | nvidia | 62 | 1181ms | General | $$ | ✅ ONLINE |

#### Tier B (Score 50-69) — Balanced

| Model | Provider | Score | Latency | Purpose | Token Cost | Status |
|-------|----------|-------|---------|---------|------------|--------|
| **Kimi K2 Instruct** | nvidia | 62 | 725ms | General | $$ | ✅ ONLINE |
| **Nemotron 3 Super** | opencode | 60 | 1275ms | Research | $$ | ✅ ONLINE |
| **GPT OSS 120B** | nvidia | 58 | 398ms | Code | $$$ | ✅ ONLINE |
| **Codestral** | codestral | 53 | 464ms | Code Fast | $$ | ✅ ONLINE |
| **Mistral Large 675B** | nvidia | 53 | 480ms | Reasoning | $$$ | ✅ ONLINE |
| **Nemotron Ultra 253B** | nvidia | 51 | 4638ms | Research Heavy | $$$$ | ✅ ONLINE |
| **Qwen3.5 400B** | nvidia | 43 | 2370ms | Quality | $$$$ | ✅ ONLINE |
| **Qwen2.5 Coder 32B** | nvidia | 42 | 591ms | Code | $ | ✅ ONLINE |

#### Tier C (Score 30-49) — Cost-Effective

| Model | Provider | Score | Latency | Purpose | Token Cost | Status |
|-------|----------|-------|---------|---------|------------|--------|
| **Nemotron Super 49B** | nvidia | 44 | 409ms | Fast | $ | ✅ ONLINE |
| **Magistral Small** | nvidia | 41 | 435ms | Light | $ | ✅ ONLINE |
| **Nemotron Nano 30B** | nvidia | 30 | 610ms | Economy | FREE | ✅ ONLINE |
| **GPT OSS 20B** | nvidia | 26 | 599ms | Budget | $ | ✅ ONLINE |
| **Stockmark 100B** | nvidia | 16 | 534ms | Budget Quality | $ | ✅ ONLINE |
| **Ministral 14B** | nvidia | 15 | 403ms | Light Fast | FREE | ✅ ONLINE |

#### Local Models (Ollama) — Zero Cloud Cost

| Model | Provider | Score | Latency | Purpose | Token Cost | Status |
|-------|----------|-------|---------|---------|------------|--------|
| **osman-agent** | ollama | 40 | ~50ms | Local General | FREE | ✅ LOCAL |
| **osman-coder** | ollama | 40 | ~50ms | Local Code | FREE | ✅ LOCAL |
| **osman-speed** | ollama | 40 | ~30ms | Local Fast | FREE | ✅ LOCAL |
| **osman-reasoning** | ollama | 40 | ~80ms | Local Reason | FREE | ✅ LOCAL |
| **osman-fast** | ollama | 40 | ~20ms | Hot Path | FREE | ✅ LOCAL |
| **qwen3.5:4b** | ollama | 40 | ~40ms | Local Default | FREE | ✅ LOCAL |
| **qwen3:8b** | ollama | 40 | ~60ms | Local Quality | FREE | ✅ LOCAL |
| **gemma3n:e4b** | ollama | 40 | ~50ms | Local Agent | FREE | ✅ LOCAL |
| **qwen2.5-coder:7b** | ollama | 40 | ~45ms | Local Code | FREE | ✅ LOCAL |
| **qwen3:4b-thinking** | ollama | 40 | ~40ms | Local Think | FREE | ✅ LOCAL |
| **qwen3.5-uncensored:9b** | ollama | 40 | ~70ms | Local Uncens | FREE | ✅ LOCAL |
| **locooperator** | ollama | 40 | ~30ms | Local Fast | FREE | ✅ LOCAL |
| **Bonsai 4B IQ1_S** | ollama | 40 | ~15ms | Edge Fast | FREE | ✅ LOCAL |
| **Bonsai 4B Q2_K** | ollama | 40 | ~20ms | Edge | FREE | ✅ LOCAL |
| **Bonsai 8B Q2_K** | ollama | 40 | ~25ms | Edge+ | FREE | ✅ LOCAL |

### Model Classification by Domain

```json
{
  "domains": {
    "code": {
      "primary": [
        {"model": "osman-coder", "tier": "local", "cost": 0, "latency_ms": 50},
        {"model": "Devstral 2 123B", "tier": "S", "cost": 4, "latency_ms": 542},
        {"model": "Qwen3 Coder 480B", "tier": "S", "cost": 5, "latency_ms": 9897},
        {"model": "GPT OSS 120B", "tier": "B", "cost": 3, "latency_ms": 398},
        {"model": "Codestral", "tier": "B", "cost": 2, "latency_ms": 464},
        {"model": "Qwen2.5 Coder 32B", "tier": "B", "cost": 1, "latency_ms": 591}
      ],
      "fallback": ["osman-coder", "qwen2.5-coder:7b", "Codestral", "GPT OSS 20B"]
    },
    "reasoning": {
      "primary": [
        {"model": "Trinity Large Preview", "tier": "S", "cost": 4, "latency_ms": 1707},
        {"model": "Kimi K2 Thinking", "tier": "A", "cost": 4, "latency_ms": 709},
        {"model": "Qwen3 80B Thinking", "tier": "A", "cost": 3, "latency_ms": 522},
        {"model": "Mistral Large 675B", "tier": "B", "cost": 3, "latency_ms": 480},
        {"model": "osman-reasoning", "tier": "local", "cost": 0, "latency_ms": 80}
      ],
      "fallback": ["osman-reasoning", "qwen3:8b", "Qwen3 80B Thinking"]
    },
    "research": {
      "primary": [
        {"model": "GLM 5", "tier": "S", "cost": 4, "latency_ms": 4539},
        {"model": "Kimi K2.5", "tier": "S", "cost": 4, "latency_ms": 2288},
        {"model": "Nemotron Ultra 253B", "tier": "B", "cost": 4, "latency_ms": 4638},
        {"model": "Nemotron 3 Super", "tier": "B", "cost": 2, "latency_ms": 1275}
      ],
      "fallback": ["GLM 5", "Nemotron 3 Super", "osman-reasoning"]
    },
    "fast": {
      "primary": [
        {"model": "osman-speed", "tier": "local", "cost": 0, "latency_ms": 30},
        {"model": "osman-fast", "tier": "local", "cost": 0, "latency_ms": 20},
        {"model": "locooperator", "tier": "local", "cost": 0, "latency_ms": 30},
        {"model": "Bonsai 4B IQ1_S", "tier": "local", "cost": 0, "latency_ms": 15},
        {"model": "Step 3.5 Flash", "tier": "S", "cost": 3, "latency_ms": 1794}
      ],
      "fallback": ["Bonsai 4B", "osman-fast", "locooperator", "Nemotron Nano 30B"]
    },
    "security": {
      "primary": [
        {"model": "Trinity Large Preview", "tier": "S", "cost": 4, "latency_ms": 1707},
        {"model": "MiniMax M2.5", "tier": "S", "cost": 5, "latency_ms": 1224},
        {"model": "GLM 5", "tier": "S", "cost": 4, "latency_ms": 4539}
      ],
      "fallback": ["Trinity Large Preview", "osman-reasoning", "qwen3:8b"]
    },
    "general": {
      "primary": [
        {"model": "MiniMax M2.5", "tier": "S", "cost": 5, "latency_ms": 1224},
        {"model": "GLM 4.7", "tier": "A", "cost": 3, "latency_ms": 4336},
        {"model": "Llama 4 Maverick", "tier": "A", "cost": 2, "latency_ms": 1181},
        {"model": "osman-agent", "tier": "local", "cost": 0, "latency_ms": 50}
      ],
      "fallback": ["osman-agent", "qwen3.5:4b", "Llama 4 Maverick"]
    }
  }
}
```

---

## 4. Dynamic Telemetry Integration

### modelrelay Integration

```python
# gmr/telemetry.py

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

MODELRELAY_URL = "http://localhost:7352/api/models"

@dataclass
class ModelTelemetry:
    """Live model telemetry from modelrelay."""
    name: str
    provider: str
    tier: int
    latency_ms: int
    uptime_pct: float
    status: str  # "up", "down", "timeout"
    timestamp: str
    
    @property
    def quality_score(self) -> float:
        """Calculate quality score from tier and uptime."""
        # Tier contribution: 0-100
        tier_score = min(self.tier, 100)
        # Uptime contribution: 0-100, weighted
        uptime_score = self.uptime_pct * 100
        # Combined: tier 70%, uptime 30%
        return tier_score * 0.7 + uptime_score * 0.3
    
    @property
    def is_available(self) -> bool:
        return self.status == "up" and self.uptime_pct >= 0.5
    
    @property
    def is_local(self) -> bool:
        return self.provider in {"ollama", "local"}


class TelemetryIngest:
    """Ingest and parse modelrelay output."""
    
    def __init__(self, url: str = MODELRELAY_URL):
        self.url = url
        self.last_fetch: Optional[datetime] = None
        self.cache: Dict[str, ModelTelemetry] = {}
    
    def fetch(self) -> Dict[str, ModelTelemetry]:
        """Fetch latest telemetry from modelrelay."""
        try:
            response = requests.get(self.url, timeout=5)
            data = response.json()
            
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            for model_data in data.get("models", []):
                telemetry = ModelTelemetry(
                    name=model_data["name"],
                    provider=model_data["provider"],
                    tier=model_data.get("tier", 0),
                    latency_ms=model_data.get("latency_ms", 9999),
                    uptime_pct=model_data.get("uptime", 1.0),
                    status=model_data.get("status", "unknown"),
                    timestamp=timestamp
                )
                self.cache[telemetry.name] = telemetry
            
            self.last_fetch = datetime.utcnow()
            return self.cache
            
        except Exception as e:
            print(f"[GMR] Telemetry fetch failed: {e}")
            return self.cache  # Return cached data
    
    def get_online_models(self) -> List[ModelTelemetry]:
        """Get list of currently available models."""
        return [m for m in self.cache.values() if m.is_available]
    
    def get_local_models(self) -> List[ModelTelemetry]:
        """Get list of local models (zero cost)."""
        return [m for m in self.cache.values() if m.is_local and m.is_available]
    
    def get_best_for_domain(self, domain: str) -> Optional[ModelTelemetry]:
        """Get best available model for a domain."""
        domain_models = DOMAIN_MAPPING.get(domain, [])
        
        for model_spec in domain_models:
            model_name = model_spec["model"]
            if model_name in self.cache:
                telemetry = self.cache[model_name]
                if telemetry.is_available:
                    return telemetry
        
        return None
```

### Auto-Refresh Schedule

```python
# gmr/scheduler.py

import time
import threading
from typing import Callable

class RefreshScheduler:
    """Schedule periodic telemetry refresh."""
    
    def __init__(self, ingest: TelemetryIngest, interval_seconds: int = 300):
        self.ingest = ingest
        self.interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
    
    def on_refresh(self, callback: Callable):
        """Register callback for after each refresh."""
        self._callbacks.append(callback)
    
    def start(self):
        """Start the refresh loop."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the refresh loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _loop(self):
        while self._running:
            # Fetch new telemetry
            self.ingest.fetch()
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(self.ingest.cache)
                except Exception as e:
                    print(f"[GMR] Callback error: {e}")
            
            # Wait for next interval
            time.sleep(self.interval)
```

---

## 5. Rotation Engine Design

### Selection Algorithm

```python
# gmr/rotator.py

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class TaskType(Enum):
    CODE = "code"
    REASONING = "reasoning"
    RESEARCH = "research"
    FAST = "fast"
    SECURITY = "security"
    GENERAL = "general"

class BudgetLevel(Enum):
    UNLIMITED = "unlimited"  # Use best quality
    HIGH = "high"           # Premium OK
    MEDIUM = "medium"       # Balanced
    LOW = "low"             # Cost-conscious
    ZERO = "zero"           # Local only

@dataclass
class ModelSelection:
    """Result of model selection."""
    primary: str
    fallbacks: List[str]
    estimated_tokens: int
    estimated_cost: float
    estimated_latency_ms: int
    reason: str

class RotationEngine:
    """V12 engine for model rotation."""
    
    def __init__(self, telemetry: TelemetryIngest):
        self.telemetry = telemetry
        self.domain_mapping = DOMAIN_MAPPING
    
    def select(
        self,
        task_type: TaskType,
        budget: BudgetLevel = BudgetLevel.MEDIUM,
        max_latency_ms: int = 10000,
        min_quality_score: float = 40.0,
        require_local: bool = False,
        prefer_local: bool = True
    ) -> ModelSelection:
        """
        Select the best model for the task.
        
        V12 cylinders working together:
        1. Filter by availability
        2. Filter by domain capability
        3. Filter by budget constraint
        4. Filter by latency requirement
        5. Filter by quality threshold
        6. Apply local preference
        7. Rank by quality/cost ratio
        8. Build fallback chain
        9. Estimate tokens/cost/latency
        10. Return selection with reason
        """
        
        # Step 1: Get available models
        available = self.telemetry.get_online_models()
        
        # Step 2: Filter by domain
        domain_models = self.domain_mapping.get(task_type.value, {}).get("primary", [])
        domain_names = {m["model"] for m in domain_models}
        candidates = [m for m in available if m.name in domain_names]
        
        if require_local:
            candidates = [m for m in candidates if m.is_local]
        
        if not candidates:
            # Fallback to general domain
            general_models = self.domain_mapping.get("general", {}).get("primary", [])
            general_names = {m["model"] for m in general_models}
            candidates = [m for m in available if m.name in general_names]
        
        # Step 3: Filter by budget
        if budget == BudgetLevel.ZERO:
            candidates = [m for m in candidates if m.is_local]
        elif budget == BudgetLevel.LOW:
            # Exclude premium models (tier > 80)
            candidates = [m for m in candidates if m.tier <= 80 or m.is_local]
        elif budget == BudgetLevel.MEDIUM:
            # Exclude ultra-premium (tier > 95)
            candidates = [m for m in candidates if m.tier <= 95 or m.is_local]
        # HIGH and UNLIMITED: no filtering
        
        # Step 4: Filter by latency
        candidates = [m for m in candidates if m.latency_ms <= max_latency_ms]
        
        # Step 5: Filter by quality
        candidates = [m for m in candidates if m.quality_score >= min_quality_score]
        
        if not candidates:
            # Emergency fallback: best local model
            local = self.telemetry.get_local_models()
            if local:
                return ModelSelection(
                    primary=local[0].name,
                    fallbacks=[m.name for m in local[1:4]],
                    estimated_tokens=1000,
                    estimated_cost=0.0,
                    estimated_latency_ms=local[0].latency_ms,
                    reason="Emergency: No cloud models available, using local"
                )
            else:
                raise RuntimeError("No models available")
        
        # Step 6: Apply local preference
        if prefer_local:
            local_candidates = [m for m in candidates if m.is_local]
            if local_candidates:
                # Use local for first selection
                primary = max(local_candidates, key=lambda m: m.quality_score)
            else:
                primary = max(candidates, key=lambda m: m.quality_score)
        else:
            primary = max(candidates, key=lambda m: m.quality_score)
        
        # Step 7-8: Build fallback chain
        fallbacks = self._build_fallback_chain(task_type, primary.name, candidates)
        
        # Step 9: Estimate metrics
        estimated_tokens = 1000  # Default estimate
        estimated_cost = self._estimate_cost(primary, estimated_tokens)
        
        return ModelSelection(
            primary=primary.name,
            fallbacks=fallbacks,
            estimated_tokens=estimated_tokens,
            estimated_cost=estimated_cost,
            estimated_latency_ms=primary.latency_ms,
            reason=f"Selected for {task_type.value} task with {budget.value} budget"
        )
    
    def _build_fallback_chain(
        self,
        task_type: TaskType,
        primary: str,
        candidates: List[ModelTelemetry]
    ) -> List[str]:
        """Build fallback chain: local → cloud → emergency."""
        
        # Get domain-specific fallbacks
        domain_fallbacks = DOMAIN_MAPPING.get(task_type.value, {}).get("fallback", [])
        
        # Start with domain fallbacks that are available
        fallbacks = []
        for model_name in domain_fallbacks:
            if model_name != primary and model_name in self.telemetry.cache:
                telemetry = self.telemetry.cache[model_name]
                if telemetry.is_available:
                    fallbacks.append(model_name)
        
        # Add remaining candidates sorted by quality
        remaining = sorted(
            [m for m in candidates if m.name != primary and m.name not in fallbacks],
            key=lambda m: m.quality_score,
            reverse=True
        )
        fallbacks.extend([m.name for m in remaining[:3]])
        
        return fallbacks[:5]  # Max 5 fallbacks
    
    def _estimate_cost(self, model: ModelTelemetry, tokens: int) -> float:
        """Estimate cost for model usage."""
        if model.is_local:
            return 0.0
        
        # Cost tiers (approximate USD per 1M tokens)
        COST_PER_TIER = {
            range(90, 101): 15.0,  # Premium
            range(80, 90): 10.0,   # High
            range(70, 80): 5.0,    # Medium
            range(50, 70): 2.0,    # Low
            range(0, 50): 0.5,     # Budget
        }
        
        for tier_range, cost in COST_PER_TIER.items():
            if model.tier in tier_range:
                return (tokens / 1_000_000) * cost
        
        return 0.0
```

---

## 6. Token Optimization Strategy

### Token Savings Calculation

```python
# gmr/savings.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
import json

@dataclass
class TokenSavings:
    """Token savings from model rotation."""
    timestamp: str
    task_type: str
    primary_model: str
    fallback_model: str
    tokens_used: int
    tokens_saved: int
    cost_saved: float
    reason: str

class SavingsTracker:
    """Track and report token savings."""
    
    def __init__(self):
        self.savings: List[TokenSavings] = []
        self.total_tokens_used = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0
    
    def record(
        self,
        task_type: str,
        primary: str,
        fallback: str,
        tokens_used: int,
        tokens_saved: int,
        cost_saved: float,
        reason: str
    ):
        """Record a savings event."""
        saving = TokenSavings(
            timestamp=datetime.utcnow().isoformat() + "Z",
            task_type=task_type,
            primary_model=primary,
            fallback_model=fallback_model,
            tokens_used=tokens_used,
            tokens_saved=tokens_saved,
            cost_saved=cost_saved,
            reason=reason
        )
        self.savings.append(saving)
        
        self.total_tokens_used += tokens_used
        self.total_tokens_saved += tokens_saved
        self.total_cost_saved += cost_saved
    
    def get_report(self) -> Dict:
        """Generate savings report."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_tokens_used": self.total_tokens_used,
                "total_tokens_saved": self.total_tokens_saved,
                "total_cost_saved": round(self.total_cost_saved, 4),
                "savings_rate": (
                    self.total_tokens_saved / max(self.total_tokens_used, 1)
                ) * 100,
            },
            "by_task_type": self._by_task_type(),
            "recent_savings": [
                {
                    "timestamp": s.timestamp,
                    "task": s.task_type,
                    "primary": s.primary_model,
                    "fallback": s.fallback_model,
                    "saved": s.tokens_saved,
                    "cost": s.cost_saved
                }
                for s in self.savings[-10:]
            ]
        }
    
    def _by_task_type(self) -> Dict:
        """Aggregate savings by task type."""
        by_type = {}
        for saving in self.savings:
            if saving.task_type not in by_type:
                by_type[saving.task_type] = {
                    "tokens_used": 0,
                    "tokens_saved": 0,
                    "cost_saved": 0.0,
                    "count": 0
                }
            by_type[saving.task_type]["tokens_used"] += saving.tokens_used
            by_type[saving.task_type]["tokens_saved"] += saving.tokens_saved
            by_type[saving.task_type]["cost_saved"] += saving.cost_saved
            by_type[saving.task_type]["count"] += 1
        return by_type
    
    def save_report(self, path: str):
        """Save report to file."""
        report = self.get_report()
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
```

### Token Savings Sources

| Source | Savings | Mechanism |
|--------|---------|-----------|
| **Local First** | 40-60% | Route to Ollama when possible |
| **Domain Routing** | 20-30% | Right-size model for task |
| **Fallback Chain** | 10-20% | Don't retry failed premium |
| **Semantic Cache** | 30-50% | Reuse similar query results |
| **Prompt Compression** | 10-25% | Compress context before send |
| **Budget Gating** | 5-15% | Block over-budget requests |

---

## 7. Implementation Specification

### File Structure

```
src/nexus_os/gmr/
├── __init__.py           # Module exports
├── telemetry.py          # modelrelay integration
├── rotator.py            # Selection engine
├── scheduler.py          # Auto-refresh
├── savings.py            # Token tracking
├── domain_mapping.py     # Domain→Model config
└── outputs/
    ├── models.json       # Full registry (regenerated)
    ├── rotation_table.md # Human-readable table
    ├── fallback_chains.json
    └── token_savings.json
```

### Integration with NEXUS OS

```python
# Integration points

# 1. Bridge — Route requests through GMR
class BridgeServer:
    def __init__(self):
        self.gmr = RotationEngine(telemetry=TelemetryIngest())
        self.savings = SavingsTracker()
    
    async def handle_request(self, request):
        # Get task type from request
        task_type = self._classify_task(request)
        
        # Select model
        selection = self.gmr.select(
            task_type=task_type,
            budget=self._get_budget(request),
            prefer_local=True
        )
        
        # Execute with fallback
        for model in [selection.primary] + selection.fallbacks:
            try:
                result = await self._execute(model, request)
                self.savings.record(...)
                return result
            except Exception:
                continue

# 2. Engine — Hermes integration
class HermesRouter:
    def route(self, task_id, description, context):
        # Use GMR for model selection
        task_type = self.classifier.classify(description)
        selection = self.gmr.select(task_type)
        
        decision = RoutingDecision(
            task_id=task_id,
            selected_model=selection.primary,
            fallback_models=selection.fallbacks,
            estimated_cost=selection.estimated_cost,
            reason=selection.reason
        )
        return decision

# 3. TokenGuard — Budget awareness
class TokenGuard:
    def check(self, agent_id, required_tokens):
        # Consider GMR estimated cost
        selection = self.gmr.current_selection
        if selection.estimated_cost > self.get_budget(agent_id):
            return False
        return True
```

### Auto-Refresh Configuration

```yaml
# gmr/config.yaml

telemetry:
  source: "http://localhost:7352/api/models"
  refresh_interval_seconds: 300  # 5 minutes
  timeout_seconds: 5
  retry_count: 3

rotation:
  default_budget: "medium"
  prefer_local: true
  max_fallbacks: 5
  
  domain_defaults:
    code:
      budget: "medium"
      max_latency_ms: 5000
    reasoning:
      budget: "high"
      max_latency_ms: 10000
    research:
      budget: "high"
      max_latency_ms: 30000
    fast:
      budget: "zero"
      max_latency_ms: 100
      require_local: true
    security:
      budget: "unlimited"
      prefer_local: false

savings:
  track_all: true
  report_interval_seconds: 3600  # 1 hour
  output_path: "gmr/outputs/token_savings.json"
```

---

## 8. File Outputs

### models.json (Regenerated)

```json
{
  "timestamp": "2026-04-16T09:15:00Z",
  "online_count": 74,
  "providers": 10,
  "domains": {
    "code": {
      "primary": [
        {"model": "osman-coder", "tier": "local", "latency_ms": 50, "cost": 0},
        {"model": "Devstral 2 123B", "tier": 86, "latency_ms": 542, "cost": 4},
        {"model": "GPT OSS 120B", "tier": 58, "latency_ms": 398, "cost": 3}
      ],
      "fallback": ["osman-coder", "qwen2.5-coder:7b", "Codestral"]
    },
    "reasoning": {
      "primary": [
        {"model": "Trinity Large Preview", "tier": 97, "latency_ms": 1707, "cost": 4},
        {"model": "Kimi K2 Thinking", "tier": 84, "latency_ms": 709, "cost": 4}
      ],
      "fallback": ["osman-reasoning", "qwen3:8b"]
    }
  },
  "local_models": [
    {"model": "osman-agent", "latency_ms": 50},
    {"model": "osman-coder", "latency_ms": 50},
    {"model": "osman-speed", "latency_ms": 30},
    {"model": "osman-fast", "latency_ms": 20},
    {"model": "qwen3.5:4b", "latency_ms": 40}
  ]
}
```

### rotation_table.md (Human-Readable)

```markdown
# GMR Rotation Table — 2026-04-16 09:15 UTC

## Domain Assignments

| Domain | Primary | Tier | Latency | Cost | Fallbacks |
|--------|---------|------|---------|------|-----------|
| **CODE** | osman-coder | Local | 50ms | $0 | qwen2.5-coder, Devstral 2 |
| **REASONING** | Trinity Large | S | 1707ms | $4 | osman-reasoning, Kimi K2 Think |
| **RESEARCH** | GLM 5 | S | 4539ms | $4 | Nemotron 3 Super, Kimi K2.5 |
| **FAST** | osman-speed | Local | 30ms | $0 | Bonsai 4B, locooperator |
| **SECURITY** | Trinity Large | S | 1707ms | $4 | GLM 5, osman-reasoning |
| **GENERAL** | osman-agent | Local | 50ms | $0 | qwen3.5:4b, Llama 4 |

## Budget Levels

| Level | Model Tier | Cost Range | Use Case |
|-------|------------|------------|----------|
| ZERO | Local only | $0 | Hot path, simple tasks |
| LOW | ≤80 | $0-2 | Routine operations |
| MEDIUM | ≤95 | $0-5 | Standard tasks |
| HIGH | ≤100 | $0-10 | Important tasks |
| UNLIMITED | All | $0-15 | Critical tasks |

## Token Savings Today

- Total Used: 1,234,567 tokens
- Total Saved: 876,543 tokens (71%)
- Cost Saved: $12.34
```

---

## Status

- **Design**: COMPLETE
- **Specification**: COMPLETE
- **Implementation**: READY FOR SPRINT

---

*Generated by Pi Agent*  
*Date: 2026-04-16 09:15 UTC*
