# Continuity, Browser-AI, Model-Team Promotion Proposal - 2026-07-09

## Scope
This proposal covers the continuity substrate, Browser-AI anti-token-burn gates, LongCat/Intern provider reconciliation, model-team CLI planning, and Papers12/13 intake infrastructure.

## Commit Plan
1. Continuity substrate and CLI: `nexus_os/continuity/*`, `nexusctl/continuity_cli.py`, `nexusctl/cli.py`, `tests/nexusctl/test_continuity_cli.py`.
2. Browser-AI control hardening: `tools/browser_ai_supervisor/*`, foreground repair scripts, CDP duplicate-target checks, and related tests.
3. Provider/model-team reconciliation: LongCat/Intern docs/scripts/tests plus `nexusctl/model_team_cli.py`.
4. Papers12/13 intake: source-card priority metadata, generalized intake tool, and tests.

## Verification Evidence
- Focused: `python -m pytest tests\nexusctl\test_continuity_cli.py tests\nexusctl\test_model_team_cli.py tests\tools\test_external_browser_ai_director.py tests\grounding\test_automation_scripts.py tests\grounding\test_browser_supervisor_silent.py tests\grounding\test_intake_papers_cli.py tests\research\test_papers09_source_cards.py tests\test_longcat_provider_config.py tests\test_internai_provider_config.py tests\nexusctl\test_model_sync_guards.py tests\model_relay\test_provider_budget.py tests\nexusctl\test_provider_quota_cli.py -q --tb=short -o cache_dir=scratch\pytest-cache-continuity-focused2` -> 91 passed, 1 pytest cache warning.
- Full suite attempted: `python -m pytest tests/ -v --tb=short -o cache_dir=scratch\pytest-cache-continuity` -> 3901 passed, 61 skipped, 98 failed, 181 errors. Failures cluster in existing NexusClaw SQLite/user-profile/vault permission areas; focused slice tests passed.
- CLI smoke: `nexusctl continuity status`, `nexusctl model-team list`, `nexusctl model-team plan --role Planner` returned JSON.
- Papers12/13 smoke: `python tools\grounding\intake_papers.py ... --batch papers12 --batch papers13` discovered and ingested 93 files into scratch with review-required proposal `scratch\papers-intake-smoke\proposals\grounding-ge-88c529c265fe4f7e81c4038e1b65ab77.json`.

## Source Grounding
- LongCat docs confirm `LongCat-2.0`, OpenAI/Anthropic-compatible endpoints, 1M context, 128K max output, and 429 retry-after handling.
- LongCat changelog confirms the 2026-06-30 `LongCat-2.0` release and 30-calendar-day token packs.
- Intern docs confirm `intern-latest -> intern-s2-preview` and `internvl3.5-latest -> internvl3.5-241b-a28b`.
- Chrome remote-debugging docs support the isolated non-default profile on CDP 9224.
- MCP security guidance supports keeping 7354 read-only and allowlisted.

## Source-Card IDs For Review
- Papers12/13 scratch proposal: `grounding-ge-88c529c265fe4f7e81c4038e1b65ab77`.
- Example cards in that proposal include `ge-88c529c265fe4f7e81c4038e1b65ab77`, `ge-e573244ed5254773ba2c63841b7e1b33`, `ge-2c601ac05a64427e869068eefd748559`, `ge-08b562a2ec8c428d838b275cb769cd63`, and `ge-362d2538d5554f57b40e61744f078fc6`.

## Known Gaps
- No live provider calls were made; model-team dispatch remains disabled when quota DB is read-only or balance/expiry is unverified.
- Papers12/13 cards are review-required. Canonical promotion still needs claim-level review and contradiction checks.
- Full suite is not globally green due existing unrelated permission/SQLite failures.
- `scratch/papers-intake-smoke` is generated smoke evidence and should not be committed unless intentionally preserved.

## Rollback
- Revert the four commit groups above independently.
- Remove `NEXUS_CONTINUITY_LEDGER` from Browser-AI scheduled environment if continuity mirror causes scheduler issues.
- Restore foreground repair scripts from previous revision only for manual use; do not reattach them to autonomous scheduler paths.
