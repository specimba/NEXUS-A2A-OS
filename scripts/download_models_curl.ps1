# Alternative download using curl + HuggingFace direct URLs
# Use this if `hf download` hangs at 0B/s

$OutputDir = "C:\Users\speci.000\Documents\NEXUS\models"
if (!(Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

function Download-GGUF {
    param(
        [string]$Repo,
        [string]$Filename,
        [string]$OutPath
    )
    $Url = "https://huggingface.co/$Repo/resolve/main/$Filename"
    Write-Host "Downloading: $Url" -ForegroundColor Cyan
    Write-Host "   -> $OutPath" -ForegroundColor Gray
    curl.exe -L --progress-bar "$Url" -o "$OutPath"
    if ($LASTEXITCODE -eq 0) {
        $Size = (Get-Item $OutPath).Length / 1MB
        Write-Host "   [OK] Downloaded: $([math]::Round($Size, 1)) MB" -ForegroundColor Green
    } else {
        Write-Host "   [FAIL] Download failed" -ForegroundColor Red
    }
}

# [1/3] Neo T-Virus
$Dir1 = "$OutputDir\Neo_T-Virus-3.2-1B"
New-Item -ItemType Directory -Path $Dir1 -Force | Out-Null
Download-GGUF -Repo "mradermacher/Neo_T-Virus-3.2-1B-GGUF" -Filename "Neo_T-Virus-3.2-1B.Q4_K_M.gguf" -OutPath "$Dir1\Neo_T-Virus-3.2-1B.Q4_K_M.gguf"

# [2/3] Special Virus
$Dir2 = "$OutputDir\Special-Virus-3.2-1B"
New-Item -ItemType Directory -Path $Dir2 -Force | Out-Null
Download-GGUF -Repo "mradermacher/Special-Virus-3.2-1B-GGUF" -Filename "Special-Virus-3.2-1B.Q4_K_M.gguf" -OutPath "$Dir2\Special-Virus-3.2-1B.Q4_K_M.gguf"

# [3/3] LFM2.5
$Dir3 = "$OutputDir\LFM2.5-1.2B-Instruct"
New-Item -ItemType Directory -Path $Dir3 -Force | Out-Null
Download-GGUF -Repo "LiquidAI/LFM2.5-1.2B-Instruct-GGUF" -Filename "LFM2.5-1.2B-Instruct.Q4_K_M.gguf" -OutPath "$Dir3\LFM2.5-1.2B-Instruct.Q4_K_M.gguf"

Write-Host ""
Write-Host "Done. Check files in $OutputDir" -ForegroundColor Green
