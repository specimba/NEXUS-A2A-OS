# Start the repo-owned governed ModelRelay on port 7350.
[CmdletBinding()]
param(
    [int]$Port = 7350,
    [string]$ConfigPath = "$env:USERPROFILE\.modelrelay.json",
    [string]$Bind = '0.0.0.0'
)

$ErrorActionPreference = 'Stop'
$Runtime = Join-Path $PSScriptRoot 'modelrelay_runtime.ps1'
if (-not (Test-Path -LiteralPath $Runtime)) { throw "ModelRelay runtime launcher missing: $Runtime" }

Write-Host "Starting NEXUS ModelRelay on port $Port"
Write-Host "  Config: $ConfigPath"
Write-Host "  Bind:   $Bind"
& $Runtime -Port $Port -ConfigPath $ConfigPath -Bind $Bind
exit $LASTEXITCODE
