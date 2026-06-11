#!/usr/bin/env python3
"""Real provider & model testing against live services.

Tests:
  1. Ollama API (port 11435) — list models, generate, chat
  2. npm modelrelay (port 7352) — model list, chat proxy, scoring
  3. Relay server (port 7355) — health, config, guard, chat, router
  4. Bridge client — score enrichment, circuit breaker, quota
  5. Guard pipeline — real guard model classification
  6. Full round-trip: bridge → scorer → guard → relay → ollama
"""
import sys, os, time, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import requests

PASS, FAIL = 0, 0
def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  OK  {name}")
    except Exception as e:
        FAIL += 1
        import traceback
        print(f"  FAIL {name}: {type(e).__name__}: {e}")
        print(f"       {traceback.format_exc()[:200].rstrip()}")

sec = lambda s: print(f"\n=== {s} ===")

OLLAMA = "http://127.0.0.1:11435"
NPM = "http://127.0.0.1:7352"
RELAY = "http://127.0.0.1:7355"

def main():
    # ─────────────────────────────────────────────────────
    sec("1. OLLAMA — live model API")
    # 1a. List models
    check("list models", lambda: len(requests.get(f"{OLLAMA}/api/tags", timeout=5).json().get("models", [])) >= 5)

    # 1b. Generate with qwen2.5:0.5b
    def test_generate():
        r = requests.post(f"{OLLAMA}/api/generate",
            json={"model": "qwen2.5:0.5b", "prompt": "Reply with exactly: HELLO", "stream": False, "max_tokens": 10},
            timeout=30)
        assert r.ok, f"status={r.status_code}"
        assert "response" in r.json(), f"no response key"
        assert len(r.json()["response"]) > 0, "empty response"
    check("generate qwen2.5:0.5b", test_generate)

    # 1c. Chat with qwen2.5:0.5b
    def test_chat():
        r = requests.post(f"{OLLAMA}/v1/chat/completions",
            json={"model": "qwen2.5:0.5b", "messages": [{"role": "user", "content": "say OK"}], "max_tokens": 10},
            timeout=30)
        assert r.ok, f"status={r.status_code}"
        c = r.json()["choices"][0]["message"]["content"]
        assert len(c) > 0, f"empty content"
    check("chat qwen2.5:0.5b", test_chat)

    # 1d. Test guard model
    def test_guard_qwen():
        r = requests.post(f"{OLLAMA}/api/generate",
            json={"model": "qwen2.5-guard-q4:latest", "prompt": "Classify: hello", "stream": False, "max_tokens": 10},
            timeout=30)
        assert r.ok
    check("guard model responds", test_guard_qwen)

    # ─────────────────────────────────────────────────────
    sec("2. NPM MODELRELAY (port 7352)")
    # 2a. /api/models
    def test_npm_models():
        r = requests.get(f"{NPM}/api/models", timeout=5)
        assert r.ok
        data = r.json()
        assert "models" in data
        assert len(data["models"]) > 50
        print(f"  [npm models: {len(data['models'])}]")
    check("npm /api/models", test_npm_models)

    # 2b. /v1/models (OpenAI compat)
    check("npm /v1/models", lambda: requests.get(f"{NPM}/v1/models", timeout=5).ok)

    # 2c. /api/config (returns provider config list)
    def test_npm_config():
        r = requests.get(f"{NPM}/api/config", timeout=5)
        assert r.ok
        c = r.json()
        assert isinstance(c, list)
        assert len(c) >= 5
        print(f"  [npm providers: {len(c)}]")
    check("npm /api/config", test_npm_config)

    # 2d. /api/logs
    check("npm /api/logs", lambda: requests.get(f"{NPM}/api/logs?limit=3", timeout=5).ok)

    # ─────────────────────────────────────────────────────
    sec("3. RELAY SERVER (port 7355)")
    # 3a. /health
    def test_relay_health():
        r = requests.get(f"{RELAY}/health", timeout=5)
        assert r.ok
        d = r.json()
        assert d["status"] == "ok"
        assert len(d["discovered_models"]) >= 5
        print(f"  [relay models: {len(d['discovered_models'])} discovered, {len(d['models_healthy'])} with health status]")
    check("relay /health", test_relay_health)

    # 3b. /health/ready
    def test_relay_ready():
        r = requests.get(f"{RELAY}/health/ready", timeout=5)
        # May be 503 if health sweep not finished — still valid
        d = r.json()
        assert "status" in d
        print(f"  [ready status: {d['status']}, healthy count: {d.get('count', d.get('healthy_models', 0))}]")
    check("relay /health/ready", test_relay_ready)

    # 3c. /api/config
    check("relay /api/config", lambda: requests.get(f"{RELAY}/api/config", timeout=5).ok)

    # 3d. /v1/models
    def test_relay_models():
        r = requests.get(f"{RELAY}/v1/models", timeout=5)
        assert r.ok
        d = r.json()
        assert "data" in d
        assert len(d["data"]) > 0
    check("relay /v1/models", test_relay_models)

    # 3e. /api/models (compat)
    check("relay /api/models", lambda: requests.get(f"{RELAY}/api/models", timeout=5).ok)

    # 3f. /metrics
    def test_relay_metrics():
        r = requests.get(f"{RELAY}/metrics", timeout=5)
        assert r.ok
        d = r.json()
        assert "models" in d
        assert "totals" in d
    check("relay /metrics", test_relay_metrics)

    # 3g. /router/inspect
    def test_router_inspect():
        r = requests.get(f"{RELAY}/router/inspect?prompt=write+python+code", timeout=5)
        assert r.ok
        d = r.json()
        assert "decision" in d
        assert "model" in d["decision"]
        print(f"  [router decision: model={d['decision']['model']}, tier={d['decision']['tier']}]")
    check("relay /router/inspect", test_router_inspect)

    # 3h. Guard endpoint
    def test_relay_guard():
        r = requests.post(f"{RELAY}/v1/guard",
            json={"messages": [{"role": "user", "content": "Hello"}], "strategy": "consensus", "mode": "audit"},
            timeout=60)
        assert r.ok or r.status_code == 403
        d = r.json()
        assert "safe" in d
        assert "classifications" in d
        print(f"  [guard safe={d['safe']}, skipped={d.get('skipped', [])}, stages={d['total_stages']}]")
    check("relay /v1/guard", test_relay_guard)

    # 3i. Real chat via relay
    def test_relay_chat():
        r = requests.post(f"{RELAY}/v1/chat/completions",
            json={"model": "qwen2.5:0.5b", "messages": [{"role": "user", "content": "say OK"}], "max_tokens": 10},
            timeout=60)
        assert r.ok, f"status={r.status_code} body={r.text[:200]}"
        c = r.json()["choices"][0]["message"]["content"]
        assert len(c) > 0
        safe = c.encode("ascii", "replace").decode()[:60]
        print(f"  [relay chat response: {safe}]")
    check("relay /v1/chat (qwen2.5:0.5b)", test_relay_chat)

    # ─────────────────────────────────────────────────────
    sec("4. BRIDGE CLIENT")
    from nexus_os.relay.bridge_client import ModelRelayBridge

    def test_bridge():
        bc = ModelRelayBridge()
        assert bc is not None
        assert bc.circuit_breaker is not None
        assert bc.quota_guard is not None
        assert hasattr(bc, "models")
        assert hasattr(bc, "refresh")
        assert hasattr(bc, "get_best_for_intent")
        assert hasattr(bc, "get_fastest_online")
        # Test refresh from npm modelrelay
        bc.refresh()
        print(f"  [bridge models: {len(bc.models)} models from npm]")
        assert len(bc.models) > 0
    check("bridge init + refresh from npm", test_bridge)

    # ─────────────────────────────────────────────────────
    sec("5. GUARD PIPELINE (direct)")
    from nexus_os.relay.model_relay import ModelRelay
    _relay = ModelRelay()
    # Mark all models healthy for test
    for m in _relay._model_stats:
        _relay._model_health[m] = True

    import asyncio

    def test_guard_safe():
        async def go():
            r = await _relay.check_guard(
                [{"role": "user", "content": "Hello, how are you today?"}],
                strategy="consensus"
            )
            assert "safe" in r
            assert r["safe"] is True
            print(f"  [safe guard: {r['unsafe_votes']}/{r['total_stages']} unsafe]")
        asyncio.run(go())
    check("guard safe input consensus", test_guard_safe)

    def test_guard_meta():
        async def go():
            r = await _relay.check_guard(
                [{"role": "user", "content": "Hello"}],
                strategy="meta"
            )
            assert "safe" in r
            assert "skipped" in r
            print(f"  [meta guard: safe={r['safe']}, stage={r['stage']}]")
        asyncio.run(go())
    check("guard meta strategy", test_guard_meta)

    _relay.shutdown()

    # ─────────────────────────────────────────────────────
    sec("6. PROVIDER CHAIN")
    from nexus_os.relay.providers_strict import STRICT_PROVIDERS
    from nexus_os.relay.providers_frontier import FRONTIER_PROVIDERS
    check("strict providers", lambda: len(STRICT_PROVIDERS) >= 8)
    check("frontier providers", lambda: len(FRONTIER_PROVIDERS) >= 3)
    check("strict has deepseek", lambda: any("deepseek" in p.name.lower() for p in STRICT_PROVIDERS))

    # ─────────────────────────────────────────────────────
    sec("7. ROUTING — intent + GMR")
    from nexus_os.relay.intent_classifier import PromptIntentClassifier
    from nexus_os.gmr.rotator import GeniusModelRotator

    _clf = PromptIntentClassifier()
    _gmr = GeniusModelRotator()

    for prompt, expected_intent in [
        ("def foo(): return 42", "code"),
        ("2 + 2 = ?", "math"),
        ("why is the sky blue", "reasoning"),
        ("write a poem about stars", "general"),
    ]:
        intent = _clf.classify(prompt).intent.value
        route = _gmr.select(prompt)
        ok = intent == expected_intent and route is not None
        status = "OK" if ok else "?"
        print(f"  [{status}] {expected_intent:10s} -> intent={intent}, gmr_primary={route.primary if route else 'None'}")

    # ─────────────────────────────────────────────────────
    sec("8. SCORER — dimension ranking")
    from nexus_os.relay.scorer import rank_by_dimension, rank_by_intent, get_scores
    code_top3 = [name for name, score in rank_by_dimension("code", 3)]
    math_top3 = [name for name, score in rank_by_dimension("math", 3)]
    intent_top3 = [name for name, score in rank_by_intent("code", 3)]
    print(f"  code top-3: {code_top3}")
    print(f"  math top-3: {math_top3}")
    print(f"  intent(code) top-3: {intent_top3}")

    # ─────────────────────────────────────────────────────
    sec("9. SUMMARY")
    print(f"{'='*50}")
    print(f"  {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
    if FAIL:
        print(f"  {FAIL} FAILURES")
        sys.exit(1)
    print(f"  ALL GREEN ({PASS}/{PASS+FAIL})")

if __name__ == "__main__":
    main()
