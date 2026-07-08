Write-Output "=== winget ==="
winget --version 2>$null | Out-String | Write-Output
Write-Output ""
Write-Output "=== Python imageio / PIL ==="
python -c "import PIL; print("PIL ok:", PIL.__version__)" 2>$null | Out-String | Write-Output
python -c "import imageio; print("imageio ok:", imageio.__version__)" 2>$null | Out-String | Write-Output
python -c "import cv2; print("cv2 ok:", cv2.__version__)" 2>$null | Out-String | Write-Output
Write-Output ""
Write-Output "=== node ==="
node -e "console.log("node ok")" 2>$null | Out-String | Write-Output
Write-Output ""
Write-Output "=== existing video files ==="
Get-ChildItem C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack\assets\video -Recurse -File | Select-Object FullName, Length | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "=== Live instance summary ==="
Get-Content C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack\artifacts\instance-timeline\SUMMARY.md -Head 30
Write-Output ""
Write-Output "=== Clipboard content (the about-the-project text) ==="
Get-Clipboard | Select-Object -First 5 | Out-String | Write-Output