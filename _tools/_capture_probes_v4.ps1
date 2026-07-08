$base = "https://nexus-sentinel-policy-adapter.onrender.com"
$ts = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$g = [guid]::NewGuid().ToString().Substring(0,12)
$samples = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack\samples"
$out = "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\video-shots\probes"

# Load and FULLY OVERWRITE every potentially-cached field on each sample
function FreshVerifyBody($sampleName, $tag, $caseTag, $remediationTag, $evalAuditId) {
    $raw = Get-Content (Join-Path $samples $sampleName) -Raw
    $obj = $raw | ConvertFrom-Json
    # strip ALL top-level identifiers and re-stamp
    $obj.request_id = "v4-" + $tag + "-" + $g
    $obj.case_id = $caseTag + "-" + $g
    $obj.remediation_id = $remediationTag + "-" + $g
    if($evalAuditId){ $obj.evaluation_audit_id = $evalAuditId }
    return $obj
}

# ALLOW first
$allow = Get-Content (Join-Path $samples "02-approved-remediation.json") -Raw | ConvertFrom-Json
$allow.request_id = "v4-allow-" + $g
$allow.case_id = "CASE-V4-ALLOW-" + $g
$allow | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $out "payload_allow.json") -Encoding UTF8
Write-Output ("ALLOW payload id: " + $allow.request_id)

$allowResp = $null
try {
  $r = Invoke-WebRequest -Uri ($base + "/api/v1/case/evaluate") -Method POST -ContentType "application/json" -InFile (Join-Path $out "payload_allow.json") -UseBasicParsing -TimeoutSec 30
  Write-Output ("ALLOW: HTTP " + $r.StatusCode + " :: " + $r.Content)
  $r.Content | Set-Content (Join-Path $out "response_allow.json") -Encoding UTF8
  $allowResp = $r.Content | ConvertFrom-Json
} catch {
  $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
  Write-Output ("ALLOW FAIL HTTP " + $sc + " :: " + $_.ErrorDetails.Message)
}

# VERIFY FAIL (full payload fresh)
if($allowResp -and $allowResp.audit_id){
  $vf = FreshVerifyBody "03-verification-failed.json" "vfail" "CASE-V4-VF" "rem-V4-F" $allowResp.audit_id
  $vf | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $out "payload_vfail.json") -Encoding UTF8
  Write-Output ("VERIFY_FAIL payload id: " + $vf.request_id)
  try {
    $r = Invoke-WebRequest -Uri ($base + "/api/v1/case/verify") -Method POST -ContentType "application/json" -InFile (Join-Path $out "payload_vfail.json") -UseBasicParsing -TimeoutSec 30
    Write-Output ("VERIFY_FAIL: HTTP " + $r.StatusCode + " :: " + $r.Content)
    $r.Content | Set-Content (Join-Path $out "response_vfail.json") -Encoding UTF8
  } catch {
    $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
    Write-Output ("VERIFY_FAIL FAIL HTTP " + $sc + " :: " + $_.ErrorDetails.Message)
  }
}

# VERIFY PASS
if($allowResp -and $allowResp.audit_id){
  $vp = FreshVerifyBody "04-verification-passed.json" "vpass" "CASE-V4-VP" "rem-V4-P" $allowResp.audit_id
  $vp | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $out "payload_vpass.json") -Encoding UTF8
  Write-Output ("VERIFY_PASS payload id: " + $vp.request_id)
  try {
    $r = Invoke-WebRequest -Uri ($base + "/api/v1/case/verify") -Method POST -ContentType "application/json" -InFile (Join-Path $out "payload_vpass.json") -UseBasicParsing -TimeoutSec 30
    Write-Output ("VERIFY_PASS: HTTP " + $r.StatusCode + " :: " + $r.Content)
    $r.Content | Set-Content (Join-Path $out "response_vpass.json") -Encoding UTF8
  } catch {
    $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
    Write-Output ("VERIFY_PASS FAIL HTTP " + $sc + " :: " + $_.ErrorDetails.Message)
  }
}

# AUDIT GET
if($allowResp -and $allowResp.audit_id){
  try {
    $r = Invoke-WebRequest -Uri ($base + "/api/v1/audit/" + $allowResp.audit_id) -Method GET -UseBasicParsing -TimeoutSec 30
    Write-Output ("AUDIT_GET: HTTP " + $r.StatusCode)
    Write-Output $r.Content
    $r.Content | Set-Content (Join-Path $out "response_audit.json") -Encoding UTF8
  } catch {
    $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
    Write-Output ("AUDIT_GET FAIL HTTP " + $sc)
  }
}

Write-Output "--- DONE ---"