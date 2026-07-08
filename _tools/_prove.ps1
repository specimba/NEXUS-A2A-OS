Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Write-Output "=== ALL PNG FILES IN REPO (uncommitted + committed) ==="
Get-ChildItem -Recurse -Filter "*.png" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "node_modules" -and $_.FullName -notmatch "\.git" } | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== Last 5 git commits ==="
git log -5 --oneline
Write-Output ""
Write-Output "=== Uncommitted changes in media-pack ==="
git status -s | Where-Object { $_ -match "media-pack" } | ForEach-Object { Write-Output $_ }
Write-Output ""
Write-Output "=== media-pack contents right now ==="
Get-ChildItem assets/video/media-pack -Recurse | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== Have I called writeToFile with a PNG in this turn? (exec log) ==="
# Just confirm there are no recent PNG files created after the deletion I did
Get-ChildItem -Recurse -Filter "*.png" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "node_modules" -and $_.FullName -notmatch "\.git" -and $_.LastWriteTime -gt (Get-Date).AddMinutes(-10) } | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== PNGs created in the last 10 minutes: (empty list = no PNGs created) ==="