---
id: NODE-MIG-ZO_OPENCLAW_CONFUSION_HELP_PROMPT_2026_05_26
authority_scope: experimental
origin_sha256: 4a2cfb6b8f3329f8b0709dc33d35f9b762a20b21285aea65e5dbf6e54a46e81d
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-C53F7E
---
# Zo OpenClaw Confusion Help Prompt - 2026-05-26

<!-- CANARY: 11238a625981444fe98d94a25707717e -->
Source chat: `https://www.zo.computer/chats/pub_BvURTkRLEdQfQ5Eu`

Purpose: give Zo a bounded prompt and correction map after the latest OpenClaw pairing/dashboard work blurred separate "claw" systems together.

## Current Read

The latest Zo chat shows a useful recovery but also a confused operating model.

The working evidence from the chat:

- `telegram-claw-gateway` was the Slack spam bridge, not the OpenClaw gateway itself.
- OpenClaw gateway was reported healthy on `127.0.0.1:18789`.
- Tailscale Serve was reported as routing `modal.tail5788b3.ts.net` to the local OpenClaw gateway.
- Browser pairing hit a circular approval problem.
- Zo bypassed the pairing deadlock by editing OpenClaw device pairing JSON directly.
- ModelRelay was reported live separately from OpenClaw provider configuration.
- OpenRouter was reported unusable at that moment because all checked keys returned `402 Insufficient Credits`.
- NIM via Zo Space was reported healthy and separate from native OpenClaw provider config.

## Corrected Mental Model

Do not say "Claw is fixed" or "Claw is broken" without naming the layer.

| Layer | What It Is | Current Rule |
|---|---|---|
| `telegram-claw-gateway` | Telegram-to-Slack bridge | Keep disabled until dedupe, backoff, and rate limits are proven. |
| AutoClaw / KiloClaw Telegram bots | Message sources that fed the bridge | Treat as separate from OpenClaw gateway. Root cause of repeated `check` still needs proof. |
| OpenClaw gateway | Local control/dashboard gateway on `127.0.0.1:18789` | Can be healthy while model/provider calls fail. |
| OpenClaw device pairing | Dashboard/CLI authorization layer | Direct JSON edit is emergency recovery, not stable install procedure. |
| ModelRelay | NEXUS/Zo provider abstraction | Preferred model routing layer for Zo because Zo has no local GPU. |
| OpenRouter | External provider route | Only usable when funded and when OpenClaw active model mapping targets OpenRouter. |
| NIM via Zo Space | Separate funded provider path | Useful fallback lane, not proof OpenClaw native provider config is repaired. |
| Tailscale Serve | Private mesh exposure | `502` means backend/proxy target issue, not necessarily DNS failure. |

## Security Corrections

- Do not paste raw Telegram tokens, device pairing tokens, provider keys, or generated dashboard tokens into public Zo chats.
- Treat any token visible in public chat as compromised if it is still valid.
- Redact before saving logs or command output into NEXUS.
- Do not embed long-lived operator tokens in public URLs.
- Do not normalize direct edits to `/root/.openclaw/devices/*.json` as the install path.
- If direct JSON repair was used, follow up with a formal key rotation and a generated install bundle.

## Workflow Corrections

The chat's "commit after every file write" lesson is too broad for NEXUS. Correct rule:

```text
Persist important work quickly, but commit only reviewed, explicit, non-secret paths.
Never commit raw keys, pairing files, provider auth profiles, logs with tokens, or unreviewed generated dumps.
```

Direct edits to `paired.json` should be treated like a break-glass operation:

```text
recover access -> rotate tokens -> write pre-paired installer -> test installer on fresh node -> retire manual edit path
```

## Prompt To Send Zo

```text
Zo, pause broad OpenClaw changes and produce a layer-separated status report.

Goal: resolve "claw" confusion without leaking tokens or mixing separate runtimes.

Do not paste raw Telegram tokens, OpenClaw pairing tokens, provider keys, auth-profiles.json contents, or dashboard bearer URLs. Redact secrets before output.

Please inspect and report these layers separately:

1. telegram-claw-gateway
   - Is it still disabled?
   - What command/service definition disables it?
   - Is there any new `autoclaw-local: check` flood in logs?
   - Do not re-enable until dedupe, minimum poll interval, and Slack rate limits exist.

2. OpenClaw gateway
   - Run: openclaw status --deep
   - Run: openclaw gateway probe
   - Run: curl -sS -i http://127.0.0.1:18789/health | head -40
   - Report whether gateway health is independent from provider/model failures.

3. Tailscale Serve
   - Run: tailscale serve status
   - Confirm whether modal.tail5788b3.ts.net points to http://127.0.0.1:18789.
   - If URL returns 502, classify as backend/proxy target issue unless DNS/TCP also fails.

4. Device pairing
   - Report whether dashboard and CLI are paired without printing tokens.
   - If paired.json was manually edited, label it BREAK-GLASS RECOVERY.
   - Propose a pre-paired install bundle that generates device keys and scopes safely.
   - Do not create permanent public URLs with embedded tokens.

5. Provider routing
   - Check the active `main` agent model mapping.
   - If it still targets OpenAI without an OpenAI key, report that as provider mapping failure.
   - If OpenRouter is 402, do not claim OpenRouter is available.
   - If NIM via Zo Space works, report it as separate ModelRelay/NIM path, not native OpenClaw proof.

6. ModelRelay
   - Report health endpoints and currently verified models.
   - Log the served provider/model for a single cheap smoke test.
   - Keep ModelRelay as the abstraction for Zo because Zo is not a GPU model host.

7. Swarm readiness
   - Do not call this swarm-ready just because dashboard connects.
   - Classify state as:
     reachable / paired / provider-routed / audited / worklog-captured / repeatable install
   - Give exact evidence for each state.

Output format:
Layered status table, then blockers, then next safe command list.

Hard boundary:
No raw secrets. No force-push. No broad service restart. No direct JSON edits unless explicitly marked break-glass and followed by rotation plan.
```

## Expected Zo Output

Zo should return:

- A table separating `telegram-claw-gateway`, OpenClaw gateway, Tailscale Serve, pairing, provider routing, ModelRelay, and swarm readiness.
- Evidence commands and redacted outputs.
- A clear statement whether the current problem is dashboard reachability, pairing, provider routing, or bridge spam.
- A token-rotation recommendation if any public transcript token is still active.
- A next-step plan that builds a repeatable pre-paired installer and migration shim instead of relying on manual JSON edits.

## NEXUS Operator Decision

Treat the latest Zo recovery as:

```text
OpenClaw dashboard/access improved.
Pairing model exposed a bootstrap flaw.
Provider routing is still separate and must be verified.
Swarm readiness remains low until repeatable install, audit, and worklog capture exist.
```

Do not scale this to more swarm installations until the pre-paired install bundle, config migration shim, and redacted evidence collector are tested on a fresh node.
