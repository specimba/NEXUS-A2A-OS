Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Write-Output "=== git log -10 (last 10 commits) ==="
git log -10 --oneline
Write-Output ""
Write-Output "=== files in repo (newest 20) ==="
Get-ChildItem -Recurse -Path docs,artifacts,evidence,assets -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\.git" } | Sort-Object LastWriteTime -Descending | Select-Object -First 20 FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== HF Space README (first 40 lines) ==="
if (Test-Path docs/HF-SPACE-README.md) { Get-Content docs/HF-SPACE-README.md -TotalCount 40 }