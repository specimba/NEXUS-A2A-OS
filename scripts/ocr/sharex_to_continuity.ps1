<#
.SYNOPSIS
  One-shot: newest ShareX image -> workspace OCR -> continuity files.
  Resource-light classical OCR only (no VLM).
#>
$ErrorActionPreference = "Continue"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
$Client = Join-Path $Repo "scripts\ocr\ocr_client.py"
$Cont = Join-Path $Repo "scripts\ocr\ocr_to_continuity.py"
$Start = Join-Path $Repo "scripts\ocr\start_ocr_gpu.ps1"
$Month = Get-Date -Format "yyyy-MM"
$Share = "C:\Users\speci.000\Documents\ShareX\Screenshots\$Month"
if (-not (Test-Path $Share)) {
  $Share = "C:\Users\speci.000\Documents\ShareX\Screenshots\2026-07"
}

$imgExt = @(".png", ".jpg", ".jpeg", ".webp", ".bmp")
$latest = Get-ChildItem $Share -File -ErrorAction Stop |
  Where-Object { $imgExt -contains $_.Extension.ToLowerInvariant() } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if (-not $latest) { throw "No images in $Share" }

Write-Host "LATEST: $($latest.FullName)  $($latest.LastWriteTime)"

try {
  Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 3 | Out-Null
} catch {
  & powershell -ExecutionPolicy Bypass -File $Start
  Start-Sleep 4
}

$env:PYTHONIOENCODING = "utf-8"
# workspace OCR writes continuity once via ocr_client (no double-run)
& python $Client $latest.FullName --mode workspace --timeout 300
if ($LASTEXITCODE -ne 0 -and (Test-Path $Cont)) {
  # Fallback only if client skipped continuity
  & python $Cont --source-image $latest.FullName
}

$facts = Join-Path $Repo "scratch\continuity\OCR_FACTS_LATEST.json"
if (Test-Path $facts) {
  try {
    $j = Get-Content $facts -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host ""
    Write-Host "STATUS=$($j.quality) machine=$($j.facts.machine) nb=$($j.facts.notebook_id) gpu=$($j.facts.gpu_primary)"
  } catch {}
}

Write-Host ""
Write-Host "Continuity:"
Write-Host "  $Repo\scratch\continuity\SESSION_PROGRESS_LATEST.md"
Write-Host "  $Repo\scratch\continuity\MISSION_STATUS.md"
Write-Host "  $Repo\scratch\continuity\OCR_FACTS_LATEST.json"
Write-Host "Intern: copy those three to /data/NEXUS/ when online."
