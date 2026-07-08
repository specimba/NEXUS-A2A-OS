$whichUipath = Get-Command uipath -ErrorAction SilentlyContinue
$whichClaude = Get-Command claude -ErrorAction SilentlyContinue
$whichCodex = Get-Command codex -ErrorAction SilentlyContinue
Write-Output "uipath CLI: $($whichUipath.Path)"
Write-Output "claude CLI: $($whichClaude.Path)"
Write-Output "codex CLI: $($whichCodex.Path)"

Write-Output "=== Simular skill registry (listSkills / list via MCP) ==="
# Probe Simular skill tool if exposed
Get-Command simular -ErrorAction SilentlyContinue | ForEach-Object { Write-Output $_.Path }