foreach($port in 9222, 9223, 9224, 9225) {
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/list" -TimeoutSec 3
    $pages = $r | Where-Object { $_.type -eq "page" }
    foreach($p in $pages){
      $isDevpost = $p.url -match "devpost\.com"
      $tag = if($isDevpost){ " [DEVPOST]" } else { "" }
      Write-Output ("PORT " + $port + $tag + " | " + $p.title + " | " + $p.url)
    }
  } catch { }
}