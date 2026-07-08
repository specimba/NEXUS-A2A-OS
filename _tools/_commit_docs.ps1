Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
git add docs/RESEARCH-GROUNDING.md docs/PRODUCT-FEEDBACK.md
git status -s
git commit -m "Add Research Grounding essay + Product Feedback survey"
git log -3 --oneline
Write-Output ""
Write-Output "=== artifacts/instance-timeline (Lane A progress) ==="
if (Test-Path artifacts/instance-timeline) { Get-ChildItem artifacts/instance-timeline -Recurse | Select-Object FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String | Write-Output } else { Write-Output "not yet created" }
Write-Output ""
Write-Output "=== tools/record_instance.py exists? ==="
if (Test-Path tools/record_instance.py) { "  yes, $(Get-Item tools/record_instance.py).Length bytes" } else { "  no" }