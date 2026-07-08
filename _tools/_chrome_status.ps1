$chrome = Get-Process chrome -ErrorAction SilentlyContinue | Select-Object Id, MainWindowTitle
Write-Output "Chrome processes:"
$chrome | Format-Table -AutoSize | Out-String | Write-Output
Write-Output ""
Write-Output "Tab list from /json/list endpoint of port 9226:"
try { Invoke-RestMethod http://127.0.0.1:9226/json/list -TimeoutSec 3 | ForEach-Object { Write-Output ("  tId="+$_.id+" title="+$_.title+" url="+$_.url) } } catch { Write-Output "  9226 unreachable" }
Write-Output ""
Write-Output "Tab list from port 9224:"
try { Invoke-RestMethod http://127.0.0.1:9224/json/list -TimeoutSec 3 | ForEach-Object { Write-Output ("  tId="+$_.id+" title="+$_.title+" url="+$_.url) } } catch { Write-Output "  9224 unreachable" }