$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Set-Location $R
Write-Output "===== canvas binding spec head ====="
if (Test-Path docs/CANVAS-BINDING-SPEC.md) { Get-Content docs/CANVAS-BINDING-SPEC.md -TotalCount 60 }
Write-Output ""
Write-Output "===== instance-timeline scaffold ====="
if (Test-Path assets/video/instance-timeline) { Get-ChildItem assets/video/instance-timeline | Select-Object Name, Length, LastWriteTime }