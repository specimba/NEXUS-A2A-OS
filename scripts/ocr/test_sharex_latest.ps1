<#
.SYNOPSIS
  Auto-test NEXUS OCR on the newest ShareX screenshot (this month folder).
.DESCRIPTION
  Picks latest file by LastWriteTime under ShareX\Screenshots\YYYY-MM,
  ensures :7360 is up (starts GPU service if needed), runs fast + detailed,
  writes report under scratch\screenshots\sharex_auto_*.txt

  Run FROM NEXUS repo root:
    powershell -ExecutionPolicy Bypass -File .\scripts\ocr\test_sharex_latest.ps1
#>
$ErrorActionPreference = "Continue"
$Repo = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path } else { "C:\Users\speci.000\Documents\NEXUS" }
$Month = Get-Date -Format "yyyy-MM"
$Share = "C:\Users\speci.000\Documents\ShareX\Screenshots\$Month"
if (-not (Test-Path $Share)) {
  $Share = "C:\Users\speci.000\Documents\ShareX\Screenshots\2026-07"
}
$Client = Join-Path $Repo "scripts\ocr\ocr_client.py"
$StartPs1 = Join-Path $Repo "scripts\ocr\start_ocr_gpu.ps1"

Write-Host "ShareX dir: $Share"
# Images only - ignore .ocr.json / .ocr.txt sidecars and other non-images
$imgExt = @(".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")
$latest = Get-ChildItem $Share -File -ErrorAction Stop |
  Where-Object { $imgExt -contains $_.Extension.ToLowerInvariant() } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if (-not $latest) { throw "No image files in $Share (looked for: $($imgExt -join ', '))" }
Write-Host "LATEST: $($latest.FullName)"
Write-Host "LastWrite: $($latest.LastWriteTime)  Size: $($latest.Length)  Ext: $($latest.Extension)"

try {
  $h = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 5
  Write-Host "HEALTH: device=$($h.device.device) tier=$($h.device.ocr_tier) det=$($h.device.det_model)"
} catch {
  Write-Host "Starting OCR GPU service..."
  & powershell -ExecutionPolicy Bypass -File $StartPs1
  Start-Sleep 8
  $h = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 15
}

$env:PYTHONIOENCODING = "utf-8"
$report = Join-Path $Repo ("scratch\screenshots\sharex_auto_" + (Get-Date -Format "yyyyMMddTHHmmss") + ".txt")
New-Item -ItemType Directory -Force -Path (Split-Path $report) | Out-Null

function Invoke-OcrMode([string]$mode, [int]$timeout) {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $out = & python $Client $latest.FullName --mode $mode --timeout $timeout 2>&1 | ForEach-Object { "$_" }
  $sw.Stop()
  return @{ mode = $mode; ms = $sw.ElapsedMilliseconds; text = ($out -join "`n") }
}

$fast = Invoke-OcrMode "workspace" 300
$det = Invoke-OcrMode "detailed" 300

# Re-sample health after OCR so tier/det reflect loaded models
try {
  $h = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 5
} catch { }

@"
ShareX auto OCR test
shot=$($latest.FullName)
lastwrite=$($latest.LastWriteTime)
size=$($latest.Length)
device=$($h.device.device)
tier=$($h.device.ocr_tier)
det=$($h.device.det_model)
rec=$($h.device.rec_model)
fast_tier=$($h.device.fast_tier)
detailed_tier=$($h.device.detailed_tier)
budget_gb=$($h.device.mem_budget_gb)
models_fast=$($h.models.fast) models_struct=$($h.models.struct)
fast_ms=$($fast.ms)
detailed_ms=$($det.ms)

--- FAST ---
$($fast.text)

--- DETAILED ---
$($det.text)
"@ | Set-Content -Path $report -Encoding UTF8

Write-Host "fast_ms=$($fast.ms)  detailed_ms=$($det.ms)"
Write-Host "REPORT=$report"

# Wire OCR facts into local continuity (SESSION_PROGRESS / MISSION_STATUS)
$Cont = Join-Path $Repo "scripts\ocr\ocr_to_continuity.py"
if (Test-Path $Cont) {
  & python $Cont --source-image $latest.FullName 2>&1 | ForEach-Object { Write-Host $_ }
  $sess = Join-Path $Repo "scratch\continuity\SESSION_PROGRESS_LATEST.md"
  $miss = Join-Path $Repo "scratch\continuity\MISSION_STATUS.md"
  if (Test-Path $sess) {
    Write-Host "--- SESSION_PROGRESS_LATEST head ---"
    Get-Content $sess -TotalCount 25 -Encoding UTF8
  }
  if (Test-Path $miss) {
    Write-Host "--- MISSION_STATUS head ---"
    Get-Content $miss -TotalCount 20 -Encoding UTF8
  }
}

$latestTxt = Join-Path $Repo "scratch\screenshots\OCR_RESULT_LATEST.txt"
if (Test-Path $latestTxt) {
  Write-Host "--- OCR_RESULT_LATEST head (cleaned) ---"
  Get-Content $latestTxt -TotalCount 40 -Encoding UTF8
  Write-Host "--- end head ---"
}
