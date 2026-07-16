# Prove idle auto-stop on free port 7361 (avoids zombie on 7360 from other sessions).
$ErrorActionPreference = "Continue"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$Py = Join-Path $Repo ".venv_ocr_gpu\Scripts\python.exe"
$Port = 7361

try {
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}
Start-Sleep 1

$env:NEXUS_OCR_GPU_MEM_GB = "3.0"
$env:CUDA_VISIBLE_DEVICES = "0"
Start-Process -FilePath $Py `
  -ArgumentList @("$Repo\scripts\ocr\paddle_ocr_service.py", "--port", "$Port", "--idle-sec", "8") `
  -WorkingDirectory $Repo `
  -WindowStyle Hidden
Start-Sleep 6

$raw = (Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 10).Content
Write-Host "HEALTH_RAW=$raw"
$h = $raw | ConvertFrom-Json
if (-not $h.idle -or [double]$h.idle.idle_timeout_s -ne 8) {
  Write-Host "FAIL: missing idle fields"
  exit 1
}
Write-Host "UP pid=$($h.pid) idle_timeout=$($h.idle.idle_timeout_s) idle_for=$($h.idle.idle_for_s)"
Write-Host "Waiting 12s for idle auto-stop..."
Start-Sleep 12
try {
  Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 3 | Out-Null
  Write-Host "STILL_UP - FAIL"
  exit 2
} catch {
  Write-Host "DOWN_OK - idle auto-stop works"
}
$alive = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match "paddle_ocr_service\.py") -and ($_.CommandLine -match "$Port") }
if ($alive) {
  Write-Host "PROCESS_STILL_ALIVE"
  exit 3
}
Write-Host "PROCESS_GONE_OK"
