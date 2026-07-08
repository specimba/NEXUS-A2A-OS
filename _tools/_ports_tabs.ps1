foreach($p in 9222,9223,9224,9225,9226) {
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$p/json/list" -TimeoutSec 3
    $pages = $r | Where-Object { $_.type -eq "page" }
    foreach($pg in $pages){
      $tag = if($pg.title -match "Maestro|Studio"){ "[STUDIO]" } elseif($pg.url -match "devpost"){ "[DEVPOST]" } else { "" }
      Write-Output ("PORT " + $p + " " + $tag + " | " + $pg.title + " | " + $pg.url)
    }
  } catch { }
}