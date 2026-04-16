# 02 — ARCHITECTURE (Canonical)
**Status**: FILE_CONFIRMED | CODE_CONFIRMED

## Core Topology (LOCKED)
BRIDGE (JSON-RPC) → VAULT (S-P-E-W) → ENGINE (Hermes) → GOVERNOR (KAIJU/VAP)

## Component Boundaries
| Pillar | Responsibility | Key Files |
|---|---|---|
| Bridge | A2A transport, HMAC, tokens | `bridge/server.py` |
| Vault | Memory lifecycle, trust | `vault/manager.py`, `trust.py` |
| Engine | DAG routing, heartbeat | `engine/hermes.py` |
| Governor | KAIJU gate, compliance, VAP | `governor/base.py`, `proof_chain.py` |

## Memory Model (S-P-E-W)
- **Session**: Ephemeral, TTL-pruned
- **Project**: Medium-term, FTS5-indexed
- **Experience**: Compressed paradigms
- **Wisdom**: High-trust promoted records

## Execution Pipeline
- **Hot**: Inline routing, hard-fail (~ms)
- **Warm**: Event append, reason codes (~10-50ms)
- **Cold**: Trust smoothing, card refresh (~s)
