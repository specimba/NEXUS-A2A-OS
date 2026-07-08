# Check TCP listeners for chrome PID 6300
$chromes = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName -eq "chrome" }
foreach ($c in $chromes) {
  $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
  Write-Output ("PID " + $c.OwningProcess + " | port " + $c.LocalPort + " | title=" + $proc.MainWindowTitle)
}
# Probe several ports
foreach ($p in 9225,9227,9228,9229,9230,9231,9232) {
  try { $r = Invoke-RestMethod "http://127.0.0.1:$p/json/list" -TimeoutSec 2 -ErrorAction SilentlyContinue; if ($r) { Write-Output ""; Write-Output "=== port $p has $($r.Count) tabs ==="; $r | ForEach-Object { Write-Output ("  tId="+$_.id+" title="+$_.title+" url="+$_.url) } } } catch {}
}