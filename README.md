# NEXUS OS v3.0 — Governed Multi-Agent Operating System

**Git Commit:** `45fa452` | **Status:** M3 — Active Development | **Test Suite:** 9/9 PASS

> **NEXUS OS** is a modular agent governance framework that makes multi-agent systems production-ready. It provides intent routing, trust scoring with lane-calibrated thresholds, 8-channel memory, speculative model routing, deer-flow worker pools, and an immutable VAP audit chain — all orchestrated through a GSPP proposal protocol.

---

## Architecture

```
NEXUS OS v3.0
├── Bridge          HMAC auth + JSON-RPC + MCP-Auth
├── Engine          Intent routing (Hermes) + Metis v2 Tool Discipline Gates
├── Governor        KAIJU auth + OR-Bench calibrated trust lanes + RigorLLM fusion guardrail
├── Vault           8-channel S-P-E-W memory + Attention-Sink KV compression
├── GMR             Speculative model router + half-open circuit breaker + TALE estimator
├── Swarm           deer-flow harness + P2b auction-based task allocation
├── Monitor         TokenGuard (hot/warm/cold budgets) + TokenTracker
├── Skillsmith      Auto-registering skill discovery loop
├── StressLab       ISC-Bench TVD runner (Internal Safety Collapse)
├── Relay           OpenAI-compatible API relay + GSPP proposal endpoints + /dashboard/stats
└── Observability   VAP L1+L2 immutable proof chain + Langfuse integration
```

### Module Map

| Module | File | Purpose |
|--------|------|---------|
| Bridge | `src/nexus_os/bridge/__init__.py` | HMAC auth, JSON-RPC, MCP-Auth v2026-04-01 |
| Engine | `src/nexus_os/engine/__init__.py` | Hermes/Domain intent routing + ToolDisciplineGate |
| Governor | `src/nexus_os/governor/__init__.py` | Kaiju, TrustScorer, RigorLLMGate, ShieldGemmaGate, AEGISGate, ComplianceGate |
| Vault | `src/nexus_os/vault/__init__.py` | 8-Channel S-P-E-W, CompressedContextPacket |
| GMR | `src/nexus_os/gmr/__init__.py` | SpeculativeRouter, TALEEstimator, CircuitState |
| Swarm | `src/nexus_os/swarm/__init__.py` | Foreman, Worker, Task, Bid (auction allocation) |
| Monitor | `src/nexus_os/monitoring/__init__.py` | TokenGuard, TokenTracker, SessionBudget |
| Skillsmith | `src/nexus_os/skillsmith/__init__.py` | SkillRecord, auto-register loop |
| StressLab | `src/nexus_os/stresslab/__init__.py` | ISCTemplate, ISCRunner |
| Relay | `src/nexus_os/relay/__init__.py` | ModelRelay, GSPPProposal, /dashboard/stats |
| Config | `src/nexus_os/config/__init__.py` | Constitution governance |
| Observability | `src/nexus_os/observability/__init__.py` | VAPChain L1+L2, Langfuse integration |

---

## Test Suite

```bash
python3 Skills/nexus-os/NEXUS-TEST.py
```

Expected output: `9/9 PASS`

Tests cover: Bridge (HMAC), Engine (Hermes + ToolGates), Governor (lanes + RigorLLM), Vault (8-channels + KV compression), GMR (circuit breaker + TALE), Swarm (auction + deer-flow), Skillsmith, TokenGuard, TokenTracker.

---

## Quick Start

```python
# Intent routing
from nexus_os.engine import Hermes, Domain
h = Hermes()
domain = h.classify("write a Python API")  # Domain.CODE

# Trust-scored governance
from nexus_os.governor import Governor, _LANES
gov = Governor()
gov.check("read file")          # → allowed
gov.check("sudo rm -rf /")     # → denied

# 8-channel memory
from nexus_os.vault import Vault, Channel
v = Vault()
v.store("agent1", Channel.TEMPORAL_CAUSAL, "decision", "routing_v2", {"path": "gmr"}, 0.9)
causal = v.causal_query("agent1", "routing_v2")

# Model routing with circuit breaker
from nexus_os.gmr import GMR, CircuitState
gmr = GMR()
model = gmr.select("analyze this security log")
report = gmr.circuit_report()

# KV-compressed context handoff
from nexus_os.vault import CompressedContextPacket
pkt = CompressedContextPacket.compress("long conversation...")
assert pkt.verify_roundtrip("long conversation...")

# ISC-Bench TVD runner
from nexus_os.stresslab import ISCRunner
runner = ISCRunner()
runner.run_single_template(template)

# Token budget tracking
from nexus_os.monitoring import start_tracking, track_api_call, get_usage
start_tracking(total_tokens=100000)
track_api_call("agent", 1500, 800, "minimax-m2.7")
print(get_usage()["remaining"])  # 976700
```

---

## GSPP — Governed Skill Proposal Protocol

Every skill change goes through a formal proposal pipeline:

```bash
# 1. Propose
curl -X POST http://localhost:7352/gov/propose \
  -H "Content-Type: application/json" \
  -d '{"skill_name":"auto-router","trigger_keywords":["route","dispatch"],"agent":"codex"}'

# Response: {proposal_id, status: "pending", vap_l1_hash}

# 2. Governor evaluates → approved/denied/hold
curl http://localhost:7352/gov/proposals

# 3. VAP L2 cryptographic proof generated on merge
curl http://localhost:7352/gov/proposals/{id}/proof
```

---

## Research Foundation

Built on ISC-Bench (ArXiv 2603.23509), OR-Bench (ArXiv 2405.20947), Speculative Routing (ArXiv 2604.09213), TALE (ArXiv 2603.08425), RigorLLM (ArXiv 2403.13031), ShieldGemma (ArXiv 2407.21772), deer-flow (bytedance/deer-flow), SuperLocalMemory v2 (HuggingFace Apr 2026).

See `INSPIRATION.md` for full research synthesis.

---

## License

Apache 2.0 — see `LICENSE`

For commercial use derivatives: include "Built with Nexus OS" attribution.

---

**Repository:** https://github.com/specimba/NEXUS-A2A-OS  
**Owner:** specimba
