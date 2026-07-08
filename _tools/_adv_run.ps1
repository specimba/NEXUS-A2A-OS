$base=""
$m = Get-Content -Raw "C:\Users\speci.000\Documents\NEXUS\_tools\_adv_manifest.json" | ConvertFrom-Json
$out=@()
foreach($j in $m){
  try {
    $r = Invoke-WebRequest -Uri $j.url -Method POST -ContentType "application/json" -InFile $j.file -UseBasicParsing
    $out += [pscustomobject]@{ name=$j.name; status=[int]$r.StatusCode; body=$r.Content }
  } catch {
    $sc=$null; if($_.Exception.Response){$sc=[int]$_.Exception.Response.StatusCode}
    $out += [pscustomobject]@{ name=$j.name; status=$sc; body=$_.ErrorDetails.Message }
  }
}
$out | ConvertTo-Json -Depth 8 -Compress