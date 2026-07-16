$ErrorActionPreference = "Continue"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$Client = Join-Path $Repo "scripts\ocr\ocr_client.py"
$Start = Join-Path $Repo "scripts\ocr\start_ocr_gpu.ps1"
$Multi = "C:\Users\speci.000\Documents\ShareX\Screenshots\2026-07\305NHnYtjX.png"
$A100 = "C:\Users\speci.000\Documents\ShareX\Screenshots\2026-07\chrome_xwrSTTQOab.png"

# Force fresh service with ch + tile auto
$env:NEXUS_OCR_LANG = "ch"
$env:NEXUS_OCR_TILE = "auto"
$env:NEXUS_OCR_IDLE_SEC = "120"
& powershell -ExecutionPolicy Bypass -File $Start
if ($LASTEXITCODE -ne 0) { Write-Host "start failed exit=$LASTEXITCODE" }

$env:PYTHONIOENCODING = "utf-8"
$report = Join-Path $Repo ("scratch\screenshots\desktop_ch_" + (Get-Date -Format "yyyyMMddTHHmmss") + ".txt")

function Run-One([string]$label, [string]$path, [string]$mode) {
  Write-Host "=== $label mode=$mode ==="
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $out = & python $Client $path --mode $mode --timeout 600 2>&1 | ForEach-Object { "$_" }
  $sw.Stop()
  return "### $label mode=$mode ms=$($sw.ElapsedMilliseconds)`n$($out -join "`n")"
}

$blocks = @()
$blocks += Run-One "MULTI_APP" $Multi "desktop"
$blocks += Run-One "A100_FOCUS" $A100 "detailed"

$body = @"
Desktop tiling + lang=ch quality test
lang=ch tile=auto

$($blocks -join "`n`n")
"@
$body | Set-Content -Path $report -Encoding UTF8
Write-Host "REPORT=$report"
Write-Host "--- LATEST head ---"
Get-Content (Join-Path $Repo "scratch\screenshots\OCR_RESULT_LATEST.txt") -TotalCount 60 -Encoding UTF8 -ErrorAction SilentlyContinue
