foreach($p in 9222,9223,9224,9225,9226) {
  $proc = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object OwningProcess
  if($proc){ $p2 = Get-Process -Id $proc.OwningProcess -ErrorAction SilentlyContinue; Write-Output ("PORT " + $p + ": PID " + $proc.OwningProcess + " - " + $p2.ProcessName) } else { Write-Output ("PORT " + $p + ": free") }
}

# where is Playwright currently connected?
$cwd = (Get-Location).Path
Write-Output ("Playwright CDP likely: http://127.0.0.1:9222 (default)")
