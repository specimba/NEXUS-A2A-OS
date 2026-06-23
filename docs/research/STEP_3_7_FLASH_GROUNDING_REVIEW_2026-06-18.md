# Step 3.7 Flash Grounding Review — 2026-06-18

## Verdict
- **Model work status:** PASS for Node/npm ModelRelay NVIDIA routing. `stepfun-ai/step-3.7-flash` is grounded as UP in logs, current NEXUS snapshots, Archivist state, and ModelRelay source/score files.
- **Architecture status:** GAP. Step 3.7 Flash is not present in the current Python relay (`nexus_os/relay/model_relay.py`) or the older D: recovery relay. It lives in the Node/npm ModelRelay layer.
- **Documentation status:** GAP. Intelligence, context, and latency values differ across sources and need reconciliation.

## Evidence map
| Source | Path | Claim | Confidence |
|---|---|---|---|
| NVIDIA NIM fix log | `Downloads\NEXUSlogs\NEXUSopencodeMAINbackendCODEkimi26log-09.txt` lines ~770, 1270-1360, 1394-1403 | User reported Step 3.7 Flash worked; NVIDIA models returned 404; wrong NVIDIA IDs fixed; after restart NVIDIA had 45 models, 14 UP, including `stepfun-ai/step-3.7-flash: intell=0.78`. | High |
| Runtime status log | `Downloads\NEXUSlogs\NEXUSantiGRAVnexlog-08.txt` lines ~1290-1292, 5182-5184 | `stepfun-ai/step-3.7-flash, Status: up, LastError: None`. | High |
| Current npm snapshot | `scratch\npm_models.json` lines 1774-1902 | NVIDIA `stepfun-ai/step-3.7-flash`, `intell: 0.75`, `ctx: 256k`, `status: up`, `avg: 3228`, `uptime: 100`, `verdict: Very Slow`. | High |
| Current npm snapshot | `scratch\npm_models.json` lines 22907-22969 | Kilocode free alias `stepfun/step-3.7-flash:free`, `intell: 0.45`, `ctx: 262k`, `status: up`, `avg: 2111`, `verdict: Slow`. | High |
| Archivist state | `nexus_os\archivist\wiki_state.json` lines 96-99 | `stepfun-ai/step-3.7-flash`, `intell: 0.78`, `provider: nvidia`, `status: up`. | Medium-high |
| Archivist entity | `nexus_os\archivist\wiki\entities\models.md` line 24 | `stepfun-ai/step-3.7-flash | 0.78 | nvidia | 840ms | 256k | up`. | Medium-high |
| Fast boot | `nexus_os\archivist\wiki\boot.md` line 27 | `stepfun-ai/step-3.7-flash | 0.78 | nvidia | up`. | Medium |
| Dashboard | `nexus_os\archivist\wiki-ui\nexus-dashboard.html` line 1914 | NVIDIA Step 3.7 Flash, `intell: 0.78`, `status: up`, `latency: 680`, `context: 128K`. | Medium |
| ModelRelay source | `AppData\Roaming\npm\node_modules\modelrelay\sources.js` line 248 | NVIDIA source lists `["stepfun-ai/step-3.7-flash", "Step 3.7 Flash", "256k"]`. | High |
| ModelRelay score | `AppData\Roaming\npm\node_modules\modelrelay\scores.js` line 93 | `stepfun-ai/step-3.7-flash: 0.75`. | High |
| Current Python relay | `nexus_os\relay\model_relay.py` lines 203, 411-429, 648-671 | Python relay fallback/mapping/API models are Ollama/Ollama-cloud oriented and do not include Step 3.7 Flash. | High |
| D: recovery relay | `D:\NEXUS_RECOVERY\NEXUS_20260605_140529\nexus_os\relay\model_relay.py` line 14 | Older v1.15 relay has `step-3.5-flash` in `healthy_models`, no Step 3.7 Flash. | High |

## Timeline
1. **Pre-fix:** NVIDIA models were returning 404 despite the user using Step 3.7 Flash successfully.
2. **Fix:** NVIDIA NIM model IDs were corrected in the Node/npm ModelRelay layer.
3. **Verification:** ModelRelay restart showed NVIDIA `45` models, `14 UP`, including `stepfun-ai/step-3.7-flash`.
4. **Runtime checks:** Later logs show `stepfun-ai/step-3.7-flash` as `up` with `LastError: None`.
5. **Archivist/dashboard capture:** Step 3.7 Flash was added to Archivist wiki state, entity table, boot table, and dashboard model list.

## Consistency gaps
| Gap | Evidence | Severity |
|---|---|---|
| Intelligence score split | `scores.js` = 0.75; Archivist/wiki/dashboard = 0.78. | P1 |
| Context split | `sources.js` and models wiki = 256k; dashboard = 128K; NVIDIA catalog log = 262144 context. | P1 |
| Latency split | Wiki/dashboard older snapshots show 680-856ms; npm average is 3228ms and verdict is Very Slow. | P2 |
| Provider alias split | NVIDIA `stepfun-ai/step-3.7-flash` and Kilocode `stepfun/step-3.7-flash:free` are distinct entries and must not be collapsed. | P1 |
| Architecture split | Node/npm ModelRelay has Step 3.7 Flash; current Python relay and D: recovery relay do not. | P1 |
| GROSS gap | No GROSS-related file reviewed mentions Step 3.7 Flash. | P2 |
| D: recovery gap | No exact Step 3.7 Flash evidence found in D: recovery; older relay only references Step 3.5 Flash. | P2 |

## Architecture placement
Step 3.7 Flash is currently a **Node/npm ModelRelay provider model** on NVIDIA, not a current Python relay model. The current Python relay at 7355 is Ollama/local/cloud fallback oriented and does not route NVIDIA provider IDs such as `stepfun-ai/step-3.7-flash`. The older D: recovery relay predates this work. GROSS remains a separate MCP bridge/evidence project and is not Step 3.7 routing evidence.

## Recommended next actions
- **P1:** Reconcile Step 3.7 Flash metadata in one source of truth: score, context, provider, latency basis, and whether the Kilocode free alias is separate.
- **P1:** Decide whether Step 3.7 Flash must be exposed through the Python relay. If yes, add provider-aware routing or document that it is Node/npm-only.
- **P2:** Add an Archivist lint rule for model metadata drift across `sources.js`, `scores.js`, `wiki_state.json`, `wiki/entities/models.md`, `wiki/boot.md`, and dashboard HTML.
- **P2:** Keep GROSS out of this model review unless new evidence appears; current GROSS files are unrelated to Step 3.7 Flash.

## Resolution applied — 2026-06-18
- **Routing source of truth:** Node/npm ModelRelay on port 7350. `stepfun-ai/step-3.7-flash` is an NVIDIA provider model, currently routed outside the Python relay.
- **Routing score:** Use `modelrelay\scores.js` value `0.75` for current routing decisions. Treat Archivist/wiki/dashboard `0.78` as historical/display snapshot drift until regenerated.
- **Context:** Use `256k` / `262144` as the canonical context value. Treat dashboard `128K` as stale UI data.
- **Latency:** Do not publish a single fixed latency. Record it as route/snapshot-dependent: current npm average is `3228ms`, while older wiki/dashboard snapshots show `680-856ms`.
- **Provider aliases:** Keep NVIDIA `stepfun-ai/step-3.7-flash` and Kilocode `stepfun/step-3.7-flash:free` as separate models. Do not merge them.
- **Python relay exposure:** Documented as Node/npm-only for now. No code change was made to expose Step 3.7 Flash through `nexus_os/relay/model_relay.py`.

## Do not expose
Do not include API keys, provider tokens, private credentials, or raw terminal dumps. This artifact references evidence paths only.