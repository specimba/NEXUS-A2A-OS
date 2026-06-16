---
id: NODE-MIG-ZO_OPENCLAW_NEXT_SAFE_SLICE_2026_05_26
authority_scope: experimental
origin_sha256: 4acb77769e23a992ae12fda0842b637b4492a7b9f9675a61b8433e7f6f85477f
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-7AF7F4
---
# Zo OpenClaw Next Safe Slice - 2026-05-26

<!-- CANARY: 42e70e458cb4c42d4cbfe90b3fa89774 -->
Source response: Zo layered status report at 2026-05-26 17:55 UTC.

## Assessment

Zo's latest report is usable because it stops treating "Claw" as one system. It correctly separates:

- `telegram-claw-gateway` spam bridge
- AutoClaw/KiloClaw message sources
- OpenClaw gateway health
- Tailscale Serve reachability
- device pairing
- provider routing
- ModelRelay/NIM path
- swarm readiness

The correct verdict is:

```text
reachable, but not swarm-ready
```

## Tight Corrections

1. `OpenClaw gateway` is described as "loopback only" while also listening on `0.0.0.0:18789`.
   - Treat this as not strictly loopback-only until bind address and firewall/container exposure are verified.
   - Tailscale Serve may be private, but the process bind is broader than loopback.

2. Exporting `OPENCLAW_GATEWAY_TOKEN` from config is acceptable only inside the Zo shell.
   - Do not paste the command output.
   - Do not paste the token-bearing environment variable.
   - Prefer a redacted command transcript.

3. Direct `paired.json` repair must trigger rotation.
   - It restored access.
   - It is not an install pattern.
   - It should be retired after a pre-paired installer exists.

## Response To Send Zo

```text
This is the right correction. Keep the current boundary:

reachable != swarm-ready.
dashboard paired != safe repeatable install.
ModelRelay/NIM success != native OpenClaw provider routing verified.

Two corrections before the next action:

1. You wrote "loopback only" but also reported OpenClaw listening on 0.0.0.0:18789. Please verify whether the gateway can be reached only through local/Tailscale routes or whether it is exposed on a broader interface. Report the bind address, firewall/container exposure, and Tailscale Serve target separately.

2. Treat the direct paired.json edit and the visible dashboard token as a break-glass incident. Do not reuse visible tokens. Do not paste token values again. Rotation is now the safe path before scale-out.

Next bounded execution slice:

Phase A - Redacted evidence bundle, no changes:
- Save redacted outputs for:
  - openclaw status --deep
  - openclaw security audit --deep
  - openclaw agent list
  - tailscale serve status
  - ss -ltnp filtered for 18789/443
  - sanitized provider mapping from models.json with no keys
- Save under docs/handoff/zo-coordination/worklogs/<timestamp>-openclaw-layered-status/

Phase B - Token hygiene plan, no rotation yet unless operator approves:
- Identify every active gateway/device/Telegram/provider token class.
- Mark which ones appeared in public transcript.
- Propose rotation order and expected downtime.
- Do not print token values.

Phase C - Provider smoke after token mismatch is fixed:
- Export gateway token only inside the shell, not into chat.
- Run one cheap OpenClaw main-agent call through the gateway.
- Prove whether it used native nvidia_nim, ModelRelay, OpenRouter, or another provider.
- Save served provider/model, latency, and redacted logs.

Phase D - Installer design:
- Draft pre-paired install bundle.
- Draft v3-to-v4 config migration shim.
- Draft redaction filter.
- Do not execute installer on the live node yet.

Do not re-enable telegram-claw-gateway.
Do not edit paired.json again.
Do not force-push.
Do not call this swarm-ready until repeatable install and provider-routed smoke pass.
```

## Acceptance For Next Zo Reply

The next Zo reply should include:

- Redacted evidence bundle path.
- Explicit answer to the `0.0.0.0:18789` exposure question.
- Token rotation plan without token values.
- One provider-routing smoke result, or a clear blocker explaining why it could not run.
- Installer/migration/redaction draft paths, not broad claims.

## NEXUS Decision

Keep OpenClaw as a single fragile but useful node for now. Do not scale it into more swarm installations until these are true:

- pairing is reproducible without manual JSON edits
- token rotation is complete
- gateway exposure is proven private
- native provider path is tested end-to-end
- redacted worklog bundle exists
- installer and migration shim have been dry-run on a fresh node
