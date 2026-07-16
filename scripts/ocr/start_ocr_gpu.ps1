<#
.SYNOPSIS
  Start NEXUS OCR service on GPU with VRAM budget and PP-OCRv6 pins.
  Auto-stops 30s after last OCR; boot grace 120s so first command is not killed.
#>
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$Py = Join-Path $Repo ".venv_ocr_gpu\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  throw "Missing $Py - run install_paddle_gpu.ps1 first"
}

function Stop-NexusOcr {
  try {
    Invoke-RestMethod -Uri "http://127.0.0.1:7360/shutdown" -Method POST -TimeoutSec 3 | Out-Null
    Start-Sleep -Seconds 2
  } catch {}
  try {
    Invoke-RestMethod -Uri "http://127.0.0.1:7360/shutdown" -Method GET -TimeoutSec 3 | Out-Null
    Start-Sleep -Seconds 2
  } catch {}

  Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match "paddle_ocr_service\.py") } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

  try {
    Get-NetTCPConnection -LocalPort 7360 -State Listen -ErrorAction SilentlyContinue |
      ForEach-Object {
        $opid = $_.OwningProcess
        Write-Host "Stopping listener PID $opid on :7360"
        Stop-Process -Id $opid -Force -ErrorAction SilentlyContinue
        Start-Process -FilePath "taskkill.exe" -ArgumentList @("/F", "/PID", "$opid") -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue | Out-Null
      }
  } catch {}
  Start-Sleep -Seconds 1
}

Stop-NexusOcr

try {
  $existing = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 2
  $hasIdle = $null -ne $existing.idle -and $existing.idle.auto_shutdown -eq $true
  if (-not $hasIdle) {
    $pidHint = $existing.pid
    if (-not $pidHint) {
      try { $pidHint = (Get-NetTCPConnection -LocalPort 7360 -State Listen | Select-Object -First 1).OwningProcess } catch {}
    }
    throw @"
Port 7360 is still held by an OLD OCR process (no idle auto-shutdown).
Kill it from THIS Windows user session, then re-run:

  Stop-Process -Id $pidHint -Force

Then:
  powershell -ExecutionPolicy Bypass -File .\scripts\ocr\start_ocr_gpu.ps1
"@
  }
  Write-Host "Existing OCR already has idle auto-stop (pid=$($existing.pid)); reusing it."
  $existing | ConvertTo-Json -Depth 6
  exit 0
} catch {
  if ($_.Exception.Message -match "OLD OCR|still held") { throw }
}

# Use more of the 8GB laptop GPU (was default 3.0 and mostly idle)
$env:NEXUS_OCR_GPU_MEM_GB = if ($env:NEXUS_OCR_GPU_MEM_GB) { $env:NEXUS_OCR_GPU_MEM_GB } else { "5.0" }
# 30s after LAST OCR job ends (not after start)
$env:NEXUS_OCR_IDLE_SEC = if ($env:NEXUS_OCR_IDLE_SEC) { $env:NEXUS_OCR_IDLE_SEC } else { "30" }
# Do not kill while you type the first command after start
$env:NEXUS_OCR_BOOT_GRACE_SEC = if ($env:NEXUS_OCR_BOOT_GRACE_SEC) { $env:NEXUS_OCR_BOOT_GRACE_SEC } else { "120" }
$env:NEXUS_OCR_LANG = if ($env:NEXUS_OCR_LANG) { $env:NEXUS_OCR_LANG } else { "ch" }
$env:NEXUS_OCR_TILE = if ($env:NEXUS_OCR_TILE) { $env:NEXUS_OCR_TILE } else { "auto" }
$env:CUDA_VISIBLE_DEVICES = "0"
$env:FLAGS_allocator_strategy = "auto_growth"

Start-Process -FilePath $Py `
  -ArgumentList @(
    "$Repo\scripts\ocr\paddle_ocr_service.py",
    "--port", "7360",
    "--idle-sec", $env:NEXUS_OCR_IDLE_SEC
  ) `
  -WorkingDirectory $Repo `
  -WindowStyle Hidden

$h = $null
foreach ($i in 1..15) {
  Start-Sleep -Seconds 2
  try {
    $h = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 5
    if ($h.status -eq "ok") { break }
  } catch {
    $h = $null
  }
}
if (-not $h) {
  throw "OCR service did not become healthy on :7360 within ~30s"
}
$h | ConvertTo-Json -Depth 6
if (-not $h.idle -or -not $h.idle.auto_shutdown) {
  throw "Started process but /health has no idle auto-shutdown - wrong binary or old process still bound."
}
Write-Host "OCR GPU started budget=$($env:NEXUS_OCR_GPU_MEM_GB)GB lang=$($env:NEXUS_OCR_LANG) tile=$($env:NEXUS_OCR_TILE)"
Write-Host "Idle: $($env:NEXUS_OCR_IDLE_SEC)s after last OCR | boot grace: $($env:NEXUS_OCR_BOOT_GRACE_SEC)s before first OCR"
Write-Host "Workspace: python .\scripts\ocr\ocr_client.py <real.png> --mode workspace"
Write-Host "ShareX->continuity: powershell -File .\scripts\ocr\sharex_to_continuity.ps1"
Write-Host "Raw dump: add --raw   (do not use literal ... as path)"
Write-Host "Manual stop: Invoke-RestMethod http://127.0.0.1:7360/shutdown -Method POST"
