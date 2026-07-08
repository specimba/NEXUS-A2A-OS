Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
git add docs/SUBMISSION.md
git commit -m "Add SUBMISSION.md (Devpost entry content, all artifacts listed)"
git log -3 --oneline
Write-Output ""
Write-Output "=== Lane A progress ==="
if (Test-Path artifacts/instance-timeline) { Get-ChildItem artifacts/instance-timeline -Recurse | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output } else { Write-Output "  not yet" }
if (Test-Path tools/record_instance.py) { Write-Output ("  tools/record_instance.py: " + (Get-Item tools/record_instance.py).Length + " bytes") } else { Write-Output "  tools/record_instance.py not yet" }