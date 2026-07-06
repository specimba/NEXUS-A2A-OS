# NEXUS browser lane roster (CDP :9224)

Registry: `nexus_os/nexusclaw/browser_lane_registry.json`

## One command — align all sessions (no new landing chats)

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action StabilizeChrome
```

Does: ensure CDP → fix slim/off-screen prefs → prune `about:blank` → **navigate existing tabs** to canonical URLs → restore window.

## Priority-1 lanes (collab core)

| Agent | Session |
|--------|---------|
| Grok | project chat (no duplicate tab) |
| Zo | specimba zo chat |
| ChatGPT GPT-5.5 | `/c/6a4600ec-…` |
| GLM-5.2 z.ai | `/c/1b1cd50b-…` — **Cancel** model downgrade; retry 5–10s |
| Apodex | deep discover home |

## Research / coding / papers

| Agent | Role |
|--------|------|
| Qwen webdev | HTML/CSS/JS sandbox `a321e504…` |
| Qwen deep research | `4d6ea806…` |
| DeepSeek | deepthink `07b0a633…` |
| AlphaXiv | assistant `019f2244…` + GLM-5.2 |
| Gemini app | `/app/6fba62a56f165a08` (not NotebookLM) |
| Meta Muse Spark | prompt `9cb00ce8…` |

## MiMo

| Lane | URL |
|------|-----|
| MiMo v2.5 chat | `#/chat/b58b518…` persistent |
| MiMo Claw | `#/` then left menu **MiMo Claw** (4h trial) |

## Connectors / multi-skill

| Agent | URL |
|--------|-----|
| Mistral work | project `b331cba1…` |
| MiniMax M3 | `agent.minimax.io` chat id |
| GMI playground | `console.gmicloud.ai/.../llm/1f12423b-ac10-4690-a670-36f768d7b9bf` |
| GMI model hub | Fable5 + catalog |

## Chrome sussy minimize / blank tabs

- Cold start uses `--restore-last-session` (not `about:blank`).
- New tabs open **background** when unavoidable.
- Disposable blanks pruned after real tabs exist.
- Broken geometry (`-26214`, height &lt; 200) → reset `window_placement` + CDP restore.

## Env overrides

`NEXUS_GEMINI_APP_URL`, `NEXUS_GLM_CHAT_URL`, `NEXUS_GMICLOUD_PLAYGROUND_URL`, etc. — see `ENV_MAP` in `open_or_navigate_lane.mjs`.

## Repair wrong tabs after URL fix

```powershell
.\scripts\repair_canonical_lane_urls.ps1
```