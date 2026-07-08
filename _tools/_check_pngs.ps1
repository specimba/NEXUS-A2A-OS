Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Write-Output "=== files in media-pack on disk ==="
Get-ChildItem assets/video/media-pack -Recurse | Select-Object Name, Length | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== files in media-pack on git (HEAD) ==="
git ls-tree -r HEAD --name-only | Where-Object { $_ -like "*media-pack*" } | ForEach-Object { git show "HEAD:$_" | Out-File -Encoding utf8 ("$env:TEMP\git_show.txt"); $info = Get-Item "$env:TEMP\git_show.txt" -ErrorAction SilentlyContinue; Write-Output ("  " + $_) }
Write-Output ""
Write-Output "=== actually untracked pngs? ==="
git status -s | Where-Object { $_ -like "*media-pack*" -or $_ -like "*png*" } | ForEach-Object { Write-Output $_ }
Write-Output ""
Write-Output "=== Delete all PNGs from media-pack, even committed ones ==="
$mp = "assets/video/media-pack"
Get-ChildItem $mp -Filter "*.png" -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("DELETING from disk: " + $_.Name + " (" + $_.Length + " bytes)"); Remove-Item $_.FullName -Force }
git rm -rf --cached assets/video/media-pack 2>&1 | Select-Object -Last 5 | Out-String | Write-Output
Write-Output "=== final state of media-pack ==="
Get-ChildItem $mp -Recurse | Select-Object Name, Length | Format-Table -AutoSize | Out-String | Write-Output