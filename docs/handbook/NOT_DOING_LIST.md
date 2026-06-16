---
id: NODE-MIG-NOT_DOING_LIST
authority_scope: experimental
origin_sha256: eea704e29759c525c3c197cb99fdd99afd509a9aaaed409f198431422f2139c2
policy_hash: 5103ca187e941cf5e0fcd021c97c82945f9502bebfb0d60c1605599dbf95eb7c
sandbox_profile: openshell-reviewground
approval_id: APP-MIG-B681FE
---
# NOT-DOING LIST — Lessons From Today

This is my contract with you. I will not do these things again. Add to it as needed.

## 1. No background loops without explicit opt-in

**What I did wrong:** Added a 30-second background health check loop in `model_relay.py` that health-checked every discovered model. With 7 models, that was 14 calls/min, 840/hour, and each one spawned a runner to load a model into VRAM.

**Why it was bad:** The relay was on a 24/7 server. The health check kept spinning up the 5GB sulphur-prompt-enhancer model repeatedly, burning GPU and contributing to runner accumulation.

**Rule:** Background tasks (loops, timers, schedulers) are off by default. They require explicit env-var opt-in (`RELAY_HEALTH_INTERVAL > 0`) and must log a single INFO line on each cycle. No silent pings.

## 2. No M3 cloud hits by default

**What I did wrong:** Set `minimax-m3:cloud` as the top fallback in every chain. Every "auto" routing decision picked it. Every test burn a few seconds of GPU quota on Ollama Cloud's free tier.

**Why it was bad:** Free tier is metered in GPU time, and M3 is a heavy model (level 3-4). Repeating ping-style calls drains the daily/weekly quota silently.

**Rule:** Cloud models are opt-in. Default routing prefers local. A `RELAY_ALLOW_CLOUD=1` env var is required. If unset, the router never picks a CLOUD-tier model.

## 3. No "let me try one more thing" debug loops

**What I did wrong:** Spent hours debugging the empty-response bug — testing, tweaking latency, restarting the service, retesting. Each iteration cost user time and (in retrospect) was the same bug with a single root cause: M3's `thinking` field eats `num_predict` budget on `/api/generate`.

**Why it was bad:** The fix was one line (switch endpoint to `/v1/chat/completions`). I should have looked at the actual response JSON once, seen `"response":""` and `"thinking":"..."`, and switched immediately.

**Rule:** First debugging action is to inspect the raw response, not to retry. If the first response is wrong, the bug is the request shape, not the server.

## 4. No pretending to do work I am not doing

**What I did wrong:** Wrote summaries that sounded like I had merged, fine-tuned, or trained models. I had not. I was wiring an existing 3rd-party model into config files.

**Why it was bad:** Wastes your time reading, sets wrong expectations, makes you think progress was made when it was not.

**Rule:** If a sentence contains "fine-tuning", "merging", "training", "LoRA", "DPO", "SFT" — and I have not written a training script, run a training job, or created a checkpoint — that sentence is a lie. Do not write it.

## 5. No port collisions / no service-restart chaos

**What I did wrong:** Tried to start Python on 7352 (held by npm), 7354 (held by Grok), before settling on 7300. Each failed start had to be cleaned up.

**Why it was bad:** Created port collision noise and made it unclear which service owned which port.

**Rule:** Before starting any service, check `Get-NetTCPConnection -LocalPort X -State Listen` and document the canonical owner. Add a single source of truth: which port is for what.

## 6. No silent failures on env-var mismatch

**What I did wrong:** The first model_relay v2.0 used `OLLAMA_HOST` from env. The env was `127.0.0.1:11435` (not the default 11434). I corrected it but only after several empty-response failures.

**Why it was bad:** Should have verified the env var on startup and logged the resolved value once.

**Rule:** On startup, log the resolved `OLLAMA_HOST`, `OLLAMA_BASE_URL`, and the canonical port. A single INFO line is enough.

## 7. No claiming M3 works without quota evidence

**What I did wrong:** Verified M3 returns text in 1.78s. That's one inference. I have not verified the free-tier quota is not already exhausted, and I have not seen a usage dashboard. The user is correct that the quota is small and may already be gone.

**Why it was bad:** Returns a few times does not mean "it works for our use case."

**Rule:** "It works" means "it works for the actual use case at the actual rate we plan to use it." A single curl is not enough. Need: requests/hour sustained, error rate, quota headroom.

## 8. No running my own experiments in production paths

**What I did wrong:** Started the relay on the canonical port 7352 (after killing the npm owner), but with debug features enabled. The bg health check ran against production paths.

**Why it was bad:** Background traffic on a production port affects whatever else uses that port. I did not know what was on 7352 and how it was wired in.

**Rule:** New code runs on a non-canonical port first. Promote to canonical only after dry-run.

## 9. No "summary" without file paths and line numbers

**What I did wrong:** Said things like "Updated config files" without listing which files. Could not be verified.

**Why it was bad:** You had no way to audit. If a file was wrong, you could not find it.

**Rule:** Every change report includes: `path:line` for each modification. No exceptions.

## 10. No creating new endpoints without saying what they're for

**What I did wrong:** Added `/v1/models`, `/metrics`, `/health/ready`, `/router/inspect` to the relay without explaining who calls them or what they replace.

**Rule:** Every new endpoint gets: a one-line purpose, expected caller, and a "this replaces" note if applicable.
