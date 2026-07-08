# Check if the Studio chrome (PID 6300) is still alive
$studio = Get-Process -Id 6300 -ErrorAction SilentlyContinue
if ($studio) { Write-Output ("Studio chrome PID 6300 ALIVE: title=" + $studio.MainWindowTitle) } else { Write-Output "Studio chrome PID 6300 dead" }
# Check what tab list says on 9222
try { $r = Invoke-RestMethod "http://127.0.0.1:9222/json/list" -TimeoutSec 3; Write-Output ""; Write-Output "=== port 9222 tabs ==="; $r | ForEach-Object { Write-Output ("  tId="+$_.id+" title="+$_.title+" url="+$_.url) } } catch { Write-Output "port 9222 unreachable" }