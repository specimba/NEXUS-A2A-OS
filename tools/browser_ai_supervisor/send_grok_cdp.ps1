# CDP send to Grok tab (:9224) — iterative short messages (see CDP_LANE_CONVERSATION_STYLES.md).
param(
    [int]$Port = 9224,
    [string]$PromptFile = "",
    [ValidateSet("", "continue", "proceed", "goon", "1", "2", "3", "A", "B", "C")]
    [string]$Nudge = "",
    [switch]$SkipRestore,
    [switch]$WaitForResponse,
    [switch]$NoWait
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

$nudgeMap = @{
    continue = "tools\browser_ai_supervisor\prompts\grok\nudge_continue.md"
    proceed  = "tools\browser_ai_supervisor\prompts\grok\nudge_proceed.md"
    goon     = "tools\browser_ai_supervisor\prompts\grok\nudge_go_on.md"
    "2"      = "tools\browser_ai_supervisor\prompts\grok\nudge_pick_2.md"
    "B"      = "tools\browser_ai_supervisor\prompts\grok\nudge_pick_B.md"
}

if ($Nudge -and $nudgeMap.ContainsKey($Nudge)) {
    $PromptFile = $nudgeMap[$Nudge]
}
if (-not $PromptFile) {
    throw "Grok send needs -PromptFile or -Nudge (continue|proceed|goon|2|B|...)"
}

if (-not $SkipRestore) {
    & "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -TitleContains "Grok" -SkipEnsure
}

$pf = Join-Path $Repo $PromptFile
if (-not (Test-Path $pf)) { throw "Missing $pf" }

$args = @("--port", $Port, "--required", "grok.com", "--send", "--operatorFocus", "--promptFile", $pf)
$baseline = 0
if ($Nudge) {
    $taskClass = "nudge"
} else {
    $taskClass = "handoff"
    if (-not $PSBoundParameters.ContainsKey("WaitForResponse")) { $WaitForResponse = $true }
    $probeRaw = node "$Repo\tools\browser_ai_supervisor\grok_cdp_context_probe.mjs" --port $Port --required grok.com --maxChars 1500 2>&1 | Out-String
    try { $baseline = ([int](($probeRaw | ConvertFrom-Json).state.tailText.Length)) } catch { $baseline = 0 }
}

node "$Repo\tools\browser_ai_supervisor\grok_cdp_director.mjs" @args

if ($WaitForResponse -and -not $NoWait) {
    & "$Repo\tools\browser_ai_supervisor\wait_lane_response.ps1" -Port $Port -Required "grok.com" -AgentId grok -TaskClass $taskClass -BaselineTailLen $baseline
}
Start-Sleep -Seconds 1