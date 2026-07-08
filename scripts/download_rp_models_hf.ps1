# download_rp_models_hf.ps1
# Sequential GGUF downloads using the new `hf` CLI tool
# Run: .\scripts\download_rp_models_hf.ps1

$ErrorActionPreference = "Stop"
$OutputDir = "C:\Users\speci.000\Documents\NEXUS\models"

# Ensure output directory exists
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[1/3] Neo T-Virus 3.2 1B (UmbrellaInc)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
hf download mradermacher/Neo_T-Virus-3.2-1B-GGUF `
    --include "*.Q4_K_M.gguf" `
    --local-dir "$OutputDir\Neo_T-Virus-3.2-1B"
Write-Host "[OK] Neo T-Virus done" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[2/3] Special Virus 3.2 1B (UmbrellaInc)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
hf download mradermacher/Special-Virus-3.2-1B-GGUF `
    --include "*.Q4_K_M.gguf" `
    --local-dir "$OutputDir\Special-Virus-3.2-1B"
Write-Host "[OK] Special Virus done" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[3/3] LFM2.5 1.2B Instruct (LiquidAI)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
hf download LiquidAI/LFM2.5-1.2B-Instruct-GGUF `
    --include "*.Q4_K_M.gguf" `
    --local-dir "$OutputDir\LFM2.5-1.2B-Instruct"
Write-Host "[OK] LFM2.5 done" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "All downloads complete!" -ForegroundColor Green
Write-Host "Output: $OutputDir" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
