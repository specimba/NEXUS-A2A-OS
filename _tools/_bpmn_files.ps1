$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Set-Location $R
Write-Output "=== files containing bpmn ==="
Get-ChildItem -Recurse -Path . -Include *.bpmn,*.xml -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "node_modules|\.git" } | Select-Object FullName, Length, LastWriteTime
Write-Output ""
Write-Output "=== Process.bpmn present? ==="
if (Test-Path uipath/NEXUSSentinelBPMN/Process.bpmn) {
  Write-Output "  yes: $(Get-Item uipath/NEXUSSentinelBPMN/Process.bpmn).Length bytes"
} else {
  Write-Output "  NO"
}