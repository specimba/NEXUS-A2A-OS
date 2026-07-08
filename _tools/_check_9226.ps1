try {
  $r = Invoke-RestMethod -Uri "http://127.0.0.1:9226/json/list" -TimeoutSec 5
  $pages = $r | Where-Object { $_.type -eq "page" }
  Write-Output ("REACHABLE: " + $pages.Count + " page(s)")
  foreach($p in $pages){
    Write-Output ("  ID=" + $p.id + " | TITLE=" + $p.title + " | URL=" + $p.url)
    Write-Output ("  webSocketDebuggerUrl=" + $p.webSocketDebuggerUrl)
  }
} catch {
  Write-Output ("UNREACHABLE: " + $_.Exception.Message)
}