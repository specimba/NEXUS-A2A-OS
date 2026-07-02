param(
    [string]$Source = "grok",
    [int]$CdpPort = 9224,
    [string]$RequiredUrlPattern = "grok\.com",
    [string]$RuntimeDir = "scratch\browser_ai_mcp_runtime",
    [switch]$RequiresBridge,
    [string]$EgressProbeUrl = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $RepoRoot

if ($Source -ne "grok") {
    throw "Only Source=grok is wired in V0."
}

$python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$runtime = if ([IO.Path]::IsPathRooted($RuntimeDir)) { $RuntimeDir } else { Join-Path $RepoRoot $RuntimeDir }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

$doctorPath = Join-Path $runtime "director_doctor_$timestamp.json"
$probePath = Join-Path $runtime "director_probe_$timestamp.json"
$memoryPath = Join-Path $runtime "external_director_memory.jsonl"
$doctorScript = Join-Path $RepoRoot "tools\browser_ai_supervisor\control_surface_doctor.ps1"
$probeScript = Join-Path $RepoRoot "tools\browser_ai_supervisor\grok_cdp_context_probe.mjs"
$directorPy = Join-Path $RepoRoot "tools\browser_ai_supervisor\external_browser_ai_director.py"

& $doctorScript -CdpPorts $CdpPort -RequiredUrlPattern $RequiredUrlPattern -Json | Set-Content -Encoding UTF8 $doctorPath

$bridgeStatus = "skipped"
if ($RequiresBridge) {
    try {
        $health = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:7354/health -TimeoutSec 5
        if ($health.StatusCode -eq 200) { $bridgeStatus = "ok" } else { $bridgeStatus = "unhealthy" }
    } catch {
        $bridgeStatus = "down"
    }
}

node $probeScript --port $CdpPort --required Grok --outFile $probePath --maxChars 5000 --maxCodeChars 1000 | Out-Null

$pyArgs = @(
    $directorPy,
    "--probe-json", $probePath,
    "--memory", $memoryPath,
    "--run-id", "director-$Source-$timestamp",
    "--bridge-status", $bridgeStatus
)
if ($RequiresBridge) { $pyArgs += "--requires-bridge" }
if ($EgressProbeUrl) { $pyArgs += @("--egress-url", $EgressProbeUrl, "--egress-method", "HEAD") }

& $python @pyArgs
$directorExit = $LASTEXITCODE
if ($directorExit -eq 0 -and $env:NEXUS_GROUNDING_ROOT) {
    $recordPy = Join-Path $RepoRoot "tools\browser_ai_supervisor\record_grounding_event.py"
    & $python $recordPy --memory $memoryPath --grounding-root $env:NEXUS_GROUNDING_ROOT
}
exit $directorExit