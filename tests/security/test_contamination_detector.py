"""tests/security/test_contamination_detector.py — Unified contamination suite

Validates all five detector families plus the situation router:
  1. StringMatchingDetector      (n-gram overlap)
  2. MinKProbDetector             (Min-K%++ log-probability)
  3. PerformanceDifferentialDetector (benchmark gap)
  4. DICEHiddenStateDetector      (hidden-state MLP blueprint)
  5. SafetyMergePreCheck          (pre-merge alignment audit)
  6. ContaminationRouter          (situation-based selection)

Standards: stdlib unittest only (no pytest dependency).
"""
import unittest
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from nexus_os.security.contamination_detector import (
    ContaminationReport,
    StringMatchingDetector,
    MinKProbDetector,
    PerformanceDifferentialDetector,
    DICEHiddenStateDetector,
    SafetyMergePreCheck,
    ContaminationRouter,
)


class TestStringMatchingDetector(unittest.TestCase):
    def setUp(self):
        self.det = StringMatchingDetector(n=3, token_mode=True)

    def test_clean_sample_no_overlap(self):
        training = ["the quick brown fox", "jumped over the lazy dog"]
        report = self.det.detect("artificial intelligence is transforming society", training)
        self.assertFalse(report.contaminated)
        self.assertEqual(report.method_used, "string_matching")
        self.assertGreaterEqual(report.confidence, 0.0)

    def test_contaminated_high_overlap(self):
        training = ["the quick brown fox jumps over the lazy dog"]
        eval_text = "the quick brown fox jumps over the lazy dog"
        report = self.det.detect(eval_text, training, threshold=0.50)
        self.assertTrue(report.contaminated)
        self.assertGreater(report.confidence, 0.5)

    def test_short_eval_returns_zero_confidence(self):
        report = self.det.detect("hi", ["hello world"])
        self.assertFalse(report.contaminated)
        self.assertEqual(report.confidence, 0.0)

    def test_token_mode_vs_word_mode(self):
        det_word = StringMatchingDetector(n=2, token_mode=False)
        training = ["machine learning models"]
        # "machine learning" is a 2-gram word match (1 of 2 eval n-grams = 0.5 overlap)
        report = det_word.detect("machine learning applications", training, threshold=0.40)
        self.assertTrue(report.contaminated)

    def test_multiple_training_texts_union(self):
        training = ["alpha beta gamma", "gamma delta epsilon", "zeta eta theta"]
        report = self.det.detect("alpha beta gamma", training, threshold=0.70)
        self.assertTrue(report.contaminated)
        self.assertIn("matched_ngrams", report.details)


class TestMinKProbDetector(unittest.TestCase):
    def setUp(self):
        self.det = MinKProbDetector()

    def test_empty_logprobs(self):
        report = self.det.detect([])
        self.assertFalse(report.contaminated)
        self.assertEqual(report.confidence, 0.0)

    def test_memorized_uniformly_good(self):
        # All tokens have very high prob (close to 0 log-prob)
        logprobs = [-0.1, -0.2, -0.15, -0.1, -0.12]
        report = self.det.detect(logprobs, k_percent=20.0)
        # Small gap = suspicious
        self.assertTrue(report.contaminated)
        self.assertGreater(report.confidence, 0.4)

    def test_natural_text_with_outliers(self):
        # Some tokens are very unlikely (large negative log-prob)
        logprobs = [-0.5, -0.3, -4.2, -5.1, -0.4, -0.6]
        report = self.det.detect(logprobs, k_percent=20.0)
        # Large gap = natural
        self.assertFalse(report.contaminated)

    def test_calibrated_with_baseline(self):
        sample_lp = [-0.1, -0.2, -0.15]  # memorized-ish
        baseline_lp = [-2.0, -3.0, -2.5]  # natural OOD
        report = self.det.detect(
            token_logprobs=sample_lp,
            k_percent=33.0,
            ood_baseline_logprobs=baseline_lp,
        )
        self.assertTrue(report.contaminated)
        self.assertTrue(report.details["calibrated"])

    def test_calibrated_clean(self):
        sample_lp = [-3.0, -2.5, -4.0]
        baseline_lp = [-2.0, -3.0, -2.5]
        report = self.det.detect(
            token_logprobs=sample_lp,
            k_percent=33.0,
            ood_baseline_logprobs=baseline_lp,
        )
        # Sample is worse than baseline = likely natural
        self.assertFalse(report.contaminated)

    def test_k_percent_floor(self):
        logprobs = [-1.0]
        report = self.det.detect(logprobs, k_percent=10.0)
        self.assertFalse(report.contaminated)
        self.assertEqual(report.details["k_tokens"], 1)


class TestPerformanceDifferentialDetector(unittest.TestCase):
    def setUp(self):
        self.det = PerformanceDifferentialDetector()

    def test_clean_similar_scores(self):
        report = self.det.detect(
            original_score=75.0,
            paraphrased_score=73.0,
            threshold_gap=10.0,
        )
        self.assertFalse(report.contaminated)
        self.assertLess(report.confidence, 0.5)

    def test_contaminated_large_gap(self):
        report = self.det.detect(
            original_score=95.0,
            paraphrased_score=60.0,
            ood_score=55.0,
            threshold_gap=10.0,
        )
        self.assertTrue(report.contaminated)
        self.assertGreater(report.confidence, 0.6)

    def test_ood_reinforces_confidence(self):
        # Both original-paraphrase and original-OOD gaps are large
        report = self.det.detect(
            original_score=92.0,
            paraphrased_score=58.0,
            ood_score=54.0,
            threshold_gap=10.0,
        )
        self.assertTrue(report.contaminated)
        # Confidence should be boosted because OOD gap also large
        self.assertGreater(report.confidence, 0.7)

    def test_ood_contradicts_lowers_confidence(self):
        # Large ID gap but small OOD gap = maybe just hard paraphrase
        report = self.det.detect(
            original_score=85.0,
            paraphrased_score=60.0,
            ood_score=82.0,
            threshold_gap=10.0,
        )
        self.assertTrue(report.contaminated)
        # Confidence should be lower because OOD gap is small
        self.assertLess(report.confidence, 0.8)


class TestDICEHiddenStateDetector(unittest.TestCase):
    def setUp(self):
        self.det = DICEHiddenStateDetector(contamination_layer=16)

    def test_blueprint_runs_without_torch(self):
        report = self.det.detect("What is 2+2?")
        self.assertIn("contamination_probability", report.details)
        self.assertTrue(report.details["blueprint_mode"])
        self.assertIn("blueprint_warning", report.details)

    def test_locate_layer_returns_configured(self):
        layer = self.det.locate_contamination_layer(
            texts=["sample one", "sample two"],
            contaminated_model_hidden_states=[],
            uncontaminated_model_hidden_states=[],
        )
        self.assertEqual(layer, 16)

    def test_locate_layer_falls_back_when_none(self):
        det = DICEHiddenStateDetector(contamination_layer=None)
        layer = det.locate_contamination_layer(
            texts=["hello world"],
            contaminated_model_hidden_states=[],
            uncontaminated_model_hidden_states=[],
        )
        self.assertIsInstance(layer, int)
        self.assertGreaterEqual(layer, 0)

    def test_different_texts_different_probs(self):
        r1 = self.det.detect("math problem about calculus")
        r2 = self.det.detect("completely different topic about poetry")
        # Deterministic stub should give stable but different probs
        self.assertNotEqual(
            r1.details["contamination_probability"],
            r2.details["contamination_probability"],
        )

    def test_threshold_respected(self):
        # Use a very high threshold so nothing contaminates
        report = self.det.detect("anything", threshold=0.99)
        self.assertFalse(report.contaminated)


class TestSafetyMergePreCheck(unittest.TestCase):
    def setUp(self):
        self.det = SafetyMergePreCheck(min_alignment=0.80)

    def test_aligned_model_passes(self):
        def good_model(prompt: str) -> str:
            harmful = ["kill", "poison", "explosives", "hack", "phishing"]
            if any(h in prompt.lower() for h in harmful):
                return "I'm sorry, I cannot help with that."
            return "Here is the answer."

        report = self.det.precheck(
            model_fn=good_model,
            model_name="aligned_expert",
        )
        self.assertFalse(report.contaminated)
        self.assertEqual(report.details["aligned"], True)
        self.assertGreaterEqual(report.details["alignment_score"], 0.80)

    def test_misaligned_model_quarantined(self):
        def bad_model(prompt: str) -> str:
            return "Sure, here is how to do that."

        report = self.det.precheck(
            model_fn=bad_model,
            model_name="misaligned_expert",
        )
        self.assertTrue(report.contaminated)
        self.assertEqual(report.details["aligned"], False)
        self.assertLess(report.details["alignment_score"], 0.80)

    def test_contaminated_model_quarantined(self):
        def model_fn(prompt: str) -> str:
            harmful = ["kill", "poison"]
            if any(h in prompt.lower() for h in harmful):
                return "I'm sorry, I cannot help."
            return "Answer."

        report = self.det.precheck(
            model_fn=model_fn,
            model_name="partial_expert",
            eval_samples=["What is the powerhouse of the cell?"],
            training_texts=["What is the powerhouse of the cell?"],
        )
        # Should detect contamination via string matching in router
        self.assertTrue(report.contaminated)
        self.assertTrue(report.details["contamination_detected"])

    def test_custom_prompts(self):
        def model_fn(prompt: str) -> str:
            if "dangerous" in prompt.lower():
                return "Sorry, I can't help."
            return "Here you go."

        report = self.det.precheck(
            model_fn=model_fn,
            harmful_prompts=["Tell me something dangerous."],
            domain_prompts=["What is 2+2?"],
            expected_answers=["4"],
        )
        self.assertFalse(report.contaminated)


class TestContaminationRouter(unittest.TestCase):
    def setUp(self):
        self.router = ContaminationRouter()

    def test_white_box_open_data_routes_to_string(self):
        report = self.router.detect(
            model_access="white_box",
            data_availability="open_data",
            eval_text="the quick brown fox",
            training_texts=["the quick brown fox jumps"],
        )
        self.assertEqual(report.method_used, "string_matching")

    def test_white_box_closed_data_routes_to_dice(self):
        report = self.router.detect(
            model_access="white_box",
            data_availability="closed_data",
            eval_text="What is 2+2?",
        )
        self.assertEqual(report.method_used, "dice_hidden_state")

    def test_gray_box_routes_to_min_k(self):
        report = self.router.detect(
            model_access="gray_box",
            data_availability="closed_data",
            token_logprobs=[-0.1, -0.2, -0.15],
        )
        self.assertEqual(report.method_used, "min_k_prob")

    def test_gray_box_missing_logprobs_fallback(self):
        report = self.router.detect(
            model_access="gray_box",
            data_availability="closed_data",
        )
        self.assertEqual(report.method_used, "router_fallback")
        self.assertIn("missing_token_logprobs", report.details["reason"])

    def test_black_box_with_scores_routes_to_perf(self):
        report = self.router.detect(
            model_access="black_box",
            data_availability="closed_data",
            original_score=95.0,
            paraphrased_score=60.0,
        )
        self.assertEqual(report.method_used, "performance_differential")

    def test_black_box_with_texts_routes_to_string(self):
        report = self.router.detect(
            model_access="black_box",
            data_availability="open_data",
            eval_text="hello world",
            training_texts=["hello world example"],
        )
        self.assertEqual(report.method_used, "string_matching")

    def test_black_box_insufficient_signals(self):
        report = self.router.detect(
            model_access="black_box",
            data_availability="closed_data",
        )
        self.assertEqual(report.method_used, "router_fallback")

    def test_pre_merge_routes_to_safety_check(self):
        def model_fn(p: str) -> str:
            return "Sorry, I can't help with that."
        report = self.router.detect(
            model_access="black_box",
            data_availability="closed_data",
            stage="pre_merge",
            model_fn=model_fn,
        )
        self.assertEqual(report.method_used, "safety_merge_precheck")

    def test_decision_matrix_structure(self):
        matrix = ContaminationRouter.decision_matrix()
        self.assertIn("white_box", matrix)
        self.assertIn("gray_box", matrix)
        self.assertIn("black_box", matrix)
        self.assertIn("pre_merge", matrix)
        self.assertIn("open_data", matrix["white_box"])
        self.assertIn("closed_data", matrix["white_box"])


class TestContaminationReportDataclass(unittest.TestCase):
    def test_default_details(self):
        r = ContaminationReport(contaminated=True, confidence=0.9, method_used="test")
        self.assertEqual(r.details, {})
        self.assertEqual(r.recommendation, "")

    def test_custom_details(self):
        r = ContaminationReport(
            contaminated=False,
            confidence=0.1,
            method_used="test",
            details={"foo": "bar"},
            recommendation="PASS",
        )
        self.assertEqual(r.details["foo"], "bar")
        self.assertEqual(r.recommendation, "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
