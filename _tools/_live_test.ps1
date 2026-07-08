$url = "https://nexus-sentinel-policy-adapter.onrender.com"
$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
foreach ($sample in @("01-safety-hold","02-approved-remediation","03-verification-failed","04-verification-passed")) {
  $file = Get-Content "$R\samples\$sample.json" -Raw
  Write-Output "=== $sample ==="
  try {
    $r = Invoke-RestMethod "$url/api/v1/case/evaluate" -Method POST -ContentType "application/json" -Body $file -TimeoutSec 15
    $verdict = $r.verdict
    $id = $r.auditId
    $verdict | Out-String | Write-Output
    "  auditId="+$id | Write-Output
    "" | Write-Output
  } catch {
    "  ERR " + $_.Exception.Response.StatusCode + ": " + $_.ErrorDetails | Write-Output
    "" | Write-Output
  }
}
Write-Output "=== AUDIT LOOKUP ==="
try {
  $r = Invoke-RestMethod "$url/api/v1/audit/$(($(Get-Content "$R\samples\01-safety-hold.json" -Raw) | ConvertFrom-Json).remediationId)" -TimeoutSec 5 -ErrorAction SilentlyContinue
  $r | ConvertTo-Json -Depth 3
} catch {
  "audits endpoint: " + $_.Exception.Message
}