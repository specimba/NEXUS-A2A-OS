python -c "import PIL; print("PIL ok:", PIL.__version__)" 2>&1 | Out-String | Write-Output
Write-Output ""
Write-Output "=== existing ffmpeg works with simpler test? ==="
ffmpeg -f lavfi -i "color=c=black:s=320x240:d=1" -frames:v 1 -y "C:\Users\speci.000\Documents\NEXUS\_tools\_test.png" 2>&1 | Select-Object -Last 5 | Out-String | Write-Output
if (Test-Path "C:\Users\speci.000\Documents\NEXUS\_tools\_test.png") { Write-Output ("test png: " + (Get-Item "C:\Users\speci.000\Documents\NEXUS\_tools\_test.png").Length + " bytes") }