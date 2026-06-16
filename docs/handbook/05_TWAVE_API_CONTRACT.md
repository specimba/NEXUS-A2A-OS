# TWAVE Wrapper Team API Contract

**Version**: 1.0  
**Date**: 2026-06-14  
**Status**: Production Ready

## Overview

This document defines the API contract between NEXUS OS governance layer and the TWAVE wrapper team. All interactions are governed by trust thresholds and audit logging.

## Architecture Boundaries

```
┌─────────────────────────────────────────────────────┐
│  NEXUS OS (Governance Layer - Port 7352)           │
│  - Trust Engine                                     │
│  - Task Router                                      │
│  - Agent Pool                                       │
│  - Memory Channels (8-channel schema)              │
└────────────────────┬────────────────────────────────┘
                     │
                     │ HTTP/JSON-RPC (Trust-Gated)
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│  TWAVE Wrapper (Execution Layer - Port 7353)       │
│  - Model loading/unloading                          │
│  - VRAM management                                  │
│  - Low-VRAM execution                               │
│  - NO governance internals                          │
└─────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Task Execution

**Endpoint**: `POST /twave/execute`

**Request**:
```json
{
  "task_id": "task-abc123",
  "model_id": "qwen2.5-7b",
  "prompt": "Execute low-VRAM inference...",
  "max_tokens": 512,
  "trust_threshold": 75.0
}
```

**Response**:
```json
{
  "task_id": "task-abc123",
  "status": "completed",
  "output": "Generated text...",
  "tokens_used": 487,
  "execution_time_ms": 1250,
  "blake3_hash": "abc123..."
}
```

**Trust Gate**: Requires trust score ≥ `trust_threshold` (default 75.0)

### 2. Model Status

**Endpoint**: `GET /twave/models/{model_id}/status`

**Response**:
```json
{
  "model_id": "qwen2.5-7b",
  "loaded": true,
  "vram_usage_mb": 4200,
  "last_used": "2026-06-14T10:30:00Z",
  "health": 0.98
}
```

### 3. Health Check

**Endpoint**: `GET /twave/health`

**Response**:
```json
{
  "status": "healthy",
  "active_models": 3,
  "total_vram_mb": 12000,
  "available_vram_mb": 4500,
  "queue_depth": 2
}
```

## Security Requirements

1. **NO Model Weights**: TWAVE must not expose model weights to external teams
2. **NO Secrets**: API keys, vault credentials must never be logged or transmitted
3. **Audit Logging**: All executions logged to NEXUS worklog with BLAKE3 hash
4. **Rate Limiting**: Max 100 req/s per model, 500 req/s total

## Integration Testing

TWAVE team must pass these tests before integration:

```bash
# Run TWAVE contract tests
pytest tests/twave/test_contract.py -v

# Expected output:
# test_execute_with_trust_gate: PASS
# test_model_status_endpoint: PASS
# test_health_check: PASS
# test_rate_limiting: PASS
# test_no_weight_exposure: PASS
```

## Contact

- **NEXUS Team**: nexus-governance@internal
- **TWAVE Team**: twave-wrapper@internal
- **Escalation**: governor-orchestrator@internal