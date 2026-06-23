"""tests/gmr/test_coger.py — CogER Router tests"""

import json
import pytest
from unittest.mock import patch, MagicMock

from nexus_os.gmr.coger import CogER


class TestCogER:

    def test_coger_initialization(self):
        coger = CogER(classifier_model="VibeThinker-3B", relay_url="http://mock-relay:7350")
        assert coger.classifier_model == "VibeThinker-3B"
        assert coger.tandem_router._relay_url == "http://mock-relay:7350"
        assert coger.peer_review._relay_url == "http://mock-relay:7350"

    def test_heuristic_classification(self):
        coger = CogER()

        # L1: Prompt Answering (very short, simple)
        assert coger.classify_complexity_heuristically("2 + 2 = ?") == "L1"
        assert coger.classify_complexity_heuristically("hello") == "L1"

        # L4: Tool-Enhanced (explicitly mentioning tools/search/api/database)
        assert coger.classify_complexity_heuristically("Search the web for today's top AI news") == "L4"
        assert coger.classify_complexity_heuristically("Query database for recent user logs") == "L4"

        # L3: Deep Reasoning (complex keywords or long queries)
        assert coger.classify_complexity_heuristically("Analyze the performance constraints in the following method") == "L3"
        assert coger.classify_complexity_heuristically("Prove the Collatz conjecture for N=100") == "L3"
        assert coger.classify_complexity_heuristically("A" * 250) == "L3"

        # L2: CoT Reasoning (moderate)
        assert coger.classify_complexity_heuristically("How many minutes are in 3.5 hours?") == "L2"
        assert coger.classify_complexity_heuristically("Explain how photosynthesis works in plants") == "L2"

    @patch("urllib.request.urlopen")
    def test_llm_classification_success(self, mock_urlopen):
        # Mock successful LLM tag classification
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "The query requires deep logic. <question level>L3</question level>"
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        coger = CogER(classifier_model="VibeThinker-3B")
        level = coger.classify_complexity("Solve this complex puzzle", use_llm=True)
        assert level == "L3"

    @patch("urllib.request.urlopen")
    def test_llm_classification_fallback_on_parse_failure(self, mock_urlopen):
        # Mock malformed LLM response without tags
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Just direct text without tags"
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        coger = CogER(classifier_model="VibeThinker-3B")
        # Should fallback to heuristic check ("hello" -> L1)
        level = coger.classify_complexity("hello", use_llm=True)
        assert level == "L1"

    @patch("urllib.request.urlopen")
    def test_route_l1_direct_slm(self, mock_urlopen):
        # Mock direct SLM response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Direct 4"
                }
            }]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        coger = CogER()
        res = coger.route("2 + 2 = ?")
        assert res["level"] == "L1"
        assert res["strategy"] == "Direct SLM"
        assert "Direct 4" in res["response"]

    @patch("urllib.request.urlopen")
    def test_route_l2_tandem(self, mock_urlopen):
        # Mock two consecutive successful calls: one for blueprint, one for execution
        mock_response_blueprint = MagicMock()
        mock_response_blueprint.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Calculate minutes"
                }
            }]
        }).encode("utf-8")

        mock_response_exec = MagicMock()
        mock_response_exec.read.return_value = json.dumps({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "There are 210 minutes."
                }
            }]
        }).encode("utf-8")

        mock_urlopen.side_effect = [
            MagicMock(__enter__=MagicMock(return_value=mock_response_blueprint)),
            MagicMock(__enter__=MagicMock(return_value=mock_response_exec))
        ]

        coger = CogER()
        res = coger.route("How many minutes in 3.5 hours?")
        assert res["level"] == "L2"
        assert res["strategy"] == "Tandem Routing"
        assert "210 minutes" in res["response"]

    @patch("urllib.request.urlopen")
    def test_route_l3_peer_review(self, mock_urlopen):
        # Mock candidate generations + peer-review selection
        # 3 candidate generations (VibeThinker, Nanbeige, fugu)
        mock_candidates = [
            MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=json.dumps({
                "choices": [{"message": {"content": "Candidate Ans 1"}}]
            }).encode("utf-8"))))),
            MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=json.dumps({
                "choices": [{"message": {"content": "Candidate Ans 2"}}]
            }).encode("utf-8"))))),
            MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=json.dumps({
                "choices": [{"message": {"content": "Candidate Ans 3"}}]
            }).encode("utf-8")))))
        ]
        
        # 3 triplets evaluated normal, 3 flipped. To simplify we can mock peer_review._call_judge or flipped_triple_scoring
        # Let's mock LLMPeerReview.flipped_triple_scoring to return a mocked dictionary of scores directly
        coger = CogER()
        
        # Patch flipped_triple_scoring to return scores favoring Candidate 2 (orig_index = 1)
        mock_scores = {
            0: [3.0, 3.2],
            1: [4.8, 4.9],
            2: [3.5, 3.6]
        }
        
        with patch.object(coger.peer_review, "flipped_triple_scoring", return_value=mock_scores):
            # Patch _call_model to return candidate answers
            with patch.object(coger, "_call_model", side_effect=["Candidate Ans 1", "Candidate Ans 2", "Candidate Ans 3"]):
                res = coger.route("Analyze this logic", level="L3")
                assert res["level"] == "L3"
                assert res["strategy"] == "Peer-Review Swarm"
                assert res["response"] == "Candidate Ans 2"

    def test_route_l4_delegate_success(self):
        coger = CogER()
        res = coger.route("Run chemical safety assessment for aspirin", trust_score=95.0)
        assert res["level"] == "L4"
        assert res["strategy"] == "Tool-Enhanced"
        assert "chemical_safety_assessment" in res["response"]
        assert "aspirin" in res["response"]
        assert "confidence_score" in res["response"]

    def test_route_l4_delegate_blocked_by_trust(self):
        coger = CogER()
        res = coger.route("Run chemical safety assessment for aspirin", trust_score=50.0)
        assert res["level"] == "L4"
        assert res["strategy"] == "Tool-Enhanced"
        assert "Trust gate blocked" in res["response"] or "Blocked by Progent" in res["response"]
