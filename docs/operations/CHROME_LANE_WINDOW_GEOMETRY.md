# Chrome lane slim-line / invisible window

## Root cause

1. **SilentBackground** launch used `--window-position=-32000,-32000` and `--window-size=1,1`.
2. Chrome **persists** that in `%ProfileDir%\Default\Preferences` → `browser.window_placement`.
3. Every later **visible** start restores a **1px-tall or off-screen** frame (taskbar sliver, click does nothing).
4. CDP `setWindowBounds({ windowState: "maximized" })` **alone** does not set width/height when the saved state is broken.

## Fix stack (run in order)

```powershell
cd C:\Users\speci.000\Documents\NEXUS
.\scripts\grok_zo_cdp_lane.ps1 -Action RestartChrome
```

Restart now: kills lane Chrome → **reset Preferences placement** → start with `--start-maximized` + `1280x900` → CDP normal-then-max with **real work area** → Win32 `MoveWindow` if height &lt; 200px.

Live CDP up (no kill):

```powershell
.\scripts\reset_lane_chrome_window_placement.ps1   # best when Chrome stopped; optional before restart
.\scripts\restore_chrome_cdp_window.ps1 -Port 9224
```

## Numbers (not arbitrary)

- **Min sane window:** 900×600 (CDP); Win32 repair if height &lt; 200 or width &lt; 400.
- **Default placement:** 1280×900 at (80,50); centered using `get_primary_work_area.ps1` (System.Windows.Forms).
- **Never** use `-SilentBackground` for Grok/Zo/GPT collab.

## Verify

```powershell
.\scripts\get_primary_work_area.ps1
node tools\browser_ai_supervisor\chrome_cdp_browser_restore.mjs --port 9224 --work-width 1920 --work-height 1080
```

JSON `steps` should show `normal_explicit` when prior bounds were broken, then `maximized`.