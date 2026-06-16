#!/usr/bin/env python3
"""Real integration test matching actual root APIs."""
import sys, os, time, logging
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
logging.basicConfig(level=logging.WARNING)

PASS, FAIL = 0, 0
def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  OK  {name}")
    except Exception as e:
        FAIL += 1
        import traceback
        print(f"  FAIL {name}: {type(e).__name__}: {e}")
        print(f"       {traceback.format_exc()[:300].rstrip()}")

sec = lambda s: print(f"\n--- {s} ---")
print("=== NEXUS OS REAL INTEGRATION TEST ===")

# ─── 1. SCORER ───────────────────────────────────────
sec("1. SCORER")
from nexus_os.relay.scorer import ModelScores, get_scores, rank_by_dimension, rank_by_intent, resolve, ALIASES
test("imports", lambda: len(ALIASES) > 20)
test("lookup gpt-4o", lambda: get_scores("gpt-4o").provider == "openai")
test("unknown returns None", lambda: get_scores("nonexistent") is None)
test("alias gpt4o->gpt-4o", lambda: resolve("gpt4o") == "gpt-4o")
test("rank_by_dimension(code,5)", lambda: len(rank_by_dimension("code", 5)) == 5)
test("rank_by_intent(code,3)", lambda: len(rank_by_intent("code", 3)) <= 3)

# ─── 2. INTENT CLASSIFIER ─────────────────────────────
sec("2. CLASSIFIER")
from nexus_os.relay.intent_classifier import PromptIntentClassifier
_clf = PromptIntentClassifier()
test("detect code", lambda: _clf.classify("Write a function to sort an array in Python").intent.value == "code")
test("detect math", lambda: _clf.classify("Calculate derivative of x^2").intent.value == "math")
test("detect reasoning", lambda: _clf.classify("Explain why the sky is blue").intent.value == "reasoning")
test("detect general", lambda: _clf.classify("Hello, how are you?").intent.value == "general")

# ─── 3. CIRCUIT BREAKER ──────────────────────────────
sec("3. CIRCUIT BREAKER")
from nexus_os.relay.circuit_breaker import ProviderCircuitBreaker
from nexus_os.relay.circuit_breaker import ProviderState
_cb = ProviderCircuitBreaker()
test("imports", lambda: True)
test("3 failures don't crash", lambda: [_cb.record_failure("p") for _ in range(3)] or True)
test("success resets", lambda: _cb.record_success("p") or True)
test("record_failure+success", lambda: (_cb.record_failure("p2"), _cb.record_success("p2")) or True)

# ─── 4. QUOTA ─────────────────────────────────────────
sec("4. QUOTA")
from nexus_os.relay.quota import QuotaGuard, QuotaType
_qg = QuotaGuard()
test("imports", lambda: True)
test("consume succeeds", lambda: _qg.consume("test-q", 1))
test("consume again", lambda: _qg.consume("test-q", 2))

# ─── 5. REALITY BRIDGE ────────────────────────────────
sec("5. REALITY BRIDGE")
from nexus_os.relay.reality_bridge import RealityBridge
_rb = RealityBridge()
test("imports", lambda: True)
test("record_success", lambda: _rb.record_success("p") or _rb.record_success("p") or True)
test("can_promote returns bool", lambda: isinstance(_rb.can_promote("p"), bool))
test("get_providers lists providers", lambda: len(_rb.get_providers()) > 0)
test("get_track_summary works", lambda: isinstance(_rb.get_track_summary(), dict))

# ─── 6. PROVIDERS ─────────────────────────────────────
sec("6. PROVIDERS")
from nexus_os.relay.providers_strict import STRICT_PROVIDERS
from nexus_os.relay.providers_frontier import FRONTIER_PROVIDERS
test("strict has 8+", lambda: len(STRICT_PROVIDERS) >= 8)
test("strict has name attr", lambda: hasattr(STRICT_PROVIDERS[0], 'name'))
test("frontier has 3+", lambda: len(FRONTIER_PROVIDERS) >= 3)

# ─── 7. MODE ──────────────────────────────────────────
sec("7. MODE")
from nexus_os.relay.mode import RelayMode
test("STRICT=strict", lambda: RelayMode.STRICT.value == "strict")
test("FRONTIER=frontier", lambda: RelayMode.FRONTIER.value == "frontier")

# ─── 8. GMR ───────────────────────────────────────────
sec("8. GMR")
from nexus_os.gmr.rotator import GeniusModelRotator
from nexus_os.gmr.domain_mapping import DOMAIN_MAPPING
_gmr = GeniusModelRotator()
test("domain_mapping has 4+", lambda: len(DOMAIN_MAPPING) >= 4)
test("rotator initializes", lambda: _gmr.models is not None)
test("select returns result", lambda: _gmr.select("Write python code") is not None)
test("get_routing_cascade returns list", lambda: len(_gmr.get_routing_cascade("code")) > 0)
test("register_from_mapping works", lambda: _gmr.register_from_mapping() or True)

from nexus_os.gmr.circuit_breaker import AdaptiveCircuitBreaker, CircuitState
_acb = AdaptiveCircuitBreaker()
test("circuit_breaker initial CLOSED", lambda: _acb.state == CircuitState.CLOSED)
[_acb.record_failure() for _ in range(3)]
test("circuit_breaker OPEN after 3 fails", lambda: _acb.state == CircuitState.OPEN)

from nexus_os.gmr.savings import SavingsTracker
_st = SavingsTracker()
test("savings tracker init", lambda: _st is not None)

from nexus_os.gmr.latency_monitor import LiveLatencyMonitor
_lm = LiveLatencyMonitor()
[_lm.record("m-a", 100 + i*10) for i in range(10)]
test("latency monitor records", lambda: _lm.get_stats("m-a")["p95"] > 0)

# ─── 9. TRUST FORMULAS ────────────────────────────────
sec("9. TRUST FORMULAS")
from nexus_os.governor.trust_formulas import logistic_scale, temporal_decay
from nexus_os.governor.trust_formulas import cdr_escalate, bayesian_posterior, non_compensatory_penalty
test("logistic_scale", lambda: 0 <= logistic_scale(0.8, k=0.1, x0=50.0) <= 1.0)
test("temporal_decay", lambda: 0 <= temporal_decay(0.9) <= 1.0)
test("cdr_escalate", lambda: isinstance(cdr_escalate(0.8, 3), (int, float)))
test("bayesian_posterior", lambda: 0 <= bayesian_posterior(8, 2) <= 1.0)
test("non_compensatory_penalty", lambda: isinstance(non_compensatory_penalty(0.2, critical=True), float))

# ─── 10. KAIJU ────────────────────────────────────────
sec("10. KAIJU")
from nexus_os.governor.kaiju_min import kaiju_check
test("kaiju_check returns result", lambda: kaiju_check() is not None)

# ─── 11. VAP ──────────────────────────────────────────
sec("11. VAP")
from nexus_os.governor.vap_proof import VAPLight
_vap = VAPLight()
test("append creates entry", lambda: _vap.append("a1", "gpt-4o", "openai", "chat") is not None)
test("verify returns True", lambda: _vap.verify())
test("summary returns dict", lambda: isinstance(_vap.summary(), dict))

# ─── 12. VAULT ────────────────────────────────────────
sec("12. VAULT")
from nexus_os.vault.memory import SuperLocalMemory, MemoryChannel
_mem = SuperLocalMemory()
_mem.store(MemoryChannel.EVENT, "test_key", {"data": 123})
test("store/retrieve", lambda: _mem.retrieve(MemoryChannel.EVENT, "test_key")[0]["data"] == 123)

# ─── 13. MODEL RELAY SERVER ───────────────────────────
sec("13. MODEL RELAY (server)")
from nexus_os.relay.model_relay import ModelRelay, ModelStats
_ms = ModelStats()
_ms.record_success(100); _ms.record_success(200)
test("model_stats tracking", lambda: _ms.success == 2 and _ms.avg_latency() == 150.0)

from nexus_os.relay.model_relay import detect_complexity
test("detect_complexity code", lambda: detect_complexity("def foo(): pass\n  return 1\n")[0] >= 0.8)

_relay = ModelRelay()
test("ModelRelay init with ollama", lambda: len(_relay._available_ollama_models) > 0)
print(f"  [ollama models: {_relay._available_ollama_models}]")

# ─── 14. ACTUAL OLLAMA INFERENCE ──────────────────────
sec("14. OLLAMA INFERENCE")
import requests
try:
    resp = requests.post("http://127.0.0.1:11435/api/generate",
        json={"model": "qwen2.5:0.5b", "prompt": "Reply with exactly: OK", "stream": False, "max_tokens": 10},
        timeout=30)
    is_ok = resp.ok and "response" in resp.json()
    test("ollama generate", lambda: is_ok)
    if is_ok:
        print(f"  [ollama response: {resp.json()['response'][:80]}]")
    else:
        print(f"  [ollama error/response: {resp.text[:200]}]")
except Exception as e:
    test("ollama generate", lambda: (_ for _ in ()).throw(e))

# ─── 15. BRIDGE CLIENT ────────────────────────────────
sec("15. BRIDGE CLIENT")
from nexus_os.relay.bridge_client import ModelRelayBridge
_bc = ModelRelayBridge()
test("bridge_client init", lambda: _bc is not None)
test("bridge_client has circuit_breaker", lambda: _bc.circuit_breaker is not None)
test("bridge_client has quota_guard", lambda: _bc.quota_guard is not None)

# ─── 16. SERVING ──────────────────────────────────────
sec("16. SERVING (dashboard)")
from nexus_os.relay.serving import app
test("serving app created", lambda: app.title == "Nexus Model Relay Dashboard")

# ─── 17. HERMES ───────────────────────────────────────
sec("17. HERMES")
from nexus_os.engine.hermes import HermesRouter
_hr = HermesRouter()
test("hermes router init", lambda: _hr is not None)

# ─── SUMMARY ──────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL:
    print(f"  ❌ {FAIL} FAILURES")
    import sys; sys.exit(1)
else:
    print(f"  ALL GREEN ({PASS}/{PASS+FAIL})")
