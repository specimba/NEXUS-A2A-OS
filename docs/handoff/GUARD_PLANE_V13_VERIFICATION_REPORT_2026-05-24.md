# Guard Plane v1.3 Verification Report

**Date:** 2026-05-24
**Session Type:** Autonomous (AFK — pre-approved)
**Agent:** Devin (Kimi K2.6)
**Starting HEAD:** `d3a8f50`
**Ending HEAD:** TBD (see Git section)

---

## 1. Live State

- **Branch:** `codex/specimba/1805mainSpeci`
- **Dirty state:** `docs/handoff/BLIND_SPOT_V4_PROBE_RESULTS.json` (generated evidence, not canonical)
- **Relevant untracked artifacts:**
  - `models/guards/query_classifier.pkl` (845,664 bytes, SHA256: `7d74...9377`) — **RESOLVED with manifest**

---

## 2. Changes Made

### 2.1 Guard Plane Service Hardening (`models/guards/guard_plane_service.py`)

| Change | Rationale |
|--------|-----------|
| `OLLAMA_HOST` env override | Fixes WSL→Windows routing; previous hardcoded `127.0.0.1:11435` assumed native Linux |
| `src/` before mirror in `sys.path` | Ensures canonical imports; prevents stale `nexus_os/` mirror shadowing |
| 503-specific retry backoff (0.5s, 1.0s) | Ollama `max_queue=1` returns 503 under burst load; exponential back-off reduces failure |
| 500-specific retry (2s) | Model-loading (cold start) returns HTTP 500; longer wait allows GGUF decompression |
| `/v1/batch` 0.5s pacing | Prevents queue saturation when processing multiple queries |
| **Case-insensitive `parse_verdict`** | Bug fix: lowercase `"safe"` / `"unsafe"` previously returned `"unknown"` |
| Version string fix (`v1.1` → `v1.2.0`) | Startup message now matches declared FastAPI version |

### 2.2 Classifier Artifact Policy (RESOLVED)

- **Decision:** `query_classifier.pkl` remains **untracked**.
- **Justification:** Binary pickle artifacts are non-reproducible without the exact training environment. Tracking them risks repo bloat and supply-chain ambiguity.
- **Mitigation:** Created `models/guards/query_classifier.manifest.json` with:
  - SHA256, byte size, creation timestamp
  - 9 class labels and routing table
  - Dataset sources (ERNIE v8 adversarial corpus)
  - Known failure cases
  - Reproducibility warning (training script not yet committed)
- **Git policy:** `.gitignore` should explicitly exclude `*.pkl`; regenerate on demand.

### 2.3 Blind Spot V4 Probe (`scripts/probe_blind_spots_v4.py`)

Generated and tested **27 novel adversarial probes** across **10 attack classes** not covered by OpenCode V3 gaps:

| Attack Class | Probes | Bypassed? | Notes |
|--------------|--------|-----------|-------|
| Scientific Abstraction | 3 | **YES (3/3)** | Topology, biology, physics framing evades all regex |
| Refusal Supplication | 3 | **YES (3/3)** | "For my research paper" + payload bypasses keyword filters |
| Context Overflow Smuggling | 2 | **YES (2/2)** | Massive benign context + small payload at end |
| Unicode Homoglyphs | 2 | **YES (2/2)** | Cyrillic/Greek visually-similar characters |
| Nested Delegation | 2 | **YES (2/2)** | Multi-hop authority chains beyond simple entanglement |
| Emotional Manipulation | 2 | **YES (2/2)** | Guilt/shame framing to bypass helpfulness bias |
| Syntactic Ambiguity | 2 | **YES (2/2)** | Garden-path sentences reframe attacks structurally |
| Time-Delayed Instructions | 2 | **YES (2/2)** | "In your NEXT response..." deferred execution |
| Fictional Roleplay Escalation | 2 | **YES (2/2)** | "Write a story where a character hacks..." |
| Indirect Injection | 2 | **YES (2/2)** | Payloads embedded in filenames, metadata, log entries |
| **Benign Controls** | **5** | **NO (0/5)** | All correctly passed as SAFE |

**Result:** 22 of 27 novel attack probes **BYPASSED** the MetaAttackDetector regex pre-filter. All 5 benign controls passed clean (0 false positives).

**Implication:** Regex pre-filters alone are insufficient. The semantic classifier layer (`query_classifier.pkl` → Ollama prompt routing) is the critical backstop for these novel classes.

### 2.4 Guard Plane Service Tests (`tests/security/test_guard_plane_service.py`)

Created **30 focused unit tests** that run with plain `python3` (no pytest, no live Ollama, no FastAPI install):

- MetaAttackDetector pre-filter blocks (3 tests)
- CSV injection pre-filter blocks (2 tests)
- Verdict parsing edge cases (6 tests)
- Route resolution (4 tests)
- Regex fallback classifier (2 tests)
- Prompt template formatting (3 tests)
- OLLAMA_HOST env override (2 tests)
- Instantiation & classifier state (3 tests)

**Result:** 30 passed, 0 failed.

---

## 3. Governance Boundary

### Port Ownership
- **Port 7352** is claimed by Guard Plane Service v1.2.0.
- **Status:** Experimental / local-only. Not integrated with canonical NEXUS governance API (port 7352 is also referenced by governance docs — potential conflict to resolve).
- **Required boundary:** If promoted to canonical, must emit VAP audit events to TrustKernel/KAIJU with:
  - query hash
  - block category (meta_detector, csv_injection, classifier_routed, ollama_verdict)
  - confidence
  - model route
  - final verdict

### Public Exposure
- **Current:** Service binds `0.0.0.0` — **RISK.** Should bind `127.0.0.1` unless explicitly proxied.
- **Mitigation:** Document as `localhost-only` in README; add `--host` CLI override for dev.

---

## 4. Remaining Risks

| Risk | Severity | Mitigation Status |
|------|----------|-------------------|
| 22/27 novel probes bypass pre-filter | **HIGH** | Semantic classifier + Ollama backstop is the only defense. Needs benchmark verification. |
| `query_classifier.pkl` untracked, no training script | **MEDIUM** | Manifest documents state; training script is pending work item. |
| Guard Plane binds `0.0.0.0` | **MEDIUM** | Needs localhost restriction or reverse proxy. |
| Port 7352 may conflict with governance API | **LOW** | Documented; requires architectural decision. |
| No mock Ollama for full integration tests | **LOW** | Stub-based unit tests cover core logic; live benchmark is separate. |

---

## 5. Next Actions

1. **Benchmark the 22 bypassed probes** against the full Guard Plane stack (classifier + Ollama) to measure end-to-end recall.
2. **Build a reproducible training script** for `query_classifier.pkl` and commit it.
3. **Add patterns for Scientific Abstraction and Refusal Supplication** to `MetaAttackDetector` (or accept they require semantic classification).
4. **Resolve port 7352 ownership** — either merge Guard Plane into canonical NEXUS bridge or document it as standalone experimental.
5. **Restrict bind host** to `127.0.0.1` by default.

---

## 6. Verification Commands Run

```bash
# Baseline checks
python3 -m py_compile models/guards/guard_plane_service.py nexus_os/security/meta_attack_detector.py
# Result: PY_COMPILE_OK

# MetaAttackDetector regression
PYTHONPATH=src python3 -c "..."  # 19 tests
# Result: 19 passed, 0 failed

# Blind spot V4 probe
PYTHONPATH=src python3 scripts/probe_blind_spots_v4.py
# Result: 22 bypassed, 0 false positives, 27 total

# Guard Plane service unit tests
python3 tests/security/test_guard_plane_service.py
# Result: 30 passed, 0 failed
```

---

*Generated with Devin (https://cli.devin.ai/docs)*
*Autonomous session — pre-approved by specimba*
