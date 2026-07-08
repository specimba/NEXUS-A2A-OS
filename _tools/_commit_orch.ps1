Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
if (-not (Test-Path evidence/orchestrator)) { New-Item -ItemType Directory -Force -Path evidence/orchestrator | Out-Null }
Copy-Item "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\orchestrator-solution-published.png" evidence/orchestrator/solution-1-v1.0.2.png
git add evidence/orchestrator/
git commit -m "Add Orchestrator evidence: Solution 1 v1.0.2 published + active"
git log -3 --oneline