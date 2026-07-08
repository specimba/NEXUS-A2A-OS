$P = "C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS"
Write-Output "=== .md FILES (first 30) ==="
Get-ChildItem -Path $P -Recurse -Filter *.md -ErrorAction SilentlyContinue | Select-Object -First 30 | ForEach-Object { "  "+$_.FullName.Substring($P.Length) + "  ("+[math]::Round($_.Length/1KB,1)+"KB)" }
Write-Output ""
Write-Output "=== TOP-RELEVANCE filenames (injection-defense / privilege / verification / governance / oversight) ==="
$hot = "prompt.?inject|injecagent|secalign|promptshield|commandsans|argus|progent|privilege|verif|validation|oversight|govern|trustworthy|guardrail|audit|provenance|threat|defen"
Get-ChildItem -Path $P -Recurse -File -Filter *.pdf -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $hot } | ForEach-Object { "  ["+$_.Directory.Name+"] "+$_.Name } | Sort-Object