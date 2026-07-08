foreach($port in 9220, 9221, 9222, 9223, 9224, 9225, 9226, 9227, 9228) {
  try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$port/json/list" -TimeoutSec 3
    $pages = $r | Where-Object { $_.type -eq "page" }
foreach($p in $pages){
  $tag = ""
  if($p.url -match "devpost"){ $tag = " [DEVPOST]" }
  if($p.url -match "accounts\.google\.com|signon|signin"){ $tag = " [GOOGLE-LOGIN]" }
  if($p.url -match "recaptcha"){ $tag = " [RECAPTCHA]" }
  Write-Output ("PORT " + $port + $tag + " | " + $p.title + " | " + $p.url)
}
  } catch { }
}