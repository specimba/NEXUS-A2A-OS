$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Set-Location $R
$demo = Get-Item (Join-Path $R "assets\video\NEXUS-Sentinel-AgentHack-Demo.mp4") -ErrorAction SilentlyContinue
if($demo){ Write-Output ("DEMO MP4: " + [math]::Round($demo.Length/1MB,1) + " MB") }
$ghReadme = Get-Item (Join-Path $R "README.md") -ErrorAction SilentlyContinue
if($ghReadme){ Write-Output ("README: " + [math]::Round($ghReadme.Length/1KB,1) + " KB") }
Write-Output ""
Write-Output "Latest commits (for changelog note):"
git log -8 --pretty=format:"  %h %ad %s" --date=format:"%m-%d %H:%M"