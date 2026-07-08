$urls = @(
  "https://nexus-sentinel-policy-adapter.onrender.com/health"
  "https://nexus-sentinel-policy-adapter.onrender.com/api/v1/case/evaluate"
  "https://github.com/specimba/NEXUS_UiPathAgentHack"
  "https://docs.google.com/presentation/d/16B00BABNwdsIpOygh_VtlineLtHP6P8VHPyjqxlnMP0/edit"
  "https://github.com/specimba/NEXUS_UiPathAgentHack/blob/main/docs/SUBMISSION.md"
  "https://github.com/specimba/NEXUS_UiPathAgentHack/blob/main/assets/video/NEXUS-Sentinel-AgentHack-Demo.mp4"
  "https://github.com/specimba/NEXUS_UiPathAgentHack/blob/main/uipath/NEXUSSentinelBPMN/Process.bpmn"
  "https://github.com/specimba/NEXUS_UiPathAgentHack/blob/main/uipath/NEXUSSentinelRobot/Main.xaml"
)
foreach($u in $urls){
  try {
    $r = Invoke-WebRequest -Uri $u -Method Head -UseBasicParsing -TimeoutSec 10
    Write-Output ("OK    [" + $r.StatusCode + "] " + $u)
  } catch {
    $sc = $null; if($_.Exception.Response){ $sc = [int]$_.Exception.Response.StatusCode }
    Write-Output ("FAIL  [" + $sc + "] " + $u)
  }
}