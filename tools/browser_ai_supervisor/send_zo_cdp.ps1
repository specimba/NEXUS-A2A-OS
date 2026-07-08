param(
    [int]$Port = 9224,
    [string]$PromptFile = "tools\browser_ai_supervisor\prompts\hermes_to_zo_phase2_v1.md",
    [switch]$SkipEnsure,
    [switch]$SkipWait,
    [switch]$SkipRestore,
    [switch]$NoWait,
    [int]$MaxWaitSec = 0,
    [string]$TaskClass = "handoff"
)
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

function Test-CdpUp {
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/json/version" -TimeoutSec 2 | Out-Null
        return $true
    } catch { return $false }
}

if (-not $SkipEnsure) {
    if (-not (Test-CdpUp)) {
        $prof = "$env:LOCALAPPDATA\NEXUS\BrowserAI\ChromeProfile"
        & "$Repo\scripts\start_grok_cdp_9224.ps1" -ProfileDir $prof -Port $Port
        Start-Sleep -Seconds 3
    }
    if (-not (Test-CdpUp)) { throw "CDP port $Port still down" }
    node "$Repo\tools\browser_ai_supervisor\open_zo_tab_cdp.mjs" --port $Port | Out-Null
}

if (-not $SkipWait) {
    $preArgs = @($Repo + "\tools\browser_ai_supervisor\lane_response_wait.mjs", "--port", $Port, "--required", "zo.computer", "--agentId", "zo", "--taskClass", $TaskClass, "--mode", "preidle")
    if ($MaxWaitSec -gt 0) { $preArgs += @("--maxWaitSec", $MaxWaitSec) }
    & node @preArgs 2>&1 | Out-Null
}

$baseline = 0
try {
    $probeRaw = node "$Repo\tools\browser_ai_supervisor\grok_cdp_context_probe.mjs" --port $Port --required zo.computer --maxChars 1500 2>&1 | Out-String
    $baseline = ([int](($probeRaw | ConvertFrom-Json).state.tailText.Length))
} catch { $baseline = 0 }

if (-not $SkipRestore) {
    & "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -TitleContains "specimba|Zo|Grok" -SkipEnsure -ForceShow
}
$pf = Join-Path $Repo $PromptFile
if (-not (Test-Path $pf)) { throw "Missing prompt $pf" }

& node "$Repo\tools\browser_ai_supervisor\grok_cdp_director.mjs" --port $Port --required zo.computer --promptFile $pf --send --operatorFocus

if (-not $NoWait) {
    & "$Repo\tools\browser_ai_supervisor\wait_lane_response.ps1" -Port $Port -Required zo.computer -AgentId zo -TaskClass $TaskClass -BaselineTailLen $baseline
}