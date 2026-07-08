$bundle = "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\nexus-skills-bundle"
if (Test-Path $bundle) { Remove-Item -Recurse -Force $bundle }
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundle "perform-adversarial-system-review") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundle "search-and-synthesize-research-papers") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bundle "generate-project-handoff-documentation") | Out-Null
Write-Output "Bundle skeleton created at $bundle"
Get-ChildItem $bundle | ForEach-Object { Write-Output ("  + " + $_.Name) }