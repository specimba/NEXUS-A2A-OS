# Operator holds live Grok/GPT/Zo collab — background jobs must not CDP-send to those lanes.
param(
    [ValidateSet("on", "off", "status")]
    [string]$Mode = "status",
    [string]$Note = ""
)

$path = "C:\Users\speci.000\Downloads\NEXUSlogs\a2a_experiment\COLLAB_LOCK.json"
switch ($Mode) {
    "on" {
        @{
            locked = $true
            since = (Get-Date).ToUniversalTime().ToString("o")
            note = $Note
            lanes = @("grok", "chatgpt_gpt55", "zo")
        } | ConvertTo-Json | Set-Content -Path $path -Encoding UTF8
    }
    "off" {
        if (Test-Path $path) { Remove-Item $path -Force }
    }
    "status" {
        if (Test-Path $path) { Get-Content $path -Raw } else { '{"locked":false}' }
    }
}