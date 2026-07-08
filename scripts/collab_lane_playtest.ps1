# Tri-lane playtest — inventory by default; pass -Send to dispatch smoke prompt (observe + wait).
param(
    [int]$Port = 9224,
    [switch]$SkipRestore,
    [switch]$Send
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

& "$Repo\scripts\ensure_lane_cdp.ps1" -Port $Port

$prompt = "tools\browser_ai_supervisor\prompts\collab_tri_lane_playtest_v1.md"
$logDir = Join-Path $Repo "NEXUSlogs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $logDir "collab_playtest_$stamp.jsonl"

function Write-Step($phase, $payload) {
    $line = @{ ts = (Get-Date).ToString("o"); phase = $phase; payload = $payload } | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path $log -Value $line
    Write-Host "[$phase]"
}

function Get-TailLen($required) {
    $raw = node "$Repo\tools\browser_ai_supervisor\grok_cdp_context_probe.mjs" --port $Port --required $required --maxChars 2000 2>&1 | Out-String
    try { return [int](($raw | ConvertFrom-Json).state.tailText.Length) } catch { return 0 }
}

function Send-And-Wait($laneRequired, $agentId, $taskClass) {
    $baseline = Get-TailLen $laneRequired
    Write-Step "baseline_$agentId" @{ tailLen = $baseline }
    node "$Repo\tools\browser_ai_supervisor\grok_cdp_director.mjs" `
        --port $Port --required $laneRequired --promptFile $prompt --send --operatorFocus | Out-Null
    $prevEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $waitLines = & "$Repo\tools\browser_ai_supervisor\wait_lane_response.ps1" `
        -Port $Port -Required $laneRequired -AgentId $agentId -TaskClass $taskClass -BaselineTailLen $baseline 2>&1
    $ErrorActionPreference = $prevEa
    $jsonLine = ($waitLines | Out-String) -split "`n" | Where-Object { $_ -match '"status"\s*:\s*"(RESPONSE_READY|TIMEOUT)"' } | Select-Object -Last 1
    $waitObj = if ($jsonLine) { $jsonLine | ConvertFrom-Json } else { @{ status = "WAIT_PARSE_ERROR" } }
    Write-Step "wait_$agentId" $waitObj
    $excerpt = node "$Repo\tools\browser_ai_supervisor\grok_cdp_context_probe.mjs" --port $Port --required $laneRequired --maxChars 1500 2>&1 | Out-String
    Write-Step "probe_$agentId" @{ excerpt = $excerpt.Substring(0, [Math]::Min(1200, $excerpt.Length)) }
    return $waitObj
}

Write-Step "start" @{ port = $Port; send = [bool]$Send }

if (-not $SkipRestore) {
    & "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -SkipEnsure
}

& "$Repo\scripts\align_browser_lanes.ps1" -Port $Port -SkipEnsure

$t = Invoke-RestMethod "http://127.0.0.1:$Port/json/list"
$pages = $t | Where-Object { $_.type -eq "page" }
Write-Step "inventory" @{
    grok    = @($pages | Where-Object { $_.url -match "grok\.com" }).Count
    zo      = @($pages | Where-Object { $_.url -match "zo\.computer" }).Count
    chatgpt = @($pages | Where-Object { $_.url -match "chatgpt" }).Count
    meta    = @($pages | Where-Object { $_.url -match "meta\.ai" }).Count
    mimo    = @($pages | Where-Object { $_.url -match "xiaomimimo" }).Count
    qwen    = @($pages | Where-Object { $_.url -match "chat\.qwen" }).Count
}

if (-not $Send) {
    Write-Host "INVENTORY_ONLY (no prompts sent). Re-run with -Send when lanes are ready."
    Write-Host "log=$log"
    exit 0
}

Send-And-Wait "grok.com" "grok" "smoke" | Out-Null
Send-And-Wait "chatgpt.com" "chatgpt" "smoke" | Out-Null
Send-And-Wait "zo.computer" "zo" "smoke" | Out-Null

Write-Host "PLAYTEST_OBSERVED_OK log=$log"