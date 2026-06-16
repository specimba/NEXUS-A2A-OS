# Original User Request

## Initial Request — 2026-06-14T16:56:45+03:00

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Research and implement a zero-cost resilient system for registering, bypassing IP/device blocks, and dynamically routing free-tier and trial API access for cutting-edge LLMs (such as Kimi 2.6/2.7, Qwen 3.6/3.7, DeepSeek V4, MiniMax M3, Claude 4.6/4.7/4.8, GPT 5.4/5.5, Gemini 3/3.1/3.5, and GLM 5.1/5.2) into the NEXUS ModelRelay architecture.

Working directory: c:/Users/speci.000/Documents/NEXUS
Integrity mode: development

## Requirements

### R1. ModelRelay Configuration Hardening
- Add native support for the `internai` (Shanghai AI Lab) and `siliconflow` providers in ModelRelay (`sources.js` and `providerLinks.js`).
- Map all newly discovered SiliconFlow and InternAI model IDs to their score lookup aliases in `MODEL_ID_ALIASES` in `sources.js` so they use correct intelligence scores.
- Increase the health check ping timeout `PING_TIMEOUT` in `server.js` from `30_000` to `60_000` (60 seconds) so slow models like `MiniMax-M3` on SiliconFlow or Nvidia NIM do not cause timeout errors and get falsely marked as down.
- Add an explicit status mapping in `server.js` where status codes `429` (depleted free credits) and `402` (payment required) are treated as `"quota"` status instead of `"down"`.

### R2. Automated dynamic WAN IP Reset Utility
- Implement a Python utility `nexus_os/bridge/dynamic_ip_rotator.py` that discovers UPnP-compliant residential gateways on the local subnet.
- Program it to trigger a WAN connection reset using UPnP SOAP requests (`urn:schemas-upnp-org:service:WANIPConnection:1` / `ForceTermination` action) to force the ISP to assign a new external IP address.
- Ensure the script logs the old IP, triggers the reset, waits for connection restoration, and logs the new IP.

### R3. Fingerprint Evasion & Trial Signup Playbook
- Create `docs/operations/EVASION_PLAYBOOK.md` detailing operational instructions on how to bypass registration blocks (using multi-session profiles, Canvas/WebGL fingerprint masking, incognito environments, and User-Agent rotating) when registering new trial accounts.

## Acceptance Criteria

### ModelRelay Integration
- [ ] Pinging slow models (e.g., MiniMax M3 on SiliconFlow or Nvidia NIM) successfully completes without health-check timeout failures.
- [ ] ModelRelay UI and endpoints list `internai` and `siliconflow` models, and the sync script `sync.py` correctly syncs them to OpenCode, MimoCode, and KiloCode.
- [ ] The dashboard displays exhausted free tiers as yellow/orange warning dots (`quota`) instead of red error dots (`down`).

### IP Reset Utility
- [ ] The `dynamic_ip_rotator.py` script executes without syntax errors and discovers UPnP-compliant devices on the local subnet.
- [ ] The script provides clear logging of WAN IP checks and reset attempts.

### Test Integrity
- [ ] All existing 203 NEXUSCLAW tests continue to pass.
