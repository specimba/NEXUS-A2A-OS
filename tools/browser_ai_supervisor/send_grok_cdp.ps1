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

# Preflight: collapse duplicate Grok page targets so context probe is READY.
$dedupeJs = "$Repo\tools\browser_ai_supervisor\dedupe_lane_tabs_cdp.mjs"
if (Test-Path $dedupeJs) {
    try {
        $null = node $dedupeJs --port $Port --match 'grok\.com' 2>&1
    } catch {
        Write-Warning "Grok dedupe preflight failed: $_"
    }
}

if (-not $SkipRestore) {
    # ForceShow: make existing CDP Chrome visible for operator observation.
    # Always also run CDP restore (does not launch a new Chrome process).
    & "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -TitleContains "Grok" -SkipEnsure -ForceShow
    try {
        $null = node "$Repo\tools\browser_ai_supervisor\grok_cdp_restore_window.mjs" --port $Port --mode normal --match 'grok\.com' 2>&1
    } catch {
        Write-Warning "CDP restore after ForceShow failed: $_"
    }
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

$sendStarted = (Get-Date).ToUniversalTime().ToString("o")
$directorOut = node "$Repo\tools\browser_ai_supervisor\grok_cdp_director.mjs" @args 2>&1 | Out-String
Write-Host $directorOut
$directorExit = $LASTEXITCODE

$waitPayload = $null
if ($WaitForResponse -and -not $NoWait) {
    $waitOut = & "$Repo\tools\browser_ai_supervisor\wait_lane_response.ps1" -Port $Port -Required "grok.com" -AgentId grok -TaskClass $taskClass -BaselineTailLen $baseline 2>&1 | Out-String
    Write-Host $waitOut
    try { $waitPayload = $waitOut | ConvertFrom-Json } catch { $waitPayload = $null }
}

# Post-send probe for human-readable proof of I/O
$afterProbeRaw = node "$Repo\tools\browser_ai_supervisor\grok_cdp_context_probe.mjs" --port $Port --required grok.com --maxChars 2500 --pickFirst 2>&1 | Out-String
$afterProbe = $null
try { $afterProbe = $afterProbeRaw | ConvertFrom-Json } catch { }

$ledger = $env:NEXUS_CONTINUITY_LEDGER
if (-not $ledger) {
    $ledger = "C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl"
}
$tailSnippet = ""
if ($afterProbe -and $afterProbe.state -and $afterProbe.state.tailText) {
    $tailSnippet = [string]$afterProbe.state.tailText
    if ($tailSnippet.Length -gt 400) { $tailSnippet = $tailSnippet.Substring($tailSnippet.Length - 400) }
}
$rec = [ordered]@{
    ts            = (Get-Date).ToUniversalTime().ToString("o")
    kind          = "lane_send_proof"
    agent         = "send_grok_cdp"
    port          = $Port
    prompt_file   = $PromptFile
    task_class    = $taskClass
    started_at    = $sendStarted
    director_exit = $directorExit
    wait_status   = if ($waitPayload) { $waitPayload.status } else { $null }
    probe_status  = if ($afterProbe) { $afterProbe.status } else { "PROBE_PARSE_FAIL" }
    proof_token   = if ($tailSnippet -match "NEXUS_PROOF_OK") { $true } else { $false }
    tail_snippet  = $tailSnippet
    target_url    = if ($afterProbe -and $afterProbe.target) { $afterProbe.target.url } else { $null }
}
try {
    $dir = Split-Path $ledger -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Add-Content -Path $ledger -Value ($rec | ConvertTo-Json -Compress -Depth 6) -Encoding utf8
    Write-Host "ledger_appended=$ledger"
} catch {
    Write-Warning "ledger append failed: $_"
}

Start-Sleep -Seconds 1
if ($directorExit -ne 0) { exit $directorExit }
if ($WaitForResponse -and -not $NoWait -and $waitPayload -and $waitPayload.status -ne "RESPONSE_READY") { exit 1 }
