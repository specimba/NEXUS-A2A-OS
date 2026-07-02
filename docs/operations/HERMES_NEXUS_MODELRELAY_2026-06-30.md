# Hermes ↔ NEXUS ModelRelay (7350) — operator wiring

**Verified:** 2026-07-02 — `nexusctl grok-lane doctor` all links UP (cdp, grok_bridge, node_relay, python_relay, god_mode, dash_api, dash_ui).

**Hermes:** `model.base_url=http://127.0.0.1:7350/v1`, `model.default=auto-fastest` (operator confirmed).

## What was broken (from NEXUSubuntuHERMESlog-05)

- Repeated **full-config heredoc rewrites** → YAML corruption (`personalities` / `pirate` quoting, missing `max_concurrent_sessions`).
- **Zombie loop:** install uvicorn on system Python while **`.venv/Scripts` already has `uvicorn.exe` + `fastapi.exe`**.
- **7355 bind fights:** killing one Windows PID then starting another relay without checking `netstat`.
- **Wrong health probe:** `/health` 404 on 7350 is normal; use `/` or `/v1/models`.
- **WSL vs Windows:** 7350 reachable from WSL; **7355 and 7352 often Windows-only** (Invoke-WebRequest 200, WSL curl 000).

## Canonical routing (Hermes)

```bash
hermes config set model.base_url http://127.0.0.1:7350/v1
hermes config set model.default auto-fastest
```

Keep your **chat identity provider** (e.g. `xai-oauth` + `grok-composer-2.5-fast`) if you want Grok billing/OAuth — but **completions must hit 7350** via `base_url`. Do **not** restart into a new session unless you need a cold config load; **resume this session** after fixing YAML on disk.

Reload rule: Hermes reads `model.base_url` at process start. After YAML fix, use gateway `/restart` or restart CLI once — not “new session + lose context” unless config is still invalid.

## Recommended `model.default` values (from live 7350 catalog)

| Use case | Model id on relay |
|----------|-------------------|
| Auto route | `auto-fastest` |
| Fast coding | `step-3.7-flash` or `step-3.5-flash` (if listed) |
| Nemotron lane | `nemotron-3-nano` / `nemotron-3-super` / `nemotron-3-ultra` |
| Local Ollama via relay | entries owned_by `ollama` in `/v1/models` |
| Claude via relay | `claude-haiku-4.5`, `claude-sonnet-4.5` |
| DeepSeek | `deepseek-v3.2`, `deepseek-v4-flash` |

Refresh list:

```bash
curl -s http://127.0.0.1:7350/v1/models | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
```

## Service map (today)

| Port | Role | WSL curl | Windows probe |
|------|------|----------|---------------|
| 7350 | Node ModelRelay **primary for Hermes** | OK | OK |
| 7355 | Python Chimera relay | often FAIL | OK if PID listening |
| 7352 | Brain API governance | often FAIL | start: `.venv\Scripts\python.exe -m nexus_os.api.brain_api` |
| 7357 | God mode proxy | check | check |

## Python relay (7355) — correct start (no pip theatre)

```powershell
cd C:\Users\speci.000\Documents\NEXUS
.\.venv\Scripts\python.exe -m nexus_os.relay.model_relay
```

Before start: `netstat -ano | findstr :7355` — one listener only.

## Next execution order (3→1→4→2→7→6→5)

1. **7355** — verify Windows listener; do not relaunch if 200 on `/`.
2. **7352** — Brain API (started when PID on 7352 present).
3. **pytest** — `tests/test_openmodel_sakana_provider_config.py`, `tests/test_external_browser_ai_director.py`.
4. **Grok bridge 7354** — only after 7352/7350 stable.
5. **Redact secrets** — `01_PROJECT_STATE.md` Baseten key.
6. **Grok URL** → `NEXUS_GROK_PROJECT_ID` in `src/app/api/nexusclaw/status/route.ts`.
7. **Git commits** — wiki + nexusclaw status slices.

## Config hygiene

- Never paste 60-line heredocs into the terminal for `config.yaml`.
- Edit with `hermes config set …` or a **small patch** (one key at a time).
- On parse failure: restore `~/.hermes/config.yaml.corrupt.*.bak`, fix **only** the reported line, validate with `python3 -c "import yaml; yaml.safe_load(open('...'))"`.