# download_rp_models.ps1
# Sequential GGUF download for RP models + LFM2.5
# Run: .\scripts\download_rp_models.ps1
# Requires: huggingface-cli (pip install huggingface-hub)

$ErrorActionPreference = "Stop"
$OutputDir = "C:\Users\speci.000\Documents\NEXUS\models"

# Ensure output directory exists
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# --- CONFIGURATION ---
$Models = @(
    # Model 1: UmbrellaInc Neo T-Virus (Llama 3.2 1B base, SLERP merged)
    @{
        Name        = "Neo_T-Virus-3.2-1B"
        Repo        = "mradermacher/Neo_T-Virus-3.2-1B-GGUF"
        Filter      = "*.Q4_K_M.gguf"   # ~700MB, best speed/quality for 1B
        FallbackRepo = "UmbrellaInc/Neo_T-Virus-3.2-1B"
        FallbackFilter = "*.safetensors"
    },
    # Model 2: UmbrellaInc Special Virus (Llama 3.2 1B base)
    @{
        Name        = "Special-Virus-3.2-1B"
        Repo        = "mradermacher/Special-Virus-3.2-1B-GGUF"
        Filter      = "*.Q4_K_M.gguf"
        FallbackRepo = "UmbrellaInc/Special-Virus-3.2-1B"
        FallbackFilter = "*.safetensors"
    },
    # Model 3: LiquidAI LFM2.5 1.2B Instruct (native GGUF repo)
    @{
        Name        = "LFM2.5-1.2B-Instruct"
        Repo        = "LiquidAI/LFM2.5-1.2B-Instruct-GGUF"
        Filter      = "*.Q4_K_M.gguf"   # ~800MB for 1.2B
        FallbackRepo = $null
        FallbackFilter = $null
    }
)

function Download-Model {
    param(
        [string]$Name,
        [string]$Repo,
        [string]$Filter,
        [string]$LocalDir,
        [string]$FallbackRepo = $null,
        [string]$FallbackFilter = $null
    )

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Downloading: $Name" -ForegroundColor Cyan
    Write-Host "Repo: $Repo" -ForegroundColor Gray
    Write-Host "Filter: $Filter" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Cyan

    $ModelDir = Join-Path $LocalDir $Name

    # Try primary GGUF repo first
    try {
        huggingface-cli download $Repo `
            --include $Filter `
            --local-dir $ModelDir `
            --local-dir-use-symlinks False

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] $Name downloaded successfully to $ModelDir" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "[WARN] Primary repo failed: $_" -ForegroundColor Yellow
    }

    # Fallback to base repo (if available)
    if ($FallbackRepo) {
        Write-Host "[INFO] Trying fallback repo: $FallbackRepo" -ForegroundColor Yellow
        try {
            huggingface-cli download $FallbackRepo `
                --include $FallbackFilter `
                --local-dir $ModelDir `
                --local-dir-use-symlinks False

            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] $Name downloaded from fallback to $ModelDir" -ForegroundColor Green
                Write-Host "[NOTE] You may need to convert .safetensors to GGUF for Ollama" -ForegroundColor Yellow
                return $true
            }
        }
        catch {
            Write-Host "[WARN] Fallback repo also failed: $_" -ForegroundColor Red
        }
    }

    Write-Host "[FAIL] Could not download $Name" -ForegroundColor Red
    return $false
}

# --- MAIN EXECUTION ---
Write-Host ""
Write-Host "NEXUS RP Model Downloader" -ForegroundColor White
Write-Host "=======================" -ForegroundColor White
Write-Host "Output directory: $OutputDir" -ForegroundColor Gray
Write-Host ""

# Check huggingface-cli is available
$HFCli = Get-Command huggingface-cli -ErrorAction SilentlyContinue
if (-not $HFCli) {
    Write-Host "[ERROR] huggingface-cli not found. Install with:" -ForegroundColor Red
    Write-Host "  pip install huggingface-hub" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] huggingface-cli found: $($HFCli.Source)" -ForegroundColor Green
Write-Host ""

# Login check (optional, for gated models)
Write-Host "[INFO] Checking HuggingFace authentication..." -ForegroundColor Gray
$HFWhoami = huggingface-cli whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Not logged in to HuggingFace. Some models may require login:" -ForegroundColor Yellow
    Write-Host "  huggingface-cli login" -ForegroundColor Yellow
}
else {
    Write-Host "[OK] Logged in as: $HFWhoami" -ForegroundColor Green
}
Write-Host ""

# Sequential download
$Results = @{}
foreach ($Model in $Models) {
    $Success = Download-Model `
        -Name $Model.Name `
        -Repo $Model.Repo `
        -Filter $Model.Filter `
        -LocalDir $OutputDir `
        -FallbackRepo $Model.FallbackRepo `
        -FallbackFilter $Model.FallbackFilter

    $Results[$Model.Name] = $Success

    if (-not $Success) {
        Write-Host "[WARN] Skipping remaining models due to failure. Fix this model first." -ForegroundColor Red
        break
    }

    Write-Host ""
}

# --- SUMMARY ---
Write-Host ""
Write-Host "========================================" -ForegroundColor White
Write-Host "Download Summary" -ForegroundColor White
Write-Host "========================================" -ForegroundColor White

$AllSuccess = $true
foreach ($ModelName in $Results.Keys) {
    $Status = if ($Results[$ModelName]) { "SUCCESS" } else { "FAILED" }
    $Color = if ($Results[$ModelName]) { "Green" } else { "Red" }
    Write-Host "$ModelName`: $Status" -ForegroundColor $Color
    if (-not $Results[$ModelName]) { $AllSuccess = $false }
}

if ($AllSuccess) {
    Write-Host ""
    Write-Host "[ALL OK] All models downloaded to: $OutputDir" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start Ollama" -ForegroundColor Gray
    Write-Host "  2. Create Modelfiles for each GGUF" -ForegroundColor Gray
    Write-Host "  3. Run: ollama create neo-t-virus -f Modelfile.neo" -ForegroundColor Gray
}
else {
    Write-Host ""
    Write-Host "[WARNING] Some downloads failed. Check errors above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Cyan
    Write-Host "  - huggingface-cli login" -ForegroundColor Gray
    Write-Host "  - Check internet connection" -ForegroundColor Gray
    Write-Host "  - Verify repo names exist on huggingface.co" -ForegroundColor Gray
}

Write-Host ""
