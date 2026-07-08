$packDir = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack\assets\video\media-pack"
Write-Output "=== BEFORE: all files in media-pack ==="
Get-ChildItem $packDir -Recurse | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== DELETING blank PNGs (size <= 6KB) ==="
Get-ChildItem $packDir -Filter "*.png" -Recurse | Where-Object { $_.Length -lt 6000 } | ForEach-Object { Write-Output ("DELETE: " + $_.Name + " (" + $_.Length + " bytes)"); Remove-Item $_.FullName -Force }
Write-Output ""
Write-Output "=== AFTER: remaining files ==="
Get-ChildItem $packDir -Recurse | Select-Object Name, Length | Format-Table -AutoSize | Out-String | Write-Output