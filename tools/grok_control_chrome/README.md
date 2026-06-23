# NEXUS Grok Control Chrome Extension

Experimental Manifest V3 controller for using Grok as a paid browser-side burst worker while NEXUS remains the verifier and durable controller.

## Safety Posture

- Default is observe-only.
- Continuation drafting is opt-in with `autoContinue`.
- Actual send-click automation is a second explicit opt-in with `autoSend`.
- Local bridge posting is disabled by default and must target `http://127.0.0.1/...`.
- The extension sends only bounded state metadata and a 500-character preview, not cookies, auth headers, full chat exports, local files, or secrets.

## What It Does

- Injects a content script only on `grok.com`.
- Uses `MutationObserver` to detect response activity and quiet periods.
- Uses `chrome.alarms` in the service worker to periodically check open Grok tabs.
- Detects shallow/surface-sweep responses by minimum response length.
- Drafts or sends a continuation prompt under an operator-controlled per-chat limit.
- Optionally posts state to a local NEXUS bridge for logging or queue routing.

## Load Locally

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Select **Load unpacked**.
4. Choose `C:\Users\speci.000\Documents\NEXUS\tools\grok_control_chrome`.
5. Open the extension popup and enable only the controls you want.

## NEXUS Integration Contract

Recommended local bridge endpoint:

```text
POST http://127.0.0.1:7352/api/grok-control/events
```

Payload shape:

```json
{
  "kind": "grok_control_state",
  "generated_at": "2026-06-18T00:00:00.000Z",
  "tab_id": 1,
  "url": "https://grok.com/...",
  "status": "idle",
  "response_chars": 420,
  "continue_count": 1,
  "surface_sweep_suspected": true,
  "action_taken": "continue_drafted",
  "preview": "bounded text preview"
}
```

NEXUS should treat the payload as telemetry/proposal input only. It must not mark Grok work accepted until `scripts\verify_grok_outbox.py` or a stronger verifier accepts a generated packet.
