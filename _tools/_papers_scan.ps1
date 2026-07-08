$P = "C:\Users\speci.000\Downloads\ARCHIVIST\PAPERS"
$files = Get-ChildItem -Path $P -Recurse -File -ErrorAction SilentlyContinue
Write-Output ("TOTAL FILES: "+$files.Count)
Write-Output ("EXTENSIONS:")
$files | Group-Object Extension | Sort-Object Count -Descending | ForEach-Object { "  {0,-8} {1}" -f $_.Name,$_.Count }
Write-Output ""
Write-Output "SUBFOLDERS:"
Get-ChildItem -Path $P -Directory -ErrorAction SilentlyContinue | ForEach-Object { "  "+$_.Name }
Write-Output ""
Write-Output "=== FILENAME KEYWORD MATCHES ==="
$kw = "govern|policy|complian|audit|agent|orchestrat|human.?in.?the.?loop|oversight|approv|prompt.?inject|safety|align|guardrail|BPMN|workflow|process.?model|verif|valid|trust|provenance|recover|fault|retry|escalat|incident|autonom|multi.?agent|LLM.?agent|tool.?use|delegat"
$files | Where-Object { $_.Name -match $kw } | ForEach-Object { "  "+$_.Name } | Sort-Object -Unique