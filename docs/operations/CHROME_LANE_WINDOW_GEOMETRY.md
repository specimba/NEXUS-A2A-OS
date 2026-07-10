# Chrome lane slim-line / invisible window

## Root cause

1. **SilentBackground** launch used `--window-position=-32000,-32000` and `--window-size=1,1`.
2. **`hide_chrome_window.mjs`** + supervisor post-run hide parked the window off-screen after every director cycle.
3. Chrome **persists** that in `%ProfileDir%\Default\Preferences` → `browser.window_placement`.
4. Every later start restores a **1px-tall or off-screen** frame; operator had to re-run `watch_lane_stack.ps1` and wait for multi-lane tab travel.
5. CDP `setWindowBounds({ windowState: "maximized" })` **alone** does not set width/height when the saved state is broken.

## Policy (2026-07-10) — KEEP VISIBLE DEFAULT

| Rule | Detail |
|------|--------|
| **Never auto-hide** | `hide_chrome_window.mjs` is a **no-op** unless `NEXUS_FORCE_HIDE=1` (do not set). |
| **Visible launch** | `start_browser_ai_profile.ps1` / `start_grok_cdp_9224.ps1` default **on-screen** 1280×900. |
| **No post-director hide** | `run_browser_ai_supervisor.ps1` never calls hide. |
| **No tab carousel by default** | `watch_lane_stack.ps1` uses silent preflight (`--no-restore`); `-Observe` is opt-in. |
| **Gentle guard** | `keep_visible_daemon.ps1` only repairs broken geometry; no focus steal when OK. |
| **Protect lock** | `WINDOW_PROTECT.json` with `permanent` + `keep_visible` under `NEXUSlogs\a2a_experiment` and `Downloads\cdp_agent_scratch`. |

## Fix stack (if already offscreen)

```powershell
cd C:\Users\speci.000\Documents\NEXUS
.\scripts\restore_chrome_cdp_window.ps1 -Port 9224 -ForceShow -OnlyIfBroken -NoStealFocus
# or one-shot:
.\scripts\watch_lane_stack.ps1
```

Hard restart (kills lane Chrome, resets placement):

```powershell
.\scripts\grok_zo_cdp_lane.ps1 -Action RestartChrome
```

## Numbers (not arbitrary)

- **Min sane window:** 900×600 (CDP); Win32 repair if height &lt; 200 or width &lt; 400.
- **Default placement:** 1280×900 at (80,50); centered using `get_primary_work_area.ps1`.
- **Never** use `-SilentBackground` for Grok/Zo/GPT/Intern collab.

## Verify hide is dead

```powershell
$env:NEXUS_FORCE_HIDE='0'
node tools\browser_ai_supervisor\hide_chrome_window.mjs 9224 grok.com
# expect: {"ok":true,"skipped":true,"reason":"default_no_hide ...","policy":"KEEP_VISIBLE_DEFAULT"}
```

## Verify geometry

```powershell
.\scripts\get_primary_work_area.ps1
node tools\browser_ai_supervisor\chrome_cdp_browser_restore.mjs --port 9224 --only-if-broken --mode normal
```

JSON `steps` should show `skip_ok` when the window is already fine, or `normal_explicit` when repairing.