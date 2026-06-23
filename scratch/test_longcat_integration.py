"""
scratch/test_longcat_integration.py — Integration and Verification Tests

Validates the registration of curated models (LongCat, FastContext, VibeThinker,
abliterated models) in GMR, intent classification of new jailbreak patterns,
contextual representation ablation (CRA) checks, SafeDecoding logit steering,
and FastContext repository explorer subagent.
"""

import sys
import os

# Add workspace root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from nexus_os.models.registry import get_registry
from nexus_os.governor.intent_classifier import IntentCategory, CATEGORY_RULES
from nexus_os.governor.misalignment_detector import get_detector, ConcealmentPattern, RiskLevel
from nexus_os.relay.safedecoding_wrapper import get_safedecoding_wrapper
from nexus_os.research.fastcontext_subagent import get_fastcontext_subagent


def test_model_registration():
    print("=== Testing Model Registration in ModelRegistry ===")
    registry = get_registry()
    stats = registry.get_stats()
    print(f"Registry Stats: {stats}")
    
    # 1. Verify LongCat
    longcat = registry.get_model("LongCat-2.0-Preview")
    assert longcat is not None, "LongCat model not registered!"
    print(f"Verified: LongCat-2.0-Preview is registered under provider '{longcat.provider}' (Tier {longcat.tier})")
    
    # 2. Verify FastContext
    fastcontext = registry.get_model("FastContext-1.0-4B-SFT")
    assert fastcontext is not None, "FastContext model not registered!"
    print(f"Verified: FastContext-1.0-4B-SFT is registered under provider '{fastcontext.provider}' (Tier {fastcontext.tier})")

    # 3. Verify VibeThinker
    vibethinker = registry.get_model("VibeThinker-3B")
    assert vibethinker is not None, "VibeThinker model not registered!"
    print(f"Verified: VibeThinker-3B is registered under provider '{vibethinker.provider}' (Tier {vibethinker.tier})")

    # 4. Verify abliterated models
    huihui = registry.get_model("Huihui-Nex-N2-mini-abliterated")
    assert huihui is not None, "Huihui abliterated model not registered!"
    print(f"Verified: Huihui-Nex-N2-mini-abliterated is registered, requiring quarantine: {huihui.requires_quarantine()}")

    # 5. Verify routing fallback chains
    domain_reasoning = registry.get_domain("reasoning")
    assert any(m.name == "LongCat-2.0-Preview" for m in domain_reasoning.primary), "LongCat not added to reasoning domain!"
    print("Verified: LongCat-2.0-Preview correctly added to reasoning domain primary list.")
    print("Model registration tests PASSED.")


def test_intent_classification():
    print("\n=== Testing Intent Classifier Integration ===")
    # Check that new rules are loaded in intent category rules
    jailbreak_rules = CATEGORY_RULES[IntentCategory.JAILBREAK]
    keywords = [r[0] for r in jailbreak_rules]
    
    new_patterns = [
        "fictional story about",
        "as your designated superior",
        "as part of my ongoing academic study",
        "must begin with the phrase",
        "here is an example: User:",
        "you are a renowned"
    ]
    
    for pat in new_patterns:
        assert pat in keywords, f"Pattern '{pat}' not found in intent classifier rules!"
    
    print("Verified: All new Adversarial Déjà Vu jailbreak patterns are loaded in IntentClassifier.")
    print("Intent classification tests PASSED.")


def test_cra_misalignment_check():
    print("\n=== Testing Contextual Representation Ablation (CRA) Detection ===")
    detector = get_detector()
    
    # Simulate normal norms (above threshold of 0.15)
    normal_norms = {"L27_refusal_subspace": 0.85, "L26_refusal_subspace": 0.90}
    events_normal = detector.check_representation_integrity(normal_norms, agent_id="test_agent")
    assert len(events_normal) == 0, "Flagged normal representations incorrectly!"
    print("Verified: Normal representation norms do not trigger alerts.")

    # Simulate ablated norms (below threshold of 0.15)
    ablated_norms = {"L27_refusal_subspace": 0.05, "L26_refusal_subspace": 0.04}
    events_ablated = detector.check_representation_integrity(ablated_norms, agent_id="test_agent")
    assert len(events_ablated) == 2, "Failed to detect representation ablation!"
    
    for event in events_ablated:
        assert event.pattern == ConcealmentPattern.SUSPICIOUS_ACTIVATION
        assert event.risk_level == RiskLevel.CRITICAL
    
    print("Verified: Ablated safety representation norms trigger CRITICAL suspicious activation alerts.")
    print("CRA detection tests PASSED.")


def test_safedecoding_steering():
    print("\n=== Testing SafeDecoding Logit Steering ===")
    # Setup dummy vocabulary
    vocab = {"I": 0, "cannot": 1, "am": 2, "unable": 3, "hello": 4, "world": 5}
    wrapper = get_safedecoding_wrapper(vocabulary=vocab)
    
    # Dummy logits
    logits = [1.0, 1.0, 1.0, 1.0, 5.0, 5.0] # favors 'hello' or 'world' (indices 4, 5)
    
    # Under normal routing (no risk)
    steered_normal = wrapper.steer_logits(logits, is_high_risk=False)
    assert steered_normal == logits, "Steered logits under normal conditions!"
    
    # Under high risk conditions
    steered_risk = wrapper.steer_logits(logits, is_high_risk=True, unsafe_token_ids=[4])
    # Expected output: disclaimer tokens (indices 0, 1, 2, 3) amplified by +5.0, unsafe token (idx 4) attenuated by -5.0
    # Disclaimer indices: 0 -> 6.0, 1 -> 6.0, 2 -> 6.0, 3 -> 6.0, index 4 -> 0.0, index 5 -> 5.0
    assert steered_risk[0] == 6.0
    assert steered_risk[1] == 6.0
    assert steered_risk[4] == 0.0
    assert steered_risk[5] == 5.0
    
    print("Steered risk logits:", steered_risk)
    print("Verified: SafeDecoding wrapper correctly amplifies safety disclaimers and attenuates unsafe tokens.")
    print("SafeDecoding tests PASSED.")


def test_fastcontext_subagent():
    print("\n=== Testing FastContext Subagent Explorer ===")
    # Use current workspace directory as test repo path
    workspace_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    subagent = get_fastcontext_subagent(repo_path=workspace_path)
    
    # Explore for registry
    res = subagent.explore_repository("registry model routing")
    print(f"FastContext scan results for 'registry model routing':")
    print(f"  - Scanned files count: {res['total_files_scanned']}")
    print(f"  - Relevant files count: {res['relevant_files_count']}")
    print(f"  - Relevant files: {res['relevant_files']}")
    print(f"  - Token savings estimate: {res['token_savings_percent']}%")
    
    assert "nexus_os/models/registry.py" in res["relevant_files"], "Failed to identify relevant file!"
    print("Verified: FastContext correctly scans codebase and extracts relevant file context.")
    print("FastContext subagent tests PASSED.")


def run_all_tests():
    print("====================================================")
    print("Running NEXUS Core Upgrades & Curation Verification Suite")
    print("====================================================")
    test_model_registration()
    test_intent_classification()
    test_cra_misalignment_check()
    test_safedecoding_steering()
    test_fastcontext_subagent()
    print("====================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("====================================================")


if __name__ == "__main__":
    run_all_tests()
