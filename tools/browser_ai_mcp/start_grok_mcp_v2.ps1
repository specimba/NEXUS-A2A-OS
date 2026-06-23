param(
    [int]$Port = 7354,
    [string]$HostName = "0.0.0.0",
    [switch]$StartNgrok,
    [string]$AllowedHosts = "huggingface.co,hf.co,cdn-lfs.huggingface.co,raw.githubusercontent.com,github.com,pypi.org,files.pythonhosted.org,grok.com,files.grok.com,modelcontextprotocol.io,arxiv.org"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$serverPath = Join-Path $PSScriptRoot "grok_mcp_server_v2.py"

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($existing) {
    Write-Error "Port $Port is already listening. Stop the existing owner intentionally before starting this bridge."
}

$env:GROK_LISTEN_PORT = [string]$Port
$env:GROK_LISTEN_HOST = $HostName
$env:GROK_HTTP_ALLOWED_HOSTS = $AllowedHosts
$env:GROK_MCP_VERSION = "2.2.0-nexus-hardened"

Write-Host "Starting hardened Grok MCP bridge on $HostName`:$Port" -ForegroundColor Cyan
$server = Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList @($serverPath) -PassThru -WorkingDirectory $repoRoot
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
