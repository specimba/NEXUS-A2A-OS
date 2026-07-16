param(
    [int]$Port = 7354,
    [string]$HostName = "127.0.0.1",
    [switch]$StartNgrok,
    [string]$AllowedHosts = "huggingface.co,hf.co,cdn-lfs.huggingface.co,raw.githubusercontent.com,github.com,pypi.org,files.pythonhosted.org,grok.com,files.grok.com,modelcontextprotocol.io,arxiv.org,docs.modal.com,modal.com,docs.tailscale.com,docs.anthropic.com,platform.openai.com,ai.google.dev,docs.groq.com,docs.z.ai,longcat.chat,intern-ai.org.cn,deepseek.com,sakana.ai"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$serverPath = Join-Path $PSScriptRoot "grok_mcp_server_v2.py"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($existing) {
    Write-Error "Port $Port is already listening. Stop the existing owner intentionally before starting this bridge."
}

$env:GROK_LISTEN_PORT = [string]$Port
$env:GROK_LISTEN_HOST = $HostName
$env:GROK_HTTP_ALLOWED_HOSTS = $AllowedHosts
$env:GROK_MCP_VERSION = "2.4.0-p0-continuity"

# Port 7354 is the read-only GROSS/MCP plane.  SAGE belongs to the separately
# authenticated Brain/governance ingress on 7352 and must never inherit a
# credential or writable mode into this child process.
$env:NEXUS_SAGE_GATEWAY_MODE = "disabled"
Remove-Item Env:NEXUS_SAGE_API_KEY -ErrorAction SilentlyContinue

Write-Host "Starting hardened Grok MCP bridge on $HostName`:$Port" -ForegroundColor Cyan
$server = Start-Process -WindowStyle Hidden -FilePath $python -ArgumentList @($serverPath) -PassThru -WorkingDirectory $repoRoot
Start-Sleep -Seconds 3

$health = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/health" -TimeoutSec 5
Write-Host "Local health OK: http://127.0.0.1:$Port/health" -ForegroundColor Green
Write-Host $health.Content

if ($StartNgrok) {
    Write-Host "Starting ngrok tunnel for port $Port" -ForegroundColor Cyan
    $ngrok = Start-Process -WindowStyle Hidden -FilePath "ngrok" -ArgumentList @("http", [string]$Port) -PassThru
    Start-Sleep -Seconds 4
    $tunnels = Invoke-RestMethod -Uri http://127.0.0.1:4040/api/tunnels -ErrorAction Stop
    $url = $tunnels.tunnels[0].public_url
    Write-Host "Custom connector URL: $url/sse" -ForegroundColor Yellow
    Write-Host "Public health URL: $url/health" -ForegroundColor Yellow
}

Write-Host "Server PID: $($server.Id)" -ForegroundColor Gray
Write-Host "Use this only as the browser-AI connector facade. Do not expose Brain API 7352." -ForegroundColor Gray

