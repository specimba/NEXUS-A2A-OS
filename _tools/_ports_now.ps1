foreach($p in 9222,9223,9224,9225,9226) {
  $proc = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object OwningProcess
  if($proc){ $p2 = Get-Process -Id $proc.OwningProcess -ErrorAction SilentlyContinue; Write-Output ("PORT " + $p + ": PID " + $proc.OwningProcess + " - " + $p2.ProcessName) } else { Write-Output ("PORT " + $p + ": free") }
}