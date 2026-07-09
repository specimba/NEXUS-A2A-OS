# GMR / Chimera / Landau–Ginzburg pipeline — 2026-07-09

## What was wrong

1. **Split CLIs** — `python -m nexus_os.cli route|track` existed, but package `python -m nexusctl` (the operator path) had no GMR/Chimera/LG surface.
2. **Cloud tier never selected for ModelRelay** — `cmd_route` hard-coded local tiers only, so live `:7350` execute paths never saw catalogue cloud profiles.
3. **Synthetic cloud profile IDs** — hand-authored `qwen2.5-72b-instruct-bf16` scored as CLOUD but is not a ModelRelay model id → HTTP 404 on execute.
4. **GMR telemetry URL shape** — probed legacy `/api/models` / wrong host assumptions; ModelRelay serves OpenAI `GET /v1/models` with a `data` array.
5. **LG disconnected from route/execute** — tracker only ran as a standalone dry-run CLI, not correlated with Chimera policy/temperature.

## What we shipped

| Piece | Path |
|-------|------|
| Unified pipeline | `nexus_os/gmr/chimera_lg_pipeline.py` |
| Catalogue telemetry fix | `nexus_os/gmr/telemetry.py` |
| Operator CLI | `nexusctl gmr catalogue \| pipeline \| track` |
| `route --execute` cloud tiers | `nexus_os/cli/nexusctl.py` |
| Tests | `tests/gmr/test_chimera_lg_pipeline.py` (5) |

## Honesty contract (LG)

Black-box ModelRelay replies do **not** supply token logits. LG post-pass is **dry-run entropy** driven by Chimera temperature + policy flags (EDT/LEAD/EPR enables). The report always includes an `honesty` field. We do not invent white-box logits from text.

## Live verification (this host)

```text
nexusctl gmr catalogue     → status ok, source :7350/v1/models, count 176
nexusctl gmr pipeline ...  → route cloud/EDT + LG dry-run ok
nexusctl gmr pipeline ... --execute
  → remapped qwen2.5-72b-instruct-bf16 → auto-fastest
  → response GMR_LG_OK via deepseek-ai/deepseek-v4-pro
  → LG dry-run aligned (T=0.6, policy edt)
```

## Hermes (operator choice)

- Default remains **`grok-build-0.1` / `xai-oauth`** (quota).
- `providers.modelrelay.base_url = http://127.0.0.1:7350/v1` stays available for catalogue/routing when switched later.
- Do **not** force Hermes off Grok Build in this slice.

## Operator commands

```powershell
cd C:\Users\speci.000\Documents\NEXUS
.venv\Scripts\python.exe -m nexusctl gmr catalogue
.venv\Scripts\python.exe -m nexusctl gmr track --tokens 32 --category F1.1
.venv\Scripts\python.exe -m nexusctl gmr pipeline "your careful prompt" --track-tokens 32
.venv\Scripts\python.exe -m nexusctl gmr pipeline "short probe" --execute --max-tokens 64
```

## Follow-ups (not done here)

- Demote or remove synthetic hand-authored CLOUD profile from Chimera DEFAULT_PROFILES once generated registry profiles fully cover quality ranking.
- Optional: feed real top-k logprobs into EPR when a provider returns them.
- Continuity ledger population requires full `DirectorRunner` / supervisor with `NEXUS_CONTINUITY_LEDGER` (Hermes CDP notes already correct).
