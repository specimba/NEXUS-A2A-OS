# NEXUS SAGE Private Preview Runbook

**Scope:** private, operator-controlled ChatGPT preview only. This is not a
public-production deployment. Do not publish the GPT, enable link sharing, or
reuse its bearer elsewhere.

Only the loopback SAGE edge may face a tunnel. It forwards exactly six
allowlisted operations to fixed Brain origin `127.0.0.1:7352`. Never tunnel the
Brain port directly.

## Preconditions

- Work from the NEXUS repository root in PowerShell 7.4 or newer.
- Keep the bearer outside the repository, history, logs, screenshots, schemas,
  instructions, and knowledge files.
- Use `observe_only`; never enable `proposal_write` for this preview.
- Confirm ports `7352` and `17452` have no stale owners.
- Keep the GPT private and operator-only. Sharing requires a separate promotion
  review and per-user authorization design.
- Keep the persisted instruction text below Builder's 8,000-character limit.
- Disable Web Search, Canvas, Image Generation, Code Interpreter, and
  conversation-training use; SAGE Preview uses only its reviewed Action.

## 1. Stop services and rotate the bearer

Rotate only while Brain, edge, and tunnel are stopped. This writes 48 random
bytes as 96 lowercase hexadecimal characters without printing the value:

```powershell
$keyFile = Join-Path $HOME ".nexus_pi\state\.sage_api_token"
New-Item -ItemType Directory -Force (Split-Path -Parent $keyFile) | Out-Null
$bytes = [byte[]]::new(48)
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$token = [Convert]::ToHexString($bytes).ToLowerInvariant()
[IO.File]::WriteAllText($keyFile, $token, [Text.UTF8Encoding]::new($false))
icacls $keyFile /inheritance:r /grant:r "${env:USERNAME}:(R,W)" | Out-Null
$token = $null
[Array]::Clear($bytes, 0, $bytes.Length)
Write-Output "SAGE_BEARER_ROTATED value_emitted=false"
```

Update Bearer authentication in the private GPT Action after rotation. Never
place it in schema or evidence. Do not restore an old bearer for rollback;
rotate again if replacement is needed.

## 2. Start and verify Brain

```powershell
pwsh -NoProfile -File .\scripts\start_sage_brain.ps1 `
  -SageKeyFile "$HOME\.nexus_pi\state\.sage_api_token"

py -3.13 .\scripts\verify_sage_runtime.py `
  --base-url http://127.0.0.1:7352 `
  --key-file "$HOME\.nexus_pi\state\.sage_api_token"
```

Continue only if output reports loopback `7352`, `observe_only`, execution
denied, and six operations. Record `listener_pid` and `supervisor_pid`
separately with their process creation timestamps; `pid` is the verified
listener identity, not the virtual-environment supervisor.

## 3. Start and verify the loopback edge

Start in a separate operator terminal. Pass only the credential path:

```powershell
$env:NEXUS_SAGE_API_KEY_FILE = "$HOME\.nexus_pi\state\.sage_api_token"
$env:NEXUS_SAGE_GATEWAY_MODE = "observe_only"
.\.venv\Scripts\python.exe .\scripts\serve_sage_edge.py
```

Then run from the control terminal:

```powershell
py -3.13 .\scripts\verify_sage_runtime.py `
  --base-url http://127.0.0.1:17452 `
  --key-file "$HOME\.nexus_pi\state\.sage_api_token"
```

Continue only if this reports the edge surface and six operations. Keep literal
loopback and fixed upstream `http://127.0.0.1:7352`.

## 4. Start and inspect a temporary HTTPS tunnel

Tunnel only `http://127.0.0.1:17452`. Disable request inspection, replay, and
body capture. An ngrok development preview has this shape:

```powershell
ngrok http http://127.0.0.1:17452 --inspect=false
```

For ngrok, check the target without printing the public hostname:

```powershell
$tunnels = @((Invoke-RestMethod http://127.0.0.1:4040/api/tunnels).tunnels)
[pscustomobject]@{
  tunnel_count = $tunnels.Count
  target_ok = @($tunnels | Where-Object { $_.config.addr -eq "http://127.0.0.1:17452" }).Count -eq 1
  https_present = @($tunnels | Where-Object { $_.proto -eq "https" }).Count -eq 1
}
$ngrokProcess = @(Get-CimInstance Win32_Process -Filter "Name = 'ngrok.exe'" |
  Where-Object { $_.CommandLine -match "127\.0\.0\.1:17452" })
[pscustomobject]@{
  target_process_count = $ngrokProcess.Count
  inspection_disabled = $ngrokProcess.Count -eq 1 -and
    $ngrokProcess[0].CommandLine -match "--inspect(?:=|\s+)false"
}
```

Require exactly one target, one HTTPS tunnel, and
`inspection_disabled=True`. OpenAI and the selected tunnel provider may process
traffic under their policies; do not send secrets or production data.

## 5. Verify the public edge and private Action

Use a transient variable and pin the current hostname:

```powershell
$publicUrl = Read-Host "Paste the current HTTPS preview URL"
$expectedHost = ([Uri]$publicUrl).Host
py -3.13 .\scripts\verify_sage_runtime.py `
  --base-url $publicUrl `
  --expected-host $expectedHost `
  --key-file "$HOME\.nexus_pi\state\.sage_api_token"
$expectedHost = $null
$publicUrl = $null
```

Require edge surface, `observe_only`, execution denied, and six operations.
Update the private GPT Action server URL and rotated Bearer. Confirm the draft
saves without an error, all optional built-in capabilities remain unchecked,
and conversation-training use remains unchecked. In a fresh Preview, ask for
current NEXUS SAGE health without naming an operation ID. Require the registered
health Action, `Allow once`, `observe_only`, `execution_allowed=false`, and
zero job submission. Do not publish or enable link sharing.

## Retention sweep

The one-shot utility is scheduler-safe but no Task Scheduler job is installed by
this runbook. Its default is a read-only report and it never accepts a database
path or job selector:

```powershell
$retention = py -3.13 .\scripts\sweep_sage_job_retention.py | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $retention.ok -or $retention.applied) {
  throw "SAGE_RETENTION_DRY_RUN_FAILED"
}
$retention | Select-Object state, mode, applied, counts
```

Require `mode=dry_run`, `applied=false`, no path/job/payload fields, and a
zero exit code before considering an operator schedule. If a live Brain has
already initialized its store, also require `state=complete`; `database_missing`
is a valid no-create result only for an inactive/new installation and is never
evidence that live retention is working.

Only an independently reviewed retention schedule may add the explicit apply
flag:

```powershell
py -3.13 .\scripts\sweep_sage_job_retention.py --apply
```

This performs logical SQLite deletion of expired job and idempotency rows only.
It is not encryption, backup/recovery, operator deletion, or forensic erasure.

## Stop and rollback

Stop in exposure-first order: tunnel, edge, Brain. Stop only captured PIDs whose
creation timestamps still match the identities recorded at startup:

```powershell
Stop-Process -Id <tunnel-pid> -Force
Stop-Process -Id <edge-pid> -Force
Stop-Process -Id <brain-listener-pid> -Force
Stop-Process -Id <brain-supervisor-pid> -Force
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -in 7352, 17452 }
```

The listener check must return nothing. Remove the temporary server URL from the
private Action if it will stay offline. Any failed claim gate is a stop
condition; never widen a bind, tunnel Brain, or enable writes as a workaround.

## Evidence logging

Append sanitized milestones to:

- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUScontinuity_runs.jsonl`
- `C:\Users\speci.000\Downloads\NEXUSlogs\NEXUSnewSOLcoordinationULTRAonCODEXlog-23.txt`

Record UTC timestamp, run ID, action, captured listener/supervisor PID, surface (`brain`, `edge`, or
`public-edge`), mode, operation count, verifier exit code, target/inspection
booleans, and evidence command. Never record the bearer, Action auth value,
request body, public URL, ephemeral hostname, or complete tunnel command line.
Mark public-edge milestones `private_only=true` and `production=false`.
