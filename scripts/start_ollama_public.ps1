$env:OLLAMA_HOST='0.0.0.0:11435'
$env:OLLAMA_ORIGINS='*'
$env:OLLAMA_DEBUG='1'
$outFile = 'C:\Users\speci.000\Documents\NEXUS\.nexus_pi\state\ollama_out.log'
$errFile = 'C:\Users\speci.000\Documents\NEXUS\.nexus_pi\state\ollama_err.log'

# Kill any existing ollama processes
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2

Start-Process 'C:\Users\speci.000\AppData\Local\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -RedirectStandardOutput $outFile -RedirectStandardError $errFile -WindowStyle Hidden
Start-Sleep 5
Write-Host 'Ollama started, checking port...'
Get-NetTCPConnection -LocalPort 11435 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State,OwningProcess
