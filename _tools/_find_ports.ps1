foreach($port in 9222,9223,9224,9225){
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/list" -TimeoutSec 3
    $pages = $r | Where-Object { $_.type -eq "page" }
    Write-Output ("PORT "+$port+" : "+$pages.Count+" page targets")
    foreach($p in $pages){ Write-Output ("   - "+$p.title+" | "+$p.url) }
  } catch { Write-Output ("PORT "+$port+" : not reachable") }
}