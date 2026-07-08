Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
if (-not (Test-Path evidence/studio-final)) { New-Item -ItemType Directory -Force -Path evidence/studio-final | Out-Null }
Copy-Item "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\studio-final-0-issues.png" evidence/studio-final/canvas-0-issues.png
git add evidence/studio-final/
git commit -m "Add final Studio canvas screenshot: 0 validation issues, publish gated by trial dialog"
git log -5 --oneline
Write-Output ""
Write-Output "=== final state of play ==="
Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\.git" } | Group-Object { ($_.FullName -split "\\")[0..1] -join "\" } | Select-Object Name, Count | Format-Table -AutoSize