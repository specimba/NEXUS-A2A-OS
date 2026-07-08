$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Set-Location $R
Get-ChildItem samples -Recurse -File -ErrorAction SilentlyContinue | Select-Object FullName, Length | Format-Table -AutoSize | Out-String | Write-Output