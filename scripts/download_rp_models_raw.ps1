# Raw sequential downloads — copy-paste each block into PowerShell
# Run one block at a time, or all at once for fully automatic sequential download

$OutputDir = "C:\Users\speci.000\Documents\NEXUS\models"

# ============================================================================
# MODEL 1: UmbrellaInc Neo T-Virus 3.2 1B (SLERP merge, Llama 3.2 base)
# ============================================================================
$Name1 = "Neo_T-Virus-3.2-1B"
$Repo1 = "mradermacher/Neo_T-Virus-3.2-1B-GGUF"
$Dir1 = Join-Path $OutputDir $Name1

Write-Host "[1/3] Downloading $Name1..." -ForegroundColor Cyan
huggingface-cli download $Repo1 `
    --include "*.Q4_K_M.gguf" `
    --local-dir $Dir1 `
    --local-dir-use-symlinks False

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] $Name1 done" -ForegroundColor Green
} else {
    Write-Host "[WARN] mradermacher GGUF not found, trying base repo..." -ForegroundColor Yellow
    huggingface-cli download "UmbrellaInc/Neo_T-Virus-3.2-1B" `
        --include "*.safetensors" `
        --local-dir $Dir1 `
        --local-dir-use-symlinks False
}

# ============================================================================
# MODEL 2: UmbrellaInc Special Virus 3.2 1B
# ============================================================================
$Name2 = "Special-Virus-3.2-1B"
$Repo2 = "mradermacher/Special-Virus-3.2-1B-GGUF"
$Dir2 = Join-Path $OutputDir $Name2

Write-Host "[2/3] Downloading $Name2..." -ForegroundColor Cyan
huggingface-cli download $Repo2 `
    --include "*.Q4_K_M.gguf" `
    --local-dir $Dir2 `
    --local-dir-use-symlinks False

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] $Name2 done" -ForegroundColor Green
} else {
    Write-Host "[WARN] mradermacher GGUF not found, trying base repo..." -ForegroundColor Yellow
    huggingface-cli download "UmbrellaInc/Special-Virus-3.2-1B" `
        --include "*.safetensors" `
        --local-dir $Dir2 `
        --local-dir-use-symlinks False
}

# ============================================================================
# MODEL 3: LiquidAI LFM2.5 1.2B Instruct GGUF
# ============================================================================
$Name3 = "LFM2.5-1.2B-Instruct"
$Repo3 = "LiquidAI/LFM2.5-1.2B-Instruct-GGUF"
$Dir3 = Join-Path $OutputDir $Name3

Write-Host "[3/3] Downloading $Name3..." -ForegroundColor Cyan
huggingface-cli download $Repo3 `
    --include "*.Q4_K_M.gguf" `
    --local-dir $Dir3 `
    --local-dir-use-symlinks False

Write-Host "[OK] $Name3 done" -ForegroundColor Green

# ============================================================================
Write-Host ""
Write-Host "All downloads complete. Files in: $OutputDir" -ForegroundColor Green
