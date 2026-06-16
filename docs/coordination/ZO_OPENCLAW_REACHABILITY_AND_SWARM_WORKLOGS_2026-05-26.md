---
id: NODE-MIG-ZO_OPENCLAW_REACHABILITY_AND_SWARM_WORKLOGS_2026_05_26
authority_scope: experimental
origin_sha256: 2211123bb8dd98f6ee132ea21f7a57b9e470fb6e799cbbfa63840810e8b324a9
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-5051F7
---
# Zo OpenClaw Reachability And Swarm Worklog Capture

<!-- CANARY: 1a772221a96863b1eef6455a348c35f3 -->
Date: 2026-05-26
Scope: `https://modal.tail5788b3.ts.net/`, OpenClaw dashboard access, and repeatable swarm worklog capture for future installations.

## Local Reachability Evidence

Windows-side checks from NEXUS show:

- DNS resolves `modal.tail5788b3.ts.net` to Tailscale IP `100.68.51.3`.
- TCP port `443` succeeds.
- Python TLS handshake succeeds with certificate CN `modal.tail5788b3.ts.net`.
- HTTPS GET returns `502 Bad Gateway`.
- HTTP port `80` is refused.
- `tailscale status` shows peer `modal` is active.
- Tailscale SSH to `root@modal` is refused on port `22`.

Interpretation:

```text
Tailscale network path is alive.
Tailscale Serve HTTPS front door is alive.
The backend service behind Serve is down, wrong-port, or misconfigured.
```

This is not a shortcut problem and not a generic DNS problem. It is a remote OpenClaw/Tailscale Serve backend regression.

## Most Likely Failure Modes

1. OpenClaw gateway on `127.0.0.1:18789` is stopped.
2. Tailscale Serve still points to `127.0.0.1:18789`, but OpenClaw moved ports.
3. OpenClaw gateway starts then exits because of invalid config.
4. Provider/auth config causes agent failures, but this should not normally break `/health`; check separately.
5. Tailscale Serve config was changed and now proxies to a stale backend.

## Remote Recovery Probe

Run on Zo/modal shell, not on Windows:

```bash
openclaw status --deep
openclaw gateway probe
openclaw security audit --deep
openclaw agent list
tailscale serve status
ps -ef | grep -Ei '[o]penclaw|[t]ailscale|[t]elegram-claw|[m]odelrelay'
ss -ltnp | grep -E '(:80|:443|:18789|:7352|:7353|:9191)' || true
curl -sS -i http://127.0.0.1:18789/health | head -40
curl -sS -i http://127.0.0.1:18789/ | head -40
```

If OpenClaw is not listening:

```bash
cd /root/.openclaw
nohup openclaw gateway > /tmp/openclaw-stdout.log 2>/tmp/openclaw-stderr.log &
sleep 6
curl -sS -i http://127.0.0.1:18789/health | head -40
```

If local health works but Tailscale still returns `502`, verify and rebind Serve:

```bash
tailscale serve status
tailscale serve --https=443 http://127.0.0.1:18789
tailscale serve status
```

Tailscale docs note that Serve CLI syntax changed in client `1.52`; verify with `tailscale serve --help` on the Zo host if the command rejects the form above.

## Read-Only Worklog Collector

Use the local helper as the repeatable pattern for all future OpenClaw/SwarmClaw installations:

```bash
bash scripts/zo_openclaw_collect_readonly.sh
```

Run it on the Zo/modal host after copying the script there. It creates a redacted bundle under `/tmp/zo-openclaw-evidence-*` containing:

- OpenClaw status, gateway probe, security audit, and agent list.
- Tailscale Serve status.
- process and listening-port inventory.
- local health checks for OpenClaw and Guard Plane ports.
- OpenClaw model config without raw keys.
- auth-profile file permissions without printing raw keys.
- recent OpenClaw logs with key-like strings redacted.

Do not publish the bundle until the redaction is reviewed.

## Swarm Installation Learning Loop

Every OpenClaw/SwarmClaw install should produce these artifacts before being called stable:

| Artifact | Purpose |
|---|---|
| `install_state.txt` | host, OS, OpenClaw version, Tailscale version, active ports |
| `security_audit.txt` | `openclaw security audit --deep` redacted output |
| `gateway_probe.txt` | gateway reachability and local health |
| `serve_status.txt` | Tailscale Serve target and public/private exposure mode |
| `agent_models.txt` | active model mapping, provider family, no raw keys |
| `agent_worklog.md` | what the swarm tried, what failed, what changed |
| `provider_failures.jsonl` | auth/rate_limit/model_unavailable/tool_unavailable/network classifications |
| `operator_decisions.md` | human approvals, rejected changes, rollback points |

The stable pattern is not "dashboard works once." The stable pattern is:

```text
reachable -> audited -> provider-routed -> rate-limited -> worklog-captured -> repeatable rollback
```

## Provider And Workstyle Guardrails

- Keep `telegram-claw-gateway` disabled until dedupe, backoff, and a minimum polling interval are proven.
- Keep OpenClaw main agent away from `openai/*` unless OpenAI billing is intentionally configured.
- Prefer OpenRouter or ModelRelay for routine OpenClaw traffic, but log actual served model and failure class.
- Add autosleep/backoff around free providers after `429` or stream interruption.
- Treat Grok/Zo browser-agent outputs as proposal artifacts. NEXUS verifies before adoption.

## Current Operator Decision

Do not treat `modal.tail5788b3.ts.net` as dead. Treat it as:

```text
tailnet peer active, Tailscale Serve active, backend OpenClaw unavailable.
```

Recover backend health first, then capture worklogs before any next swarm tweak.

## Local SpecimbaPC Tailnet Recovery - 2026-05-26

Observed local URL:

```text
https://specimbapc.tail5788b3.ts.net/
HTTP 502 Bad Gateway
```

Windows-side evidence:

- DNS resolved `specimbapc.tail5788b3.ts.net` to `100.88.178.62`.
- TCP `443` succeeded.
- `tailscale serve status` initially reported no persistent Serve config.
- A stale foreground `tailscale.exe` listener occupied HTTPS `443`.
- Local Guard Plane was healthy at `http://127.0.0.1:7352/v1/health`.

Fix applied:

```powershell
Stop-Process -Id 12520 -Force
tailscale serve --bg --https=443 http://127.0.0.1:7352
```

Post-fix state:

```text
https://specimbapc.tail5788b3.ts.net (tailnet only)
|-- / proxy http://127.0.0.1:7352
```

Verification:

```text
https://specimbapc.tail5788b3.ts.net/v1/health -> 200 OK
{"status":"ok","service":"nexus-guard-plane","version":"1.2.0","classifier_loaded":true,"models_available":["special-virus","gemma3"]}
```

Expected behavior:

- `/v1/health` is the health endpoint.
- `/` and `/health` return FastAPI `404 Not Found`; that is not a Tailscale failure.
- A future `502` on this hostname means the Tailscale front door is alive but the backend target is unavailable or misbound.
