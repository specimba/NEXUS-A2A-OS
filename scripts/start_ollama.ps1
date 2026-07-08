$env:OLLAMA_HOST='127.0.0.1:11435'
$env:OLLAMA_ORIGINS='*'
Start-Process 'C:\Users\speci.000\AppData\Local\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden
Start-Sleep 3
Get-NetTCPConnection -LocalPort 11435 -ErrorAction SilentlyContinue | Select-Object LocalPort,State
