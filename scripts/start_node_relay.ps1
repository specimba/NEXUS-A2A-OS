# Start Node.js ModelRelay on port 7350 (leaves 7352 free for Brain API)
param(
    [int]$Port = 7350,
    [string]$ConfigPath = "$env:USERPROFILE\.modelrelay.json"
)

$nodeRelay = "$env:APPDATA\npm\node_modules\modelrelay\bin\modelrelay.js"

if (-not (Test-Path $nodeRelay)) {
    Write-Error "Node ModelRelay not found at $nodeRelay"
    Write-Error "Install with: npm install -g modelrelay"
    exit 1
}

Write-Host "🚀 Starting NEXUS ModelRelay on port $Port..."
Write-Host "   Config: $ConfigPath"
Write-Host "   API:    http://localhost:$Port/v1"
Write-Host "   Web UI: http://localhost:$Port"
Write-Host ""

node $nodeRelay --port $Port --config $ConfigPath
