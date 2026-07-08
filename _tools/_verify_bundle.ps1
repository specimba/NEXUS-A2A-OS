$path = "C:\Users\speci.000\AppData\Roaming\simular-unified-ui\SimularFiles\artifacts\nexus-skills-bundle"
Write-Output "Bundle contents:"
Get-ChildItem -Recurse -Path $path -File | ForEach-Object {
    $rel = $_.FullName.Substring($path.Length)
    $kb = [math]::Round($_.Length / 1KB, 1)
    Write-Output ("  {0,-60}  {1,6} KB" -f $rel, $kb)
}