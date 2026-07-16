<#
.SYNOPSIS
  Carefully swap CPU paddlepaddle -> GPU paddlepaddle-gpu for NEXUS OCR.
.DESCRIPTION
  - Stops OCR service on :7360
  - Uninstalls CPU paddlepaddle
  - Installs paddlepaddle-gpu 3.3.1 (cu126, cp313 win) from official index
  - Caps OCR VRAM via NEXUS_OCR_GPU_MEM_GB (default 3.0, range 2-4)
  - Restarts OCR service
  - Verifies is_compiled_with_cuda + device
#>
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\speci.000\Documents\NEXUS"
# Prefer dedicated OCR GPU venv (avoids Program Files permission fights)
$Venv = Join-Path $Repo ".venv_ocr_gpu"
$PySys = "C:\Program Files\Python313\python.exe"
$Index = "https://www.paddlepaddle.org.cn/packages/stable/cu126/"
$MemGb = if ($env:NEXUS_OCR_GPU_MEM_GB) { $env:NEXUS_OCR_GPU_MEM_GB } else { "3.0" }

Write-Host "=== NEXUS Paddle GPU install (careful, isolated venv) ===" -ForegroundColor Cyan
Write-Host "OCR VRAM budget GB: $MemGb (service clamps 2-4)"

# 1) Stop OCR listeners
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match "paddle_ocr_service.py" } |
  ForEach-Object {
    Write-Host "Stopping OCR PID $($_.ProcessId)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
Start-Sleep -Seconds 2

# 2) Ensure venv
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) {
  Write-Host "[1/4] Create $Venv ..." -ForegroundColor Yellow
  & $PySys -m venv $Venv
} else {
  Write-Host "[1/4] Venv exists"
}
$Py = Join-Path $Venv "Scripts\python.exe"

# 3) Install GPU wheel + OCR deps into venv only (do not touch system torch)
Write-Host "[2/4] Install paddlepaddle-gpu==3.3.1 + paddleocr into venv..." -ForegroundColor Yellow
& $Py -m pip install -U pip
& $Py -m pip install "paddlepaddle-gpu==3.3.1" -i $Index
if ($LASTEXITCODE -ne 0) { throw "pip install paddlepaddle-gpu failed" }
& $Py -m pip install paddleocr pillow

# 4) Verify CUDA build
Write-Host "[3/4] Verify CUDA compile..." -ForegroundColor Yellow
& $Py -c "import paddle; print('paddle', paddle.__version__); print('cuda_compiled', paddle.is_compiled_with_cuda()); paddle.device.set_device('gpu:0'); print('device', paddle.device.get_device())"
if ($LASTEXITCODE -ne 0) { throw "paddle GPU verify failed" }

# 5) Restart OCR with budget env
Write-Host "[4/4] Restart OCR service :7360 from venv..." -ForegroundColor Yellow
$env:NEXUS_OCR_GPU_MEM_GB = $MemGb
$env:CUDA_VISIBLE_DEVICES = "0"
$env:FLAGS_allocator_strategy = "auto_growth"
Start-Process -FilePath $Py `
  -ArgumentList @("$Repo\scripts\ocr\paddle_ocr_service.py", "--port", "7360") `
  -WorkingDirectory $Repo `
  -WindowStyle Hidden

Start-Sleep -Seconds 8
try {
  $h = Invoke-RestMethod -Uri "http://127.0.0.1:7360/health" -TimeoutSec 20
  $h | ConvertTo-Json -Depth 6
} catch {
  Write-Host "Health not ready yet: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "  Service Python: $Py"
Write-Host "  Budget: NEXUS_OCR_GPU_MEM_GB=$MemGb (~2-4GB)"
Write-Host "  Test: python scripts\ocr\ocr_client.py <png> --mode fast"
