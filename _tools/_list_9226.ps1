try {
  $r = Invoke-RestMethod -Uri "http://127.0.0.1:9226/json/list" -TimeoutSec 5
  $pages = $r | Where-Object { $_.type -eq "page" }
  foreach($p in $pages){
    $tag = ""
    if($p.url -match "devpost"){ $tag = " [DEVPOST]" }
    if($p.url -match "accounts\.google\.com|signon|signin"){ $tag = " [GOOGLE-LOGIN]" }
    Write-Output ("TAB " + $p.id + $tag + " | " + $p.title + " | " + $p.url)
  }
} catch {
  Write-Output ("FAIL to reach 9226: " + $_.Exception.Message)
}