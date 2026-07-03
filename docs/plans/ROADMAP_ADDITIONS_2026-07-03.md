# Roadmap Additions & Grounded Milestones — 2026-07-03

**Status:** Operator-approved continuation of `IMPROVEMENT_ROADMAP_2026-07-02.md`.
Completes the grounding synthesis the 2026-07-02 evening session left pending
(its miner findings are folded in here), plus everything learned in the
2026-07-03 Phase-2 execution session.

## 1. State consolidation (what is DONE)

- **Phase 1 (P1-1..P1-10)**: complete as of `0f10fa2d` — all 4 audit CRITICALs,
  relay hardening, governor/KAIJU/nexusclaw fail-closed, CI gate, central
  redaction. Suite was 3714 passed / 21 skipped.
- **Phase 2 (P2-1..P2-7)**: complete as of `acfa5ab0` + done-gate e2e
  (`tests/integration/test_p2_done_gate.py`). Commits: `d248a1ed`, `740f7117`,
  `c98f679a`, `ac561a5f`, `2e4da306`, `8295cb33`, `acfa5ab0`. Details in
  `docs/reviews/FULL_AUDIT_2026-06-29_TRIAGE.md` (Phase 2 section). The novel
  core is now WIRED: real per-token entropy verdicts flow relay → relay_info →
  JSONL → monitor daemon → A2A; one TrustKernel per process with agent_pool
  read-through; channels persist AES-256-GCM encrypted.
- **Provenance note**: P2-1/3/4-tests/7 arrived as an unattributed uncommitted
  working-tree bundle (~04:55 AM 2026-07-03, roadmap-numbered comments, no lane
  log claims it). Operator approved adopt+repair. Repairs the adoption review
  caught: CHD key mismatch (`risk`/`score` vs `risk_level`/`risk_score` — every
  verdict had been "unknown"/0.0), twave spectral recursion + cooling ×0,
  verdict drain race, missing model attribution, judge attribution scramble.

## 2. Concurrent-lane picture (2026-07-03 morning)

| Lane | State | Coordination rule |
|---|---|---|
| CODEX (planning, GPT-5.4) | Built `nexus_os/sentinel/` native recovery subsystem after UiPath AgentHack **disqualification** (had to run on UiPath Cloud; ours ran on Render). 26 files, +2788, **uncommitted**; out of quota until 6:18 AM. | Its files (brain_api.py, port_registry.py, sentinel/*, most src/*, tests/sentinel|bridge) stay untouched until it commits. |
| DeepSeek V4 Pro (backend/relay) | SiliconFlow 12-model config.ts expansion, relay adapter breaker+quota wiring, quota.py sliding-window RPM — **uncommitted**. DPO dedup done (1000→375, imbalanced 247/128). | Relay-layer files (config.ts, model_relay_adapter.py, quota.py) are its lane. |
| HERMES (Ubuntu, grok CDP) | Collab-lock tri-lane observe mode; lane scripts + registry under its git-scope allowlist. bBoN + judge scaffold built, unlaunched. | CDP collision zone off-limits (roadmap P5-4 unchanged). |
| antiGRAV (Gemini IDE) | Branch `codex/specimba/nexus-blind-push` (separate checkout): import_stage fix `7a5c1b14`; internai/longcat adapter configs; WSL HERMES→relay host fix designed, NOT applied. | Different branch; provider JSONs untouched. |

## 3. New milestones (grounded, prioritized)

### M1 — Live local-model verdict demo [BLOCKED: operator]
The done-gate e2e stubs only the model HTTP response because the local Ollama
install is a 72MB cloud-client shell: **no llama-server.exe**, and global
`OLLAMA_HOST=https://ollama.com`. Cloud lanes return no logprobs.
**Operator action:** reinstall full Ollama (or point the relay at any local
OpenAI-compat server with logprobs, e.g. llama.cpp/vLLM). Then: run
`tests/integration/test_p2_done_gate.py` variant against the live model and
archive the first real hallucination verdict.

### M2 — Sentinel-native integration review (after CODEX commits)
When the Sentinel changeset lands: review port-8000 signed-exec/7354-reject
against the port registry ruleset, wire Sentinel case-events into the vault
TASK channel, and consider TrustKernel gating for case transitions. Do NOT
start before CODEX's lane commits its 26-file tree.

### M3 — Phase 3 CLI/CTL ecosystem (roadmap Weeks 3-4, operator priority)
Unchanged from the approved roadmap (P3-1..P3-8). Additions from grounding:
- P3-4 rotate_keys propagation should also cover the new
  `~/.nexus/vault.key` + `NEXUS_VAULT_KEY` introduced by P2-5.
- P3-7 `nexusctl relay verdicts` now has a real data source
  (`~/.nexus/hallucination_verdicts.jsonl` + offset sidecar).
- NEW P3-9: `nexusctl trust` should read the SINGLETON kernel and show
  bootstrap-prior vs evidence-backed state per agent/lane.

### M4 — Track F fine-tune unblock
DPO v1 dedup left 375 unique pairs (247 SAFE / 128 UNSAFE) — **imbalanced**.
Next: dedup-aware balanced re-generation to ~1k unique (pipeline is resumable),
THEN the frozen held-out eval pack (F-2) before any training run.

### M5 — Provider reality maintenance (from DeepSeek probe 7/3)
LIVE: InternAI intern-s2-preview, Groq llama-3.3-70b, Alibaba qwen3-235b,
Ollama Cloud minimax-m3. DEAD/DEGRADED: SiliconFlow (401, key <48h), NIM
GLM-5.1 (410) / MiniMax (degraded) / Kimi-K2 (EOL) / Devstral (404), LongCat,
OpenRouter (402), Cloudflare, Fireworks/DeepInfra/Novita/Baseten.
Actions: registry `models verify` refresh + purge dead entries (roadmap P4-7);
operator: SiliconFlow dashboard key, LongCat beta re-request, OpenModel key.

### M6 — WSL HERMES relay access (coordination-gated)
antiGRAV designed the fix (env-override NODERELAY_URL/MODELRELAY_URL in
hermes.py + WSL-gateway detection in model_relay_adapter.py) but
model_relay_adapter.py carries DeepSeek's uncommitted work. Land AFTER the
DeepSeek lane commits, in ITS lane or with explicit handoff.

## 4. Standing constraints (unchanged)

- No key rotation (operator directive; redaction is the compensating control).
- No push before the operator's history-rewrite decision.
- No parallel NIM-backed calls (429 cascade); tests use mocks/local only.
- Multi-lane commit hygiene: explicit file lists, re-check `git status`+`log`
  before every commit, never sweep other lanes' working-tree files.
