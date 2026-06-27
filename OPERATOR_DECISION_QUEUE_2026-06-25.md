# NEXUS Operator Decision Queue — Pending Approval
**Date:** 2026-06-25  
**Status:** Awaiting operator pick; research dive in progress

1. Register Windows Scheduled Task `NexusServiceAutoRevive` for durable port auto-revive after reboot
2. Wire Hermes `model.base_url → http://127.0.0.1:7350/v1` so Hermes routes through ModelRelay
3. Verify Hermes install type: native binary vs Python venv (`hermes doctor`, `hermes --version`)
4. Consolidate duplicate revive scripts (`revive_relay_ports.ps1`, `start_nexus_services.ps1`, `start_python_relay_7355.bat`) into one canonical `scripts/nexus_revive.ps1`
5. P0 detector lift: raise MCP gateway + hallucination detection coverage from 20–30% toward 80%+ (real logit-stream wiring)
