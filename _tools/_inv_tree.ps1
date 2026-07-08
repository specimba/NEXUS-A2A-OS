$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Write-Output "===== REPO TREE (non-git) ====="
Get-ChildItem -Path $R -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\\.git\\|node_modules|__pycache__|\.venv" } | ForEach-Object { $rel = $_.FullName.Substring($R.Length); $kb=[math]::Round($_.Length/1KB,1); "{0,-60} {1,8} KB  {2}" -f $rel,$kb,$_.LastWriteTime } | Sort-Object
Write-Output ""
Write-Output "===== ANY .xaml / Studio / Maestro / bpmn FILES under NEXUS ====="
Get-ChildItem -Path "C:\Users\speci.000\Documents\NEXUS" -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "\.xaml$|\.bpmn$|project\.json$|maestro|studio" } | ForEach-Object { $_.FullName + "  (" + [math]::Round($_.Length/1KB,1) + " KB, " + $_.LastWriteTime + ")" }