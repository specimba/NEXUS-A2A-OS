# NEXUS Browser-AI Supervisor Reset - 2026-06-25

## Decision
NEXUS should not use frequent Codex heartbeat browser loops for Grok, Zo, GLM/Z.ai, or GPT-browser sources. The frequent lane is a local NexusClaw browser-AI supervisor that reads durable JSONL memory first, fingerprints visible browser/source state, and calls free/cheap providers only on material deltas.

## Cadence Rules
- Grok project supervisor: 10 minutes, only when the dedicated CDP profile and `7354` MCP bridge are healthy.
- Zo Computer, GLM-5.2/Z.ai, GPT-browser MCP, and other private browser sources: 6 hours by default unless operator-supervised.
- Unknown browser sources are inactive-safe: no run until a profile is explicitly added.

## Provider Rules
- `NOOP_UNCHANGED` means zero provider calls.
- Setup blockers such as missing CDP, wrong target, missing connector tools, or bridge down mean zero provider calls.
- Retryable bridge timeouts stay local and do not call providers.
- New artifact or material delta permits one provider evaluation max.
- Provider cooldown remains 20 minutes, with a max of three calls per hour per source.

## Bridge Rules
- `7352` is Brain API only.
- `7354` is the browser/Grok MCP bridge and may expose `ping`, `registry_debug`, `http_diagnostic`, `task_add`, session, evidence, and coordination tools.
- Public exposure must use a dedicated tunnel to `7354 /sse`; do not reuse `7352` for MCP or dashboard work.
- `http_diagnostic` is a governed public egress probe, not a general proxy: public GET/HEAD only, private targets blocked, sensitive headers stripped.

## Provider Additions
- InternAI remains preserved as an existing wired lane.
- LongCat remains a gated lane with dry/live checks and 429 backoff behavior.
- OpenModel/DeepSeek V4 Flash is added as an env-keyed provider lane with no tracked secrets.
- Sakana/Fugu and Fugu Ultra are added as env-keyed provider lanes with no tracked secrets.

## Research Intake
- Papers09 support remains active.
- Papers10 starts as E0 filename/backlog evidence and only promotes to E1 when a body-derived claim, path/hash, lane, and adoption gate exist.
- Behavior-control model labels remain denied from normal routing and allowed only in governed lab contexts.

## Verification
Executed focused reset gate on 2026-06-25:

```powershell
python -m pytest tests\bridge\test_browser_http_diagnostic.py tests\mcp\test_egress_governor.py tests\tools\test_grok_mcp_server_v2_static.py tests\tools\test_external_browser_ai_director.py tests\tools\test_external_browser_ai_director_cli.py tests\test_openmodel_sakana_provider_config.py tests\test_internai_provider_config.py tests\test_longcat_provider_config.py tests\research\test_papers09_source_cards.py tests\models\test_registry_roles.py tests\nexusclaw\test_model_intake.py -q --tb=short
```

Result: `84 passed, 1 warning`.

Known warning: pytest cache cannot write under `.tmp\pytest_cache` due Windows access denial. Test assertions passed.

## Git Blocker
Current `origin` was previously observed as `specimba@gmail.com:<specimba>/nexusalpha.git`, which causes SSH to `gmail.com:22`. Use the valid GitHub remote before push, or push through an already valid remote. Do not blind-push from the bad `origin`.
