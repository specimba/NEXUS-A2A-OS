# Intelligent wait: observe Thinking / Thought-for / Zo-is-thinking — never blind-nudge mid-generation.
param(
    [int]$Port = 9224,
    [Parameter(Mandatory = $true)]
    [string]$Required,
    [string]$AgentId = "",
    [ValidateSet("smoke", "handoff", "nudge", "coding", "deep_search", "audit", "paper_review", "general")]
    [string]$TaskClass = "general",
    [int]$BaselineTailLen = 0,
    [int]$MaxWaitSec = 0,
    [int]$PollSec = 4
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
Set-Location $Repo

if (-not $AgentId) {
    if ($Required -match "grok") { $AgentId = "grok" }
    elseif ($Required -match "zo") { $AgentId = "zo" }
    elseif ($Required -match "chatgpt") { $AgentId = "chatgpt" }
    else { $AgentId = $Required }
}

$py = "$Repo\.venv\Scripts\python.exe"
if ($MaxWaitSec -le 0) {
    $MaxWaitSec = [int](& $py -m nexus_os.nexusclaw.lane_timing_cli suggest-wait $AgentId $TaskClass)
}

$waitScript = "$Repo\tools\browser_ai_supervisor\lane_response_wait.mjs"
$nodeArgs = @(
    $waitScript,
    "--port", $Port,
    "--required", $Required,
    "--agentId", $AgentId,
    "--taskClass", $TaskClass,
    "--maxWaitSec", $MaxWaitSec,
    "--pollSec", $PollSec,
    "--baselineTailLen", $BaselineTailLen
)

$waitLog = & node @nodeArgs 2>&1
$waitText = ($waitLog | Out-String)
# Prefer a full JSON object line; fall back to first { ... } span (handles TIMEOUT noise).
$jsonLine = ($waitText -split "`n" | Where-Object { $_.Trim().StartsWith("{") -and $_ -match '"status"' } | Select-Object -Last 1)
if (-not $jsonLine) {
    $start = $waitText.IndexOf("{")
    $end = $waitText.LastIndexOf("}")
    if ($start -ge 0 -and $end -gt $start) {
        $jsonLine = $waitText.Substring($start, $end - $start + 1)
    }
}
if (-not $jsonLine) { throw "lane wait produced no JSON`n$waitText" }
try {
    $payload = $jsonLine | ConvertFrom-Json
} catch {
    throw "lane wait JSON parse failed: $($_.Exception.Message)`nline=$jsonLine`nraw=$waitText"
}

$jsonCompact = $payload | ConvertTo-Json -Compress -Depth 8
try {
    & $py -m nexus_os.nexusclaw.lane_timing_cli record --task-class $TaskClass --json $jsonCompact | Out-Null
} catch {
    Write-Warning "lane_timing_cli record failed (non-fatal): $_"
}

$payload | ConvertTo-Json -Depth 8
if ($payload.status -ne "RESPONSE_READY") { exit 1 }
exit 0