$R = "C:\Users\speci.000\Documents\NEXUS\NEXUS_UiPathAgentHack"
Set-Location $R
Write-Output "===== git log ====="
git log -6 --oneline --decorate
Write-Output ""
Write-Output "===== git status ====="
git status
Write-Output ""
Write-Output "===== push status (compare local to origin) ====="
git fetch origin 2>&1 | Out-Null
$local  = git rev-parse HEAD
$remote = git rev-parse origin/main
if ($local -eq $remote) { Write-Output "PUSHED: local == origin/main ($local)" } else { Write-Output "NOT PUSHED: local=$local  origin/main=$remote"; Write-Output "Ahead:"; git log origin/main..HEAD --oneline; Write-Output "Behind:"; git log HEAD..origin/main --oneline }
Write-Output ""
Write-Output "===== test count (re-run) ====="
python -m pytest --tb=no -q 2>&1 | Select-Object -Last 15