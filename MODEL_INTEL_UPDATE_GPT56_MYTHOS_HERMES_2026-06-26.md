# Model-Intelligence Update: GPT-5.6 + Mythos + Hermes Wiring — June 26 2026
**Purpose:** Single decision-grade synthesis of C (reasoning-mode tech), A (LoopWM source vs implementation), D (Hermes routing intent from logs), and ARCHIVIST Fable/Mythos deep-research.  
**Audience:** Operator decision-making + direct NEXUS engineering use.

---

## 1. What "Max" and "Ultra" Reasoning Actually Mean (C)

| Mode | Mechanism | When to Use |
|------|-----------|-------------|
| **Standard / Fast** | Single-pass decode | Cheap, high-throughput, routine |
| **Max** | Extended internal deliberation budget; model thinks longer before emitting | Hard problems requiring planning/iteration |
| **Ultra** | **Multi-subagent architecture** — central coordinator decomposes task → parallel subagents → consolidated answer | Long-horizon agentic work, coding, research |

**Technical significance for NEXUS:**
- "Ultra mode" is OpenAI building an internal version of what NEXUS is trying to build externally with OsmanClaw/OpenClaw + A2A. The API surface is the same: task decomposition → parallel execution → result merge.
- This means NEXUS's planned 3-agent stack (orchestrator/code-reviewer/researcher) is architecturally validated by the market leader as the right abstraction.
- The difference: OpenAI's subagents are opaque/black-boxed; NEXUS's would be governed (KAIJU-gated, VAP-audited, Hermes-routed through 7350).

**Cerebras WSE-3 hardware angle:** 750 tokens/s target for Sol in July via Cerebras wafer-scale. For NEXUS ModelRelay, this means if a partner gains access, the cost/latency curve for high-reasoning tasks drops sharply — ChimeraRouter's cost-aware scoring should weight `gpt-5.6-sol` differently once Cerebras-backed inference is available.

---

## 2. LoopWM Paper vs GLM-5.2 Implementation (A)

| Element | Paper (arXiv 2606.18208) | GLM-5.2 `spectral_stability.py` | Verdict |
|---------|--------------------------|---------------------------------|---------|
| Core idea | Recursive transformer loop sharing weights across iterations | `overlay_on_lg_states()` mutates existing `lg_states` in place | Faithful |
| Stability constraint | `A = diag(-exp(a))`, eigenvalues in (-1, 0) | `bound_effective_temperature()` clips + smooths | **Approximation, not exact spectral bound** |
| Zero-order hold | Discrete-time stability guarantee | Not implemented (smoothing is continuous blend) | Missing |
| Guarantee | Provably bounded for arbitrary rollout length | Empirically bounded (smoke test passes) | **Weaker than paper claim** |

**Verdict:** GLM-5.2's implementation is a **pragmatic engineering approximation** of LoopWM — it clips and smooths `t_eff` series rather than enforcing the strict negative-diagonal spectral constraint. For NEXUS's purposes this is fine (the LG tracker's downstream consumers just need bounded values), but don't cite it as "LoopWM-proven." The paper is real, peer-accessible on arXiv since June 2026, and worth reading directly for formal guarantees.

---

## 3. What Hermes Actually Did on Model Routing (D)

From `NEXUSlocalworkspaceHERMESwindowslogs-01.txt` and `NEXUSubuntuHERMESlog-05.txt`:

| Attempt | Command | Result |
|---------|---------|--------|
| 7355 Python relay | `wsl bash -lc 'RELAY_PORT=7355 .venv/bin/python -m nexus_os.relay.model_relay'` | **Failed** — Windows .venv not executable from WSL |
| 7355 via cmd.exe | `cmd.exe /c scripts\\start_python_relay_7355.bat` | **Failed** — Windows PID 6644 already bound to 7355 |
| 7355 via start | `cmd.exe /c start "" /min cmd /c scripts\\start_python_relay_7355.bat` | **Failed** — same bind conflict |
| 7357 config issue | `.modelrelay_7357.json` missing | **Resolved** — file created 06/25 |
| Hermes config | `hermes config set model.base_url` | **Never executed** — proposed but not committed |

**The truth:** Hermes rediscovered the WSL→Windows execution boundary but never closed the loop. The practical path is:
1. Accept Node-only relay (7350 + 7357 working)
2. Demote 7355 to optional (only needed if Python relay has unique adapters)
3. **Actually run** `hermes config set model.base_url http://127.0.0.1:7350/v1`

---

## 4. ARCHIVIST Deep-Read: What the Fable/Mythos Reports Actually Add

### 4.1 claude_fable_mythos_report.md (34 KB, 306 lines)
**Most useful for:** Benchmark comparison, enterprise validation, governance architecture.  
**Key new facts:**
- Fable 5 / Mythos 5 are **the same ~10T parameter model**, different governance envelopes (not different models)
- Fable 5 scores **80.3% on SWE-Bench Pro** vs GPT-5.5's 58.6%
- Stripe migrated 50M-line Ruby codebase in **one day** with Fable 5
- Safeguard routing: cybersecurity/biology queries → Opus 4.8 fallback, not refusal
- <5% of sessions trigger safeguards
- 30-day data retention required

### 4.2 MYTHOSdeep-research-report.md (17 KB, 100 lines)
**Most useful for:** NEXUS governance architecture recommendations.  
**Key NEXUS-specific findings:**
- NEXUS already aligns well with Mythos philosophy: canonical governance boundary (7352), evidence pipelines, bounded release surface
- **Main gap:** NEXUS lacks "formalized release, harness, and telemetry discipline" — exactly what Mythos system card exemplifies
- Recommendation: create **NEXUS Capability & Safeguards Card** for every release
- Recommendation: implement **Mythos-style 24-hour holdback window** for high-capability changes
- Recommendation: standardize **harness cards** for all evaluations (scaffold, sandbox profile, token budget, timeout, etc.)

### 4.3 "Beyond Scale" competitive analysis (50 KB)
**Most useful for:** Strategic positioning, pricing, hardware trends.  
**Key new facts:**
- GPT-5.6 family is strategically positioned as "good/better/best" durable tiers (not numerical variants)
- Sol pricing maintained at GPT-5.5 level ($5/$30) despite capability jump — aggressive market capture
- Terra at $2.50/$15 = "GPT-5.5 performance at half cost"
- Cerebras WSE-3 target: 750 tokens/s for Sol by July 2026
- 1.5M token context window claimed (unverified from primary)
- Prompt caching: 90% read discount, 1.25x write rate, 30-min cache lifetime minimum

---

## 5. ARCHIVIST Gap: What's Still Missing

Despite deep ARCHIVIST search, **no technical paper for `ultra mode` internals** was found. It is described only at the API/blogs level:
- "Central coordinator + subagents"
- "Parallel execution"
- No disclosed architecture, routing algorithm, or failure modes

**What to watch for:** GitHub issues, OpenAI research publications, or Cerebras case studies in July 2026 that might expose the actual subagent orchestration mechanism.

---

## 6. Convergent Action Items for NEXUS

| Priority | Action | Evidence Source |
|----------|--------|-----------------|
| P0 | Wire Hermes → 7350: `hermes config set model.base_url http://127.0.0.1:7350/v1` | Log-05, 12-gap plan |
| P0 | Register Windows Scheduled Task `NexusServiceAutoRevive` for 7350/7356/7357 at logon | Log-05 gap analysis |
| P1 | Add `gpt-5.6-sol/terra/luna` aliases to `.modelrelay.json` (when access available) | ModelRelay adapter spec |
| P1 | Add `reasoning_effort` routing dimension to ChimeraRouter (fast/max/ultra) | GPT-5.6 blog + 12-gap plan |
| P1 | Add cost-aware scoring: SOL=$5/$30, TERRA=$2.50/$15, LUNA=$1/$6 per 1M tokens | Lushbinary + OpenAI Help |
| P2 | Create `nexus_os/model_capability_card.py` schema mirroring Anthropic's release-card discipline | Mythos deep-research report |
| P2 | Implement 24-hour holdback window for high-autonomy changes | Mythos system card pattern |
| P2 | Read LoopWM paper (arXiv 2606.18208) and decide if spectral wrapper needs formal upgrade | GLM-5.2 spectral_stability.py |

---

## 7. Bottom Line

- **GPT-5.6 family is real, access-gated, technically ahead on TerminalBench (91.9%) and CTF (96.7%), with a genuine architectural innovation (ultra mode = multi-subagent orchestration).**
- **Claude Fable 5 / Mythos 5 are real, same 10T model, different governance envelopes. Fable 5 public, Mythos 5 restricted. SWE-Bench Pro 80.3% vs GPT-5.5's 58.6%.**
- **Hermes routing blocker is solvable in one config command** — the expensive reviving workaround was never needed if Hermes had committed to 7350.
- **ARCHIVIST's best addition:** NEXUS governance should copy Mythos's *discipline*, not its capabilities. Create capability cards, holdback windows, harness documentation standards.
- **LoopWM is real, GLM's use is approximate** — smoke-tested but not formally verified against the paper's spectral guarantees.
