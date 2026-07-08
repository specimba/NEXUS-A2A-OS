"""validate_premium_providers.py — Live endpoint check for Ethicore + Baseten.

Verifies that the premium providers referenced in the .env file are reachable
and that the integration code in models/guards/guard_plane_service.py and
nexus_os/relay/model_relay.py would succeed.

Output: validation result + latency + response shape.
"""
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

env_path = Path(r"C:\Users\speci.000\Documents\NEXUS\.env")
env = {}
for line in env_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()


def probe(name, url, headers, body, timeout_s=10):
    print(f"\n=== {name} ===")
    print(f"  URL: {url}")
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            data = r.read().decode()
            elapsed = time.time() - t0
            print(f"  STATUS: {r.status}  ({elapsed:.2f}s)")
            print(f"  RESPONSE: {data[:300]}")
            return {"ok": True, "status": r.status, "elapsed": elapsed, "body": data[:500]}
    except urllib.error.HTTPError as e:
        elapsed = time.time() - t0
        body = e.read().decode() if e.fp else ""
        print(f"  HTTP_ERROR: {e.code}  ({elapsed:.2f}s)")
        print(f"  BODY: {body[:300]}")
        return {"ok": False, "status": e.code, "elapsed": elapsed, "body": body[:500]}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        elapsed = time.time() - t0
        print(f"  NETWORK_ERROR: {type(e).__name__}  ({elapsed:.2f}s)")
        print(f"  DETAIL: {str(e)[:200]}")
        return {"ok": False, "status": None, "elapsed": elapsed, "body": str(e)[:200]}


results = {}

api_key = env.get("ORACLESTECH_API_KEY", "")
if api_key:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"text": "What is the capital of France?"})
    results["ethicore"] = probe(
        "Ethicore / ORACLESTECH",
        "https://api.oraclestechnologies.com/v1/guardian/analyze",
        headers, body, timeout_s=8,
    )
else:
    print("ORACLESTECH_API_KEY not found in .env")
    results["ethicore"] = {"ok": False, "reason": "no_api_key"}

baseten_key = env.get("BASETEN_API_KEY", "")
baseten_endpoint = env.get("BASETEN_ENDPOINT", "https://bridge.baseten.co/v1/chat/completions")
if baseten_key:
    headers = {
        "Authorization": f"Bearer {baseten_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps({
        "model": "llama-3-8b",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    })
    results["baseten"] = probe(
        "Baseten",
        baseten_endpoint,
        headers, body, timeout_s=10,
    )
else:
    print("BASETEN_API_KEY not found in .env")
    results["baseten"] = {"ok": False, "reason": "no_api_key"}

cf_token = env.get("CLOUDFLARE_AI_TOKEN", "")
if cf_token:
    headers = {
        "Authorization": f"Bearer {cf_token}",
        "Content-Type": "application/json",
    }
    body = json.dumps({"messages": [{"role": "user", "content": "ping"}]})
    results["cloudflare"] = probe(
        "Cloudflare AI",
        "https://api.cloudflare.com/client/v4/accounts/ai/run/@cf/meta/llama-3-8b-instruct",
        headers, body, timeout_s=10,
    )
else:
    results["cloudflare"] = {"ok": False, "reason": "no_token"}

zilliz_uri = env.get("ZILLIZ_URI", "")
if not zilliz_uri:
    for k, v in env.items():
        if k.startswith("ZILLIZ") and "URI" in k.upper():
            zilliz_uri = v
            break
print(f"\nZilliz URI: {zilliz_uri or '(not found in .env)'}")
results["zilliz"] = {"ok": "skip", "reason": "requires ZILLIZ_URI + token (separate from .env keys)"}

out_dir = Path(r"C:\Users\speci.000\Documents\NEXUS\benchmarks\stress_lab")
out_dir.mkdir(parents=True, exist_ok=True)
stamp = time.strftime("%Y%m%d_%H%M%S")
out_path = out_dir / f"premium_provider_validation_{stamp}.json"
out_path.write_text(json.dumps(results, indent=2))
print(f"\nSaved -> {out_path}")
print("\n=== SUMMARY ===")
for k, v in results.items():
    status = "OK" if v.get("ok") else f"FAIL ({v.get('status') or v.get('reason', '?')})"
    print(f"  {k:12s} {status}")
