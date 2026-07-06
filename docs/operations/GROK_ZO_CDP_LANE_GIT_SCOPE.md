# Grok + Zo CDP lane — git scope (FABLE5 isolation)

**Rule:** Lane work must not ride along with FABLE5 / core-solidify general reworks.

## Allowed paths (lane-only commits)

```
scripts/start_grok_cdp_9224.ps1
scripts/grok_zo_cdp_lane.ps1
scratch/show_grok_lane_for_passkey.ps1
scratch/commit_grok_lane_rollback.ps1
tools/browser_ai_supervisor/grok_cdp_*.mjs
tools/browser_ai_supervisor/run_external_director.ps1
tools/browser_ai_supervisor/prompts/hermes_zo_grok_*.md
tools/browser_ai_supervisor/prompts/grok_*.md
tools/browser_ai_mcp/start_grok_mcp_v2.ps1
tools/browser_ai_mcp/grok_mcp_server_v2.py
nexus_os/nexusclaw/grok_lane_env.py
tests/**/test_grok_lane*.py
docs/operations/*GROK*
docs/operations/*ZO*
docs/operations/GROK_CDP_DIRECTOR_RUNBOOK*.md
docs/operations/NEXUS_CDP_ZO_AGENT_S_MUTATION*.md
```

## Forbidden in lane commits (defer to FABLE5 board)

```
nexus_governance.db
.nexus/governance-rest.db
nexus_os/archivist/**
nexusctl/** (except grok-lane doctor if already lane-owned)
src/lib/modelrelay/**
vendor/**
tests/security/** (unless CDP-specific new file under lane allowlist)
```

## Branch discipline

- Prefer: `lane/grok-zo-cdp` or stay on feature branch but **only** `git add` paths from allowlist above.
- Rollback tag: `lane-grok-zo-73c8e800` (commit `73c8e800`).

## Pre-commit check (manual)

```powershell
cd C:\Users\speci.000\Documents\NEXUS
git diff --cached --name-only | ForEach-Object {
  if ($_ -notmatch '^(scripts/(start_grok_cdp|grok_zo_cdp)|tools/browser_ai_|scratch/show_grok|docs/operations/(GROK|ZO|NEXUS_CDP_ZO|HERMES_GROK|HERMES_NEXUS_MODELRELAY|GROK_CDP)|nexus_os/nexusclaw/grok_lane)') {
    Write-Warning "OUT OF LANE SCOPE: $_"
  }
}
```

## Hermes skill (out of repo)

`~/.hermes/skills/software-development/nexus-bbon/` — backup separately; not mixed into FABLE5 commits.