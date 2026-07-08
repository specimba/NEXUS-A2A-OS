Write-Output "Installing ffmpeg via winget (this may take 1-2 min)..."
winget install --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements --silent 2>&1 | Out-String | Write-Output
Write-Output ""
Write-Output "=== ffmpeg path ==="
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ff) { Write-Output ("ffmpeg found: " + $ff.Source); ffmpeg -version | Select-Object -First 1 } else { Write-Output "ffmpeg NOT in PATH yet - checking standard install paths..."; Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object FullName | Format-Table -AutoSize | Out-String | Write-Output }