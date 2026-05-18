\# 02 — ARCHITECTURE (Canonical v3.0)
**Status**: CODE_CONFIRMED | **Tag**: m3-hardened | **Date**: 2026-04-16

## Core Topology (LOCKED)

BRIDGE (JSON-RPC) → VAULT (S-P-E-W) → ENGINE (Hermes) → GOVERNOR (KAIJU/VAP)

## Component Boundaries

| Pillar | Responsibility | Key Files | Proof |
| --- | --- | --- | --- |
| Bridge | A2A transport, HMAC, Token Headers |  | CODE_CONFIRMED |
| Vault | Memory lifecycle, Trust Scoring | `file vault/manager.py`, `file monitoring/trust_scorer.py` | CODE_CONFIRMED |
| Engine | DAG routing, Hermes Skill Adapter |  | CODE_CONFIRMED |
| Governor | KAIJU Auth, Compliance, VAP Audit | `file governor/base.py`, `file governor/proof_chain.py` | CODE_CONFIRMED |

## Execution Pipeline

- **Hot**: Inline routing, hard-fail (\~ms)
- **Warm**: Event append, reason codes (\~10-50ms)
- **Cold**: Trust smoothing, card refresh (\~s)

## P0 Verified Components

1. **TokenGuard**: Integrated in Bridge & Governor (Hard-stop @ 5000 tokens)
2. **Trust Hot-Path**: O(1) latency scoring (`get_score_hotpath`)
3. **VAP Audit**: SHA-256 L1+L2 Hash Chain (`ProofChain`)