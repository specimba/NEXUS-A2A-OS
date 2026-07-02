# Local mirror of .github/workflows/ci.yml (roadmap P1-9).
# Run before pushing / at the end of a work session:
#   pwsh scripts/ci_local.ps1
$ErrorActionPreference = "Stop"
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

Write-Host "== ruff (runtime-fatal classes) ==" -ForegroundColor Cyan
ruff check nexus_os/ nexusctl/ nexus_cli_ctl/ src/ tests/
if ($LASTEXITCODE -ne 0) { throw "ruff gate failed" }

Write-Host "== pytest (core suite) ==" -ForegroundColor Cyan
python -m pytest tests/ -q -m "not slow" --ignore=tests/benchmarks
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

Write-Host "CI-local green." -ForegroundColor Green
