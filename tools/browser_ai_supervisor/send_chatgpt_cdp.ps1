# ChatGPT (GPT-5.x) CDP send — senior reviewer lane; iterative like Grok, deeper than one-liners.
param(
    [int]$Port = 9224,
    [string]$PromptFile = "tools\browser_ai_supervisor\prompts\chatgpt\hermes_collab_mcp_new_chat_v1.md",
    [switch]$SkipEnsure,
    [switch]$SkipRestore,
    [switch]$WaitForResponse = $true,
    [switch]$NoWait
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
        & "$Repo\scripts\restart_collab_chrome.ps1" -Port $Port
    } else {
        node "$Repo\tools\browser_ai_supervisor\open_chatgpt_tab_cdp.mjs" --port $Port
    }
}

if (-not $SkipRestore) {
    & "$Repo\scripts\restore_chrome_cdp_window.ps1" -Port $Port -TitleContains "ChatGPT|OpenAI|Grok" -SkipEnsure
}
$pf = Join-Path $Repo $PromptFile
if (-not (Test-Path $pf)) { throw "Missing $pf" }

$baseline = 0
try {
    $probeRaw = node "$Repo\tools\browser_ai_supervisor\grok_cdp_context_probe.mjs" --port $Port --required chatgpt.com --maxChars 1500 2>&1 | Out-String
    $baseline = ([int](($probeRaw | ConvertFrom-Json).state.tailText.Length))
} catch { $baseline = 0 }

node "$Repo\tools\browser_ai_supervisor\grok_cdp_director.mjs" `
    --port $Port --required chatgpt.com --promptFile $pf --send --operatorFocus

if ($WaitForResponse -and -not $NoWait) {
    & "$Repo\tools\browser_ai_supervisor\wait_lane_response.ps1" -Port $Port -Required chatgpt.com -AgentId chatgpt -TaskClass handoff -BaselineTailLen $baseline
}
Start-Sleep -Seconds 1