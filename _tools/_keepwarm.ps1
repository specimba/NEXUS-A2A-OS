$ErrorActionPreference="SilentlyContinue"
while($true){
  try { Invoke-RestMethod "https://nexus-sentinel-policy-adapter.onrender.com/health" -TimeoutSec 60 | Out-Null; "$(Get-Date -Format o) OK" | Out-File -Append "C:\Users\speci.000\Documents\NEXUS\_tools\keepwarm.log" }
  catch { "$(Get-Date -Format o) ERR $($_.Exception.Message)" | Out-File -Append "C:\Users\speci.000\Documents\NEXUS\_tools\keepwarm.log" }
  Start-Sleep -Seconds 120
}