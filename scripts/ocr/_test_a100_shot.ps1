$ErrorActionPreference = "Continue"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$Shot = "C:\Users\speci.000\Documents\ShareX\Screenshots\2026-07\chrome_xwrSTTQOab.png"
$Client = Join-Path $Repo "scripts\ocr\ocr_client.py"
$Start = Join-Path $Repo "scripts\ocr\start_ocr_gpu.ps1"

if (-not (Test-Path $Shot)) { throw "missing shot $Shot" }

try {
  $h = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 4
  if (-not $h.idle -or -not $h.idle.auto_shutdown) {
    Write-Host "Health lacks idle auto-stop; restarting service..."
    & powershell -ExecutionPolicy Bypass -File $Start
    Start-Sleep 8
  } else {
    Write-Host "HEALTH ok pid=$($h.pid) idle=$($h.idle.idle_timeout_s)"
  }
} catch {
  Write-Host "Starting OCR GPU service..."
  & powershell -ExecutionPolicy Bypass -File $Start
  Start-Sleep 8
}

$env:PYTHONIOENCODING = "utf-8"
$report = Join-Path $Repo ("scratch\screenshots\a100_ocr_" + (Get-Date -Format "yyyyMMddTHHmmss") + ".txt")
New-Item -ItemType Directory -Force -Path (Split-Path $report) | Out-Null

function Run-Mode([string]$mode, [int]$timeout) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $out = & python $Client $Shot --mode $mode --timeout $timeout 2>&1 | ForEach-Object { "$_" }
  $sw.Stop()
  return @{ mode = $mode; ms = $sw.ElapsedMilliseconds; text = ($out -join "`n") }
}

$fast = Run-Mode "fast" 180
$det = Run-Mode "detailed" 300
try { $h2 = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 5 } catch { $h2 = $null }

@"
A100 workspace OCR quality test
shot=$Shot
device=$($h2.device.device)
tier=$($h2.device.ocr_tier)
det=$($h2.device.det_model)
rec=$($h2.device.rec_model)
budget_gb=$($h2.device.mem_budget_gb)
fast_ms=$($fast.ms)
detailed_ms=$($det.ms)

--- FAST ---
$($fast.text)

--- DETAILED ---
$($det.text)
"@ | Set-Content -Path $report -Encoding UTF8

Write-Host "fast_ms=$($fast.ms) detailed_ms=$($det.ms)"
Write-Host "REPORT=$report"
Write-Host "--- LATEST cleaned head ---"
Get-Content (Join-Path $Repo "scratch\screenshots\OCR_RESULT_LATEST.txt") -TotalCount 50 -Encoding UTF8 -ErrorAction SilentlyContinue
