Set-Location 'C:\Users\speci.000\Documents\NEXUS'
$ErrorActionPreference = 'Stop'
$paths = @(
  'scripts/start_grok_cdp_9224.ps1',
  'scripts/grok_zo_cdp_lane.ps1',
  'nexus_os/nexusclaw/grok_lane_env.py',
  'tests/nexusclaw/test_grok_lane_env.py',
  'docs/operations/GROK_ZO_CDP_LANE_GIT_SCOPE.md',
  'docs/operations/ZO_CDP_TUNNEL_WINDOWS_2026-07-02.md',
  'tools/browser_ai_supervisor/grok_cdp_paste_submit.mjs',
  'tools/browser_ai_supervisor/grok_cdp_restore_window.mjs',
  'tools/browser_ai_supervisor/run_external_director.ps1',
  'scratch/show_grok_lane_for_passkey.ps1',
  'docs/operations/NEXUS_CDP_ZO_AGENT_S_MUTATION_2026-07-02.md',
  'docs/operations/ZO_BROWSER_NEXUS_A2A_COLLAB_2026-07-02.md',
  'tools/browser_ai_supervisor/prompts/hermes_zo_grok_handoff_v1.md',
  'tools/browser_ai_supervisor/prompts/hermes_zo_grok_handoff_short_v1.md'
)
git add -- $paths
git commit -m "feat(grok-lane): visible CDP default, window restore, Zo A2A ops, director paths" `
  -m "Safe rollback point: Grok passkey lane, visible Chrome, Hermes-Zo handoff." `
  -m "- ASCII-safe launcher; -SilentBackground opt-in only" `
  -m "- restore window + show_grok_lane_for_passkey helper" `
  -m "- run_external_director repo-root cwd + .venv python" `
  -m "- mutation + Zo A2A ops docs; Grok handoff prompts"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git log -1 --format="%H %s"