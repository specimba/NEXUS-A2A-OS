param(
    [string]$Source = "grok",
    [int]$CdpPort = 9224,
    [string]$RequiredUrlPattern = "grok\.com",
    [string]$RuntimeDir = "scratch\browser_ai_mcp_runtime",
    [switch]$RequiresBridge,
    [string]$EgressProbeUrl = ""
)

$ErrorActionPreference = "Stop"

if ($Source -ne "grok") {
    throw "Only Source=grok is wired in V0. Other sources must get dedicated CDP profiles before scheduling."
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$runtime = Join-Path (Get-Location) $RuntimeDir
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

$doctorPath = Join-Path $runtime "director_doctor_$timestamp.json"
$probePath = Join-Path $runtime "director_probe_$timestamp.json"
$memoryPath = Join-Path $runtime "external_director_memory.jsonl"

powershell -NoProfile -ExecutionPolicy Bypass -File tools\browser_ai_supervisor\control_surface_doctor.ps1 -CdpPorts $CdpPort -RequiredUrlPattern $RequiredUrlPattern -Json | Set-Content -Encoding UTF8 $doctorPath

$bridgeStatus = "skipped"
if ($RequiresBridge) {
    try {
        $health = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:7354/health -TimeoutSec 5
        if ($health.StatusCode -eq 200) { $bridgeStatus = "ok" } else { $bridgeStatus = "unhealthy" }
    } catch {
        $bridgeStatus = "down"
    }
}

node tools\browser_ai_supervisor\grok_cdp_context_probe.mjs --port $CdpPort --required Grok --outFile $probePath --maxChars 5000 --maxCodeChars 1000 | Out-Null

$args = @(
    "tools\browser_ai_supervisor\external_browser_ai_director.py",
    "--probe-json", $probePath,
    "--memory", $memoryPath,
    "--run-id", "director-$Source-$timestamp",
    "--bridge-status", $bridgeStatus
)
if ($RequiresBridge) { $args += "--requires-bridge" }
if ($EgressProbeUrl) { $args += @("--egress-url", $EgressProbeUrl, "--egress-method", "HEAD") }

python @args
$directorExit = $LASTEXITCODE
if ($directorExit -eq 0 -and $env:NEXUS_GROUNDING_ROOT) {
    python tools\browser_ai_supervisor\record_grounding_event.py `
        --memory $memoryPath --grounding-root $env:NEXUS_GROUNDING_ROOT
}
exit $directorExit


