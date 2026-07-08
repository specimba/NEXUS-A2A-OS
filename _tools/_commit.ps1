$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Set-Location $R
# Add evidence dir + live-test output + screens to repo
if (-not (Test-Path evidence/live-test)) { New-Item -ItemType Directory -Force -Path evidence/live-test | Out-Null }
Copy-Item "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\live-test-output.txt" evidence/live-test/output.txt
Copy-Item "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\studio-canvas-with-opus-edits.png" evidence/live-test/studio-canvas.png
Copy-Item "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\studio-canvas-final.png" evidence/live-test/studio-canvas-final.png
git add evidence/live-test/
git commit -m "Add live test evidence + Studio canvas screenshots for next-session handoff"
git log -3 --oneline