$src = "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\nexus-skills-bundle"
$zipOut = "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\nexus-skills-bundle.zip"
if (Test-Path $zipOut) { Remove-Item -Force $zipOut }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($src, $zipOut)
Write-Output ("ZIP: " + $zipOut)
Write-Output ("Size: " + [math]::Round((Get-Item $zipOut).Length / 1KB, 1) + " KB")

# Now ship to the repo (read-only source side, codex owns commits)
$repo = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
$dst = Join-Path $repo "skills"
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Recurse -Force (Join-Path $src "*") $dst
Write-Output ""
Write-Output ("Shipped to repo at: " + $dst)
Get-ChildItem -Recurse $dst -File | ForEach-Object {
    $rel = $_.FullName.Substring($repo.Length)
    $kb = [math]::Round($_.Length / 1KB, 1)
    Write-Output ("  {0,-60}  {1,6} KB" -f $rel, $kb)
}

# Also drop the ZIP at the repo root for direct consumption
Copy-Item -Force $zipOut (Join-Path $repo "nexus-skills-bundle.zip")
Write-Output ""
Write-Output ("ZIP copied to repo root: " + (Join-Path $repo "nexus-skills-bundle.zip"))