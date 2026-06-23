# NEXUSCLAW Design — Native NEXUS Claw System (replaces NemoClaw install)

**Source:** NEXUS-CLAW-01.txt L138-218 + live tree `nexus_os/claw/`  
**Status:** Active design artifact — replace any prior NemoClaw plan with this.

---

## 1. Decision Rationale — Why NemoClaw Was Rejected

NemoClaw install carries 12 unresolved collisions with NEXUS. NEXUSCLAW eliminates every collision by being native rather than bolted on.

| Collision | NemoClaw | NEXUSCLAW |
|:---|:---|:---|
| #1 OS drift | blocker | none — our code |
| #2 port 11434 | workaround 11436 | uses NEXUS 11434 |
| #3 WSL2 lifecycle | watchdog needed | NEXUS systemd already has it |
| #4 GPU exclusivity | race condition | NEXUS Ollama is the only one |
| #5 trust boundary | MCP egress, no identity | in-process TrustKernel ID, no boundary |
| #6 x86 vs ARM | skip cloudflared | native |
| #7 cgroup | unknown | NEXUS Docker already tested |
| #8 "AS IS demo" | NVIDIA's disclaimer | our warranty, our code |
| #9 VAP bloat | unproven at scale | already designed for this in v2.2 |
| #10 KAIJU latency | network round-trip | in-process, <1ms |
| #11 in-flight Ollama | race | NEXUS owns Ollama lifecycle |
| #12 cache fragmentation | duplicate | single cache |

12/12 collisions resolved. NemoClaw fits a generic team without governance. We have governance. We need a claw that speaks NEXUS natively. *(NEXUS-CLAW-01.txt: L140-153)*

---

## 2. Architecture Diagram — Reuses + Native Components

```
nexus_os/claw/
├── __init__.py            — package root, v0.1.0
├── exceptions.py          — structured ClawError hierarchy
├── elicitation.py        — MCP ctx.elicit() param resolution (ElicitationGuard)
├── locks.py              — SessionWriteLock (msvcrt/fcntl, ~/.openclaw/agents/)
├── store.py              — StoreBackend ABC + MemoryStore / FileTreeStore / PreferenceStore
├── tiers.py              — ModelTier + TrustThreshold + classify_model() + ModelTierStore
├── policies/
│   ├── validator.py      — policy enforcement (gates actions)
│   └── presets/          — canned policy profiles
├── security/
│   ├── config_integrity.py — file-hash integrity (pin + verify)
│   └── secret_scanner.py   — pre-write secret detection, blocks egress
├── runners/
│   ├── runner.py         — agent execution backbone
│   └── retry.py          — back-off / retry wrapper
└── [planned] agent.py / sandbox.py / governance.py / audit.py / cli.py

REUSES (not rewrite):
├── OpenClaw  (340K★) — agent loop patterns
├── OpenShell (NVIDIA) — Landlock/seccomp/netns reference
├── Hermes Agent (Nous) — self-improving + TUI
└── NEXUS core — TrustKernel, VAP, Vault, KAIJU
```

*(Live tree verified 2026-06-18; placeholder modules from plan become active append-only extensions.)*

---

## 3. Module Contracts — `nexus_os/claw/` Live Tree

### `exceptions.py`
- `ClawError(message, **context)` — base; carries structured context dict.
- `SubprocessError(command, stderr, stdout, returncode)` — non-zero exit.
- `SubprocessTimeoutError(timeout)` — wall-clock exceed.
- `CLINotFoundError` — binary missing on PATH.
- `ParseError` — tool output unparseable.
- `RetryableError(http_status, retry_after)` — HTTP 429 / 503, safe to back-off.
- `PolicyError` / `PolicyDeniedError` / `PolicyNotApprovedError` — policy gate failures; `PolicyNotApprovedError` blocks until human approval.
- `ConfigIntegrityError` — pinned-hash mismatch.
- `SecretDetectedError` — secret in egress; write blocked.
- `LockError` — lock acquisition timeout.
- `UnsupportedAgentError` — unknown agent runtime.

### `locks.py`
- `SessionWriteLock(agent_id, session_key, lock_dir, allow_reentrant)` — OS-level file lock (`msvcrt` Win32 / `fcntl` POSIX).
- Default path: `~/.openclaw/agents/<agent_id>/sessions/<session_key>.lock`
- `acquire(timeout_ms=60000)` → bool; raises `LockError` on timeout.
- `release()` — unlock + unlink `.lock` file.
- Context-manager + `__del__` safety.

### `store.py`
- `StoreBackend` (ABC): `load(collection, key)`, `save(collection, key, value)`, `delete(collection, key)`, `list_keys(collection)`.
- `MemoryStore` — in-process dict; `FileTreeStore` — `~/.openclaw/store/<collection>/<key>.json`; `RedisStore` planned.
- `PreferenceStore` collections: `preferences` (per-agent), `tiers` (`model_map`), `trust` (per-agent ERNIE HARDWALL/CAUTION/RESTRICTED config).

### `tiers.py`
- `ModelTier`: `QUICK` / `STANDARD` / `THOROUGH`.
- `TrustThreshold`: `HARDWALL` / `CAUTION` / `RESTRICTED` (ERNIE Session 13/14 pattern).
- `classify_model(name)` — heuristic regex matching over provider families.
- `estimate_trust_threshold(name)` — QUICK→HARDWALL, THOROUGH→CAUTION, STANDARD→RESTRICTED.
- `ModelTierStore(store)` — persistent overrides via `PreferenceStore`.

### `elicitation.py`
- `ElicitationGuard` (singleton) — suppression flags per session.
- `elicit_cli_selection(fn, options)` — pick CLI tool; fallback first option.
- `elicit_model_selection(fn, models)` — pick model; fallback first.
- `elicit_confirmation(fn, prompt)` — yes/no; fallback `default`.
- `elicit_vague_prompt(fn, original)` — ask for elaboration; fallback original.
- `suppress_all()` — silence all prompts for CLI/headless mode.

### `policies/` (validator + presets)
- Policy enforcement wrapper; gates actions before execution.
- Presets provide canned policy profiles (to be mapped to KAIJU tier outputs).

### `security/`
- `config_integrity.py` — file-hash pinning; write blocked on mismatch.
- `secret_scanner.py` — pre-write scan + `SecretDetectedError`; zero secrets to external channels.

### `runners/`
- `runner.py` — agent execution backbone (invoke CLI, capture output, enforce policy).
- `retry.py` — exponential back-off for transient errors (`RetryableError`).

---

## 4. TrustKernel Identity Integration

Three OsmanClaw agents, each with a NEXUS-native TrustKernel ID:

| Agent | Role | TrustKernel ID | NEXUS channel |
|:---|:---|:---|:---|
| nexus-osmanclaw-1 | orchestrator | `claw-orch-001` | #nexus-control |
| nexus-osmanclaw-2 | reviewer | `claw-rev-002` | #nexus-codex-tasks |
| nexus-osmanclaw-3 | researcher/ops | `claw-res-003` | (task routing) |

Identity flow: TrustKernel ID set at agent spawn, passed in-process to VAP recorder (`audit.py`) and Vault 8-channel memory. No MCP egress boundary — TrustKernel is in the same address space as the Governor/KAIJU gate. *(NEXUS-CLAW-01.txt: L173-178)*

---

## 5. Port / Path / Resource Reconciliation with NEXUS

| Resource | NemoClaw | NEXUSCLAW (this tree) |
|:---|:---|:---|
| Ollama port | 11436 (workaround) | **11434** (NEXUS native) |
| Store base | vendor-defined | `~/.openclaw/store/` (`FileTreeStore`) |
| Lock base | vendor-defined | `~/.openclaw/agents/<agent_id>/sessions/` (`locks.py`) |
| Trust config | MCP-boundary egress | `PreferenceStore.load_trust_config(agent_id)` (in-process) |
| Agent runtime | external | `nexus_os/claw/runners/runner.py` (in-process wrapper) |
| Policy gate | network KAIJU | in-process `policies/validator.py` (target: <1ms) |
| VAP channel | unproven external | NEXUS VAP v2.2 (planned `audit.py`, native append-only) |
| Channels | Telegram / Discord slots | NEXUS channels only (master plan §8); Slack → Zo → NEXUSCLAW only |
| Tunnel | cloudflared required | SSH only (master plan §8) |

---

## 6. Effort Estimate

Lane A → B → C, scoped tight. *(NEXUS-CLAW-01.txt: L211-218)*

| Phase | Deliverable | Estimate |
|:---|:---|:---|
| **Lane A** — Reconcile | 1 design doc (this file) + 1 task doc update | 1–2 h |
| **Lane B** — Active Diagnosis | `sandbox.py` prototype + minimal `agent.py`; prove Landlock + seccomp + netns in WSL2 with 1 test agent | 4–6 h (~200 LoC sandbox) |
| **Lane C** — Isolated Candidate | All 6 modules (`sandbox`, `agent`, `governance`, `audit`, `memory`, `cli`); spawn 3 OsmanClaw agents with TrustKernel IDs; full cycle test Slack/Zo → KAIJU → NEXUSCLAW → VAP → memory | 1–2 days (~1500 LoC) |
| **Tests** | Unit + integration (focus: lock, store, policy, elicitation) | 4–6 h (~600 LoC) |
| **Total** | | **~2300 LoC, ~3 days** |

**What we don't do (deferred / dropped):**
- ❌ NemoClaw install — replaced by this design.
- ❌ cloudflared tunnel — `nexus-os*` over SSH only (master plan §8).
- ❌ Telegram / Discord channels — NEXUS owns channels.
- ❌ OpenClaw as separate runtime — Hermes Agent + NEXUSCLAW sandbox sufficient.
