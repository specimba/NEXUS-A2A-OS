---
id: NODE-MIG-ANTIGRAVITY_IDE_BUG_REPORT_2026_05_23
authority_scope: experimental
origin_sha256: 245b57df509b2631e7ae0e50e21fddcf7cf481b37a003afbbd42c4d630655eb8
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-0505AD
---
# Antigravity Client "Open IDE" Custom Protocol — Bug Report & Resolution Guide

**Date:** 2026-05-23  
**Status:** REMEDIATED LOCALLY — AWAITING UPSTREAM PATCH  
**Target Recipient:** Google DeepMind / Gemini Developers Team  
**Scope:** Antigravity Desktop Shell UI / Editor Launcher  
**Related Screenshots:**  
<!-- CANARY: a8c42d893fb2bccee9b2f685e0a94d27 -->
- **UI Trigger:** ![UI Trigger](/c:/Users/speci.000/Documents/NEXUS/docs/ide_bug_1.png)  
- **System Collapse:** ![System Error](/c:/Users/speci.000/Documents/NEXUS/docs/ide_bug_2.png)  
- **Store Failure:** ![Store Search Failure](/c:/Users/speci.000/Documents/NEXUS/docs/ide_bug_3.png)  

---

## 1. Bug Description

Following the recent software update to the **Antigravity desktop client/editor**, a new **"Open IDE"** button was successfully introduced in the top-right header section of the interface (Screenshot 1). 

However, clicking this button triggers a custom protocol link (`antigravity-ide://`) that fails to open any local editor or CLI tool. Instead, Windows throws a standard system dialogue warning:  
**"Get an app to open this 'antigravity-ide' link"** (Screenshot 2).

If the user clicks "Browse Microsoft Store", the store performs a keyword search for `antigravity-ide` and fails with **"Sonuç bulunamadı"** ("No results found") (Screenshot 3). 

---

## 2. Root Cause Analysis

The "Open IDE" feature operates by launching a custom Windows URI scheme protocol (specifically `antigravity-ide://?path=...`). 

However, the Antigravity desktop application installer/updater **fails to register this custom URI protocol handler** inside the Windows Registry during the update process. Because the system classes database lacks any definition for `antigravity-ide`, the Windows shell cannot route the action to a local editor (like Cursor or VS Code) and displays the protocol-missing popup.

---

## 3. Local Remediation & Working Workaround

To restore immediate, automated workspace connections for developers while the upstream patch is being integrated, we built and deployed a custom intermediate handler script and registered it for the active user:

### Step 1: Intermediate Protocol Handler
We created [`scripts/antigravity_ide_handler.py`](file:///c:/Users/speci.000/Documents/NEXUS/scripts/antigravity_ide_handler.py). This script:
1.  Receives the raw protocol URL passed by Windows.
2.  Parses the target workspace path out of the URL (unquoting percent-encoded parameters like `%3A` and `%5C`).
3.  Automatically detects the user's primary IDE path (preferring Cursor located under `%USERPROFILE%\AppData\Local\Programs\cursor\Cursor.exe` or falling back to VS Code).
4.  Launches the IDE targeting the current workspace.
5.  Logs the execution details for debugging under `%USERPROFILE%\.gemini\antigravity\ide_handler.log`.

### Step 2: Protocol Registry Key Insertion
We registered the custom URI protocol handler cleanly under the current user's scope (which **requires zero Administrator privileges**) by running [`scripts/register_protocol.ps1`](file:///c:/Users/speci.000/Documents/NEXUS/scripts/register_protocol.ps1):

```registry
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Classes\antigravity-ide]
@="URL:antigravity-ide Protocol"
"URL Protocol"=""

[HKEY_CURRENT_USER\Software\Classes\antigravity-ide\shell]

[HKEY_CURRENT_USER\Software\Classes\antigravity-ide\shell\open]

[HKEY_CURRENT_USER\Software\Classes\antigravity-ide\shell\open\command]
@="\"C:\\Program Files\\Python313\\pythonw.exe\" \"c:\\Users\\speci.000\\Documents\\NEXUS\\scripts\\antigravity_ide_handler.py\" \"%1\""
```

*Note: The command binds to `pythonw.exe` rather than standard `python.exe` to suppress opening a command prompt console window, providing a completely seamless native launching experience.*

---

## 4. Recommended Upstream Fix for Gemini Team

To permanently resolve this bug in the next client update, the Antigravity desktop installer/shell wrapper should:
1.  **Register standard HKCU keys during installation**: During installation or client launch, automatically check if the `antigravity-ide` registry key exists, and create it under `HKEY_CURRENT_USER\Software\Classes\antigravity-ide` mapping to the Antigravity desktop executable or target user preference.
2.  **Provide an IDE Selection Menu inside client Settings**: Add a selector in the Antigravity settings panel allowing users to map the `antigravity-ide://` protocol target command to either Cursor, VS Code, or a custom CLI command.
