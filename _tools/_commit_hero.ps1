Set-Location "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
if (-not (Test-Path evidence/studio-final)) { New-Item -ItemType Directory -Force -Path evidence/studio-final | Out-Null }
Copy-Item "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\studio-ready-to-publish.png" evidence/studio-final/canvas-ready-to-publish.png
git add evidence/studio-final/
git commit -m "Add hero screenshot: Studio canvas with 0 issues + all conditional flows visible"
git log -3 --oneline