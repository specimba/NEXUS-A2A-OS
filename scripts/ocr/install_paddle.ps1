<#
.SYNOPSIS
    Install PaddleOCR + dependencies for NEXUS OCR pipeline.
.DESCRIPTION
    Installs paddlepaddle (CPU) and paddleocr via pip.
    For GPU support, manually install paddlepaddle-gpu after this script.
#>

$ErrorActionPreference = "Stop"
Write-Host "=== NEXUS PaddleOCR Installer ===" -ForegroundColor Cyan

# Check python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    $py = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $py) {
    Write-Error "Python not found. Install from https://python.org"
    exit 1
}
$py = $py.Source

# Check pip
& $py -m pip --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip not available. Ensure pip is installed."
    exit 1
}

# Install
Write-Host "[1/3] Installing paddlepaddle (CPU)..." -ForegroundColor Yellow
& $py -m pip install paddlepaddle -i https://mirrors.aliyun.com/pypi/simple/

Write-Host "[2/3] Installing paddleocr..." -ForegroundColor Yellow
& $py -m pip install paddleocr -i https://mirrors.aliyun.com/pypi/simple/

Write-Host "[3/3] Verifying installation..." -ForegroundColor Yellow
& $py -c "import paddle; print('Paddle:', paddle.__version__)"
& $py -c "import paddleocr; print('PaddleOCR:', paddleocr.__version__)"

Write-Host ""
Write-Host "=== Install Complete ===" -ForegroundColor Green
Write-Host "Start OCR service with:" -ForegroundColor Cyan
Write-Host "  python scripts\ocr\paddle_ocr_service.py --port 7360"
Write-Host ""
Write-Host "Test with:" -ForegroundColor Cyan
Write-Host "  python scripts\ocr\ocr_pipeline.py --required grok.com --serve"
