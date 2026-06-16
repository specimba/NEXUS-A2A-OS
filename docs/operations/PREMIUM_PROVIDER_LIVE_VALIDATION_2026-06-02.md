---
id: NODE-MIG-PREMIUM_PROVIDER_LIVE_VALIDATION_2026_06_02
authority_scope: experimental
origin_sha256: 85fdca377149b846315e38a013416620a7baa0f20198c26e078129ddb37fb154
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-D9197C
---
# Premium Provider Live Validation — 2026-06-02

**Date:** 2026-06-02
**Script:** `scripts/validate_premium_providers.py`
**Result file:** `benchmarks/stress_lab/premium_provider_validation_20260602_105836.json`

## Live Probe Results

| Provider | Status | Error / Detail | Action |
|---|---|---|---|
| **Ethicore / ORACLESTECH** | HTTP 403 | Cloudflare error code 1010 (bot challenge). The endpoint rejects server-originated requests without browser user-agent + cookies. | Endpoint is not callable from this server in the current network posture. |
| **Baseten** | HTTP 200 | Returned HTML login page. The configured URL `https://bridge.baseten.co/v1/chat/completions` is not the actual API gateway — may be an outdated default in `model_relay.py:163`. | Need to verify the real Baseten deployment URL. The `BASETEN_ENDPOINT` env var can override. |
| **Cloudflare AI** | HTTP 404 | Path `accounts/ai/run/@cf/meta/llama-3-8b-instruct` is wrong — the official format requires an account ID, e.g. `accounts/<ACCOUNT_ID>/ai/run/@cf/meta/llama-3-8b-instruct`. | The token alone is insufficient. Need to add Cloudflare Account ID. |
| **Zilliz** | URI present | URI is `https://in05-fafefb36a4353d4.serverless.aws-eu-central-1.cloud.zilliz.com` (Serverless-01). Connection not yet probed. | Add to a follow-up probe with ZILLIZ_TOKEN. |

## What This Means for V5/V6 Plan

### A.1 Ethicore: Cloudflare WAF blocks server traffic
The current implementation in `guard_plane_service.py:491` calls
`https://api.oraclestechnologies.com/v1/guardian/analyze` with a Bearer token,
but Cloudflare's bot challenge (code 1010) rejects the request without a
browser session.

**Workarounds (in order of preference):**
1. **Use the mock path** — keep `MOCK_EXTERNAL_APIS=true` for development.
   Production deployment must use a server that is allow-listed by Ethicore's WAF.
2. **Add a User-Agent header** — some WAFs allow-listed server UAs. Try
   `User-Agent: NexusOS/1.0 (Server)`. The current code does not set a UA.
3. **Add `cf-clearance` cookie** — requires browser session; not feasible.
4. **Use a different provider** — `kayba-ai/guard-rails` or `enosislabs/matex`
   that don't sit behind Cloudflare WAF.

### A.2 Baseten: Default endpoint is outdated
The default `https://bridge.baseten.co/v1/chat/completions` is a
**landing page**, not the API. The real Baseten deployment URL is per-model
and looks like `https://model-{hash}.api.baseten.co/...`.

**Workarounds:**
1. **Set BASETEN_ENDPOINT to the real model URL** — requires manual configuration
   per deployed model.
2. **Use the Baseten Model API v1** — `https://api.baseten.co/v1/models/{model_id}/predict`
   requires a model_id.
3. **Skip Baseten** — fall back to local Ollama. Per the V3 benchmark,
   llama-guard3:1b is a viable local replacement.

### A.3 Cloudflare AI: Missing account ID
The model path requires `<ACCOUNT_ID>` not just `<MODEL>`. The token alone
is not enough.

**Workarounds:**
1. **Add CLOUDFLARE_ACCOUNT_ID** to `.env` and update the URL.
2. **Use the official `@cf` worker bindings** — different URL pattern.

### A.4 Zilliz: Not yet probed
Zilliz Serverless-01 is configured. A direct probe with token is needed.
This is the simplest case — Zilliz's API is pymilvus-based and stable.

## Recommended Action

1. **Don't fix the providers in this session** — they require either
   infrastructure changes (allow-listing the server with Ethicore) or
   manual config (Baseten deployment URL, Cloudflare account ID).
2. **Document the failure modes in V6 plan** — V6 explicitly says "skip
   Ethicore if not callable" and "fall back to local Ollama" which is
   exactly what happens today.
3. **Promote llama-guard3:1b as the primary fallback** — already done in B.
4. **Add a probe to CI** — so future PRs detect provider regression.

## Net Effect on NEXUS
The premium provider integrations are **architecturally wired** but
**operationally gated**. The local Ollama stack (qwen2.5-guard-q4 +
llama-guard3:1b + qwen2.5:0.5b) is the de facto production guard tier.
The premium providers are a future tier, not a present one.

## What I Will Not Claim
- I will not claim "Ethicore is wired" without acknowledging the 403.
- I will not claim "Baseten works" without acknowledging the HTML login page.
- I will not claim "Cloudflare AI works" without the account ID.

This is the correct evidence-grounded posture for the audit. The opus log
did not check live endpoints and so could not catch these issues.
