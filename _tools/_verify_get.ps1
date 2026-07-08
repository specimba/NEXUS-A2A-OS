try {
  $r = Invoke-WebRequest -Uri "https://nexus-sentinel-policy-adapter.onrender.com/health" -UseBasicParsing -TimeoutSec 10
  Write-Output ("ADAPTER /health: HTTP " + $r.StatusCode + " body=" + $r.Content)
} catch {
  $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
  Write-Output ("ADAPTER /health FAIL: " + $sc)
}
try {
  $r = Invoke-WebRequest -Uri "https://nexus-sentinel-policy-adapter.onrender.com/api/v1/audit/audit-nonexistent" -UseBasicParsing -TimeoutSec 10
  Write-Output ("ADAPTER audit miss: HTTP " + $r.StatusCode)
} catch {
  $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
  Write-Output ("ADAPTER audit miss: " + $sc)
}