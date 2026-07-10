"""gmr/coger.py — Cognitive-Inspired Elastic Reasoning (CogER) Router

Implements the CogER framework (arXiv:2512.15089) for dynamic, resource-efficient
reasoning. Classifies queries into 4 complexity levels (L1 to L4) and routes them
to the appropriate execution strategy:
- L1 (No Think): Direct SLM answering
- L2 (Think): Tandem Routing (LLM-SLM collaboration)
- L3 (Extend): Peer-Review Swarm (LLM-PeerReview ensembling with flipped-triple scoring)
- L4 (Delegate): Cognitive Tool-Assisted Reasoning (CoTool delegation)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from nexus_os.gmr.tandem_routing import TandemRouter
from nexus_os.gmr.peer_review import LLMPeerReview

logger = logging.getLogger(__name__)


class CogER:
    """Complexity Classifier and strategy router choosing between Direct SLM, Tandem, or Peer-Review Swarm."""

    def __init__(
        self,
        classifier_model: str = "VibeThinker-3B",
        relay_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        import os
        port = int(os.environ.get("NODERELAY_PORT", "7350"))
        self._relay_url = (relay_url or f"http://127.0.0.1:{port}").rstrip("/")
        self._timeout = timeout
        self.classifier_model = classifier_model
        
        self.tandem_router = TandemRouter(relay_url=self._relay_url, timeout=timeout)
        self.peer_review = LLMPeerReview(relay_url=self._relay_url, timeout=timeout)

    def _call_model(self, model: str, system_prompt: str, user_content: str, max_tokens: int = 512) -> str:
        """Call ModelRelay for chat completions."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self._relay_url}/v1/chat/completions",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.debug("CogER: Failed to call model %s: %s", model, e)
        return ""

    def classify_complexity_heuristically(self, query: str) -> str:
        """Rule-based / Heuristic complexity classification (fast, zero-cost)."""
        query_lower = query.lower()

        # L4: Tool-Enhanced (explicitly mentions tool call, files, system command, network search, or scientific tools)
        tool_keywords = [
            "search the web", "query database", "read file", "write file", 
            "mcp", "tool", "run command", "execute shell", "call api"
        ]
        if any(tk in query_lower for tk in tool_keywords) or self._extract_tool_call_heuristically(query)[0] is not None:
            return "L4"

        # L1: Prompt Answering (extremely simple lookups, facts, basic math)
        if len(query) < 15 and not any(k in query_lower for k in ["how", "why", "analyze", "explain", "code", "write", "implement"]):
            return "L1"

        # L3: Deep Reasoning (complex analysis, coding tasks, logic, proofs)
        deep_keywords = [
            "analyze", "prove", "conjecture", "optimize", "refactor", 
            "complex", "comparison", "peer-review", "swarm", "class ", "def "
        ]
        if any(dk in query_lower for dk in deep_keywords) or len(query) > 200:
            return "L3"

        # L2: CoT Reasoning (medium difficulty, standard questions)
        return "L2"

    def classify_complexity_llm(self, query: str) -> str:
        """Queries the classifier model to categorize query complexity."""
        system_prompt = (
            "You are a cognitive complexity classifier. Categorize the user's query into "
            "one of the following levels:\n"
            "L1: Simple queries, direct lookups, basic arithmetic (No Think)\n"
            "L2: Moderate reasoning, basic logic, math, explanation (Think with CoT)\n"
            "L3: Deep reasoning, analysis, multi-hop logic, coding (Extend with LRM)\n"
            "L4: Highly complex queries requiring external tools, data, or files (Delegate)\n\n"
            "Return the classification in the format: <question level>L_i</question level>"
        )
        response = self._call_model(
            model=self.classifier_model,
            system_prompt=system_prompt,
            user_content=query,
            max_tokens=64
        )
        match = re.search(r"<question level>(L[1-4])</question level>", response)
        if match:
            return match.group(1)
        
        # Fallback to heuristics if parse fails
        return self.classify_complexity_heuristically(query)

    def classify_complexity(self, query: str, use_llm: bool = False) -> str:
        """Wrapper method that decides between LLM or Heuristic classification."""
        if use_llm:
            try:
                return self.classify_complexity_llm(query)
            except Exception:
                pass
        return self.classify_complexity_heuristically(query)

    def _call_direct_slm(self, query: str) -> str:
        """L1 direct answering using a small local model."""
        return self._call_model(
            model="VibeThinker-3B",
            system_prompt="You are a direct answering model. Provide a short, direct answer with no reasoning.",
            user_content=query,
            max_tokens=256
        )

    def _generate_ensemble_candidates(self, query: str) -> List[str]:
        """Generate candidate responses from multiple models for L3 ensembling."""
        candidates = []
        models_pool = ["VibeThinker-3B", "Nanbeige4.1-3B", "fugu"]
        for model in models_pool:
            ans = self._call_model(
                model=model,
                system_prompt="Solve the task step-by-step.",
                user_content=query,
                max_tokens=512
            )
            # P2-3: Never fabricate candidates — empty strings are filtered
            # out downstream rather than polluting the ensemble with
            # synthetic hallucinations.
            if ans:
                candidates.append(ans)
        return candidates

    def _extract_tool_call_heuristically(self, query: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Heuristic regex parser to extract tool name and arguments from query."""
        query_lower = query.lower()
        known_tools = [
            "multiomics_integration",
            "polymer_property_analysis",
            "chemical_safety_assessment",
            "alanine_scanning_pipeline",
            "bioassay_analysis",
            "admet_druglikeness_report",
            "protein_drug_interaction",
            "drug_warning_report"
        ]
        
        # Match tool name
        matched_tool = None
        for t in known_tools:
            if t in query_lower or t.replace("_", " ") in query_lower:
                matched_tool = t
                break
                
        if not matched_tool:
            return None, {}
            
        args = {}
        if matched_tool == "multiomics_integration":
            match = re.search(r"\b([a-nr-z][0-9][a-z0-9]{3,5}|[o][0-9][a-z0-9]{3})\b", query, re.IGNORECASE)
            if match:
                args["uniprot_id"] = match.group(1).upper()
            else:
                words = [w for w in query.split() if w.isupper() and len(w) == 6]
                args["uniprot_id"] = words[0] if words else "P12345"
        elif matched_tool == "polymer_property_analysis":
            match = re.search(r"composition\s+(?:is|of|for)?\s*['\"]?([a-z0-9()]+)['\"]?", query_lower)
            if match:
                args["composition"] = match.group(1).upper()
            else:
                words = [w for w in query.split() if any(c.isdigit() for c in w) and len(w) > 2]
                args["composition"] = words[0] if words else "H2O"
        elif matched_tool == "chemical_safety_assessment":
            match = re.search(r"(?:assessment for|assessment of|safety of|compound)\s+['\"]?([a-z0-9\-]+)['\"]?", query_lower)
            if match:
                args["compound_name"] = match.group(1)
            else:
                words = query.strip().split()
                args["compound_name"] = words[-1] if words else "aspirin"
        elif matched_tool == "alanine_scanning_pipeline":
            match = re.search(r"sequence\s+['\"]?([a-z]+)['\"]?", query_lower)
            if match:
                args["sequence"] = match.group(1).upper()
            else:
                words = [w for w in query.split() if w.isupper() and len(w) > 4 and all(c in "ACDEFGHIKLMNPQRSTVWY" for c in w)]
                args["sequence"] = words[0] if words else "ACDEF"
        elif matched_tool == "bioassay_analysis":
            match = re.search(r"(?:assay|aid)\s+(?:id\s+)?(?:is\s+)?(\d+)", query_lower)
            if match:
                args["assay_id"] = match.group(1)
            else:
                args["assay_id"] = "1234"
        elif matched_tool == "admet_druglikeness_report":
            match = re.search(r"smiles\s+['\"]?([a-z0-9()=#\-\[\]\+\/\\@]+)['\"]?", query_lower)
            if match:
                args["smiles"] = match.group(1)
            else:
                words = [w for w in query.split() if any(c in "=#()[]+/" for c in w)]
                args["smiles"] = words[0] if words else "CC(=O)NC1=CC=C(O)C=C1"
        elif matched_tool == "protein_drug_interaction":
            match_smiles = re.search(r"smiles\s+['\"]?([a-z0-9()=#\-\[\]\+\/\\@]+)['\"]?", query_lower)
            match_seq = re.search(r"sequence\s+['\"]?([a-z]+)['\"]?", query_lower)
            args["smiles"] = match_smiles.group(1) if match_smiles else "CC(=O)NC1=CC=C(O)C=C1"
            args["sequence"] = match_seq.group(1).upper() if match_seq else "ACDEF"
        elif matched_tool == "drug_warning_report":
            match = re.search(r"(?:warning for|warning of|drug)\s+['\"]?([a-z0-9\-]+)['\"]?", query_lower)
            if match:
                args["drug_name"] = match.group(1)
            else:
                words = query.strip().split()
                args["drug_name"] = words[-1] if words else "aspirin"
                
        return matched_tool, args

    def _extract_tool_call_llm(self, query: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Queries the classifier model to extract tool name and arguments."""
        system_prompt = (
            "You are a tool extraction assistant. Given the user's query, identify which scientific tool they want to run and extract its arguments.\n"
            "Available tools and required arguments:\n"
            "- multiomics_integration: uniprot_id (string), genes (array of strings, optional)\n"
            "- polymer_property_analysis: composition (string)\n"
            "- chemical_safety_assessment: compound_name (string)\n"
            "- alanine_scanning_pipeline: sequence (string)\n"
            "- bioassay_analysis: assay_id (string)\n"
            "- admet_druglikeness_report: smiles (string)\n"
            "- protein_drug_interaction: smiles (string), sequence (string)\n"
            "- drug_warning_report: drug_name (string)\n\n"
            "Respond ONLY with a JSON object in the format:\n"
            "{\"tool_name\": \"...\", \"arguments\": {...}}\n"
            "If no tool matches, return {\"tool_name\": null, \"arguments\": {}}"
        )
        response = self._call_model(
            model=self.classifier_model,
            system_prompt=system_prompt,
            user_content=query,
            max_tokens=256
        )
        try:
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(l for l in lines if not l.startswith("```"))
            parsed = json.loads(response.strip())
            return parsed.get("tool_name"), parsed.get("arguments", {})
        except Exception:
            return None, {}

    def _resolve_trust_score(self, trust_score: float | None) -> float:
        """Resolve trust score from caller or TrustKernel singleton.

        P2-3: The old default of 100.0 meant every COGER invocation ran
        with maximum trust, bypassing the governor's trust gates. Unknown
        callers get a conservative 40.0 budget.
        """
        if trust_score is not None:
            return trust_score
        try:
            from nexus_os.governor.trust_kernel import get_trust_kernel
            kernel = get_trust_kernel()
            snapshot = kernel.get_snapshot("coger", "general")
            return snapshot.trust * 100.0  # trust is 0.0-1.0, score is 0-100
        except Exception:
            return 40.0

    def _handle_tool_delegation(self, query: str, trust_score: float | None = None) -> str:
        """L4 Cognitive Tool-Assisted Reasoning delegation (CoTool)."""
        trust = self._resolve_trust_score(trust_score)
        tool_name, arguments = self._extract_tool_call_heuristically(query)
        if not tool_name:
            tool_name, arguments = self._extract_tool_call_llm(query)
            
        if not tool_name:
            return f"Error: No matching scientific tool could be extracted from query: '{query}'"
            
        # P2-3: L4 fail-closed — both bridge and direct client failures
        # return error strings, never fabricated results.
        try:
            from nexus_os.bridge.gross_bridge import GrossMCPBridge
            bridge = GrossMCPBridge()
            reg = bridge.register()
            if reg.success:
                logger.info("CogER: Successfully registered GrossMCPBridge for CoTool execution.")
                result = bridge.call_tool(tool_name, arguments, trust_score=trust)
                if result.blocked:
                    return f"Execution Blocked: {result.reason}"
                if result.is_error:
                    return f"Execution Error: {result.error_message}"
                return json.dumps(result.result, indent=2)
        except Exception as e:
            logger.debug("CogER: Failed to execute via GrossMCPBridge (%s), falling back to direct client", e)
            
        try:
            from nexus_os.bridge.intern_discovery import InternDiscoveryClient
            client = InternDiscoveryClient()
            high_governance_tools = {"chemical_safety_assessment", "drug_warning_report"}
            if tool_name in high_governance_tools and trust < 90.0:
                return (
                    f"Execution Blocked: Trust gate blocked: trust={trust:.1f} < "
                    f"threshold=90.0 for governance tool '{tool_name}'"
                )
            result = client.call_scp_tool(tool_name, arguments)
            if result.is_error:
                return f"Execution Error: {result.error_message}"
            return json.dumps(result.result, indent=2)
        except Exception as e:
            # P2-3: fail-closed — clear error, no silent fabrication
            return f"Execution Blocked: Both GrossMCPBridge and InternDiscoveryClient failed for '{tool_name}': {e}"

    def route(self, query: str, level: Optional[str] = None, use_llm: bool = False, trust_score: float | None = None) -> Dict[str, Any]:
        """Route the query to the optimal strategy based on complexity level."""
        if not level:
            level = self.classify_complexity(query, use_llm=use_llm)
 
        if level == "L1":
            response = self._call_direct_slm(query)
            strategy = "Direct SLM"
        elif level == "L2":
            response = self.tandem_router.route(query)
            strategy = "Tandem Routing"
        elif level == "L3":
            candidates = self._generate_ensemble_candidates(query)
            if not candidates:
                # P2-3: no fabricated fallback — fail with clear error
                response = f"Error: All L3 ensemble models failed to produce candidates for: {query[:80]}"
                strategy = "Peer-Review Swarm (degraded)"
            else:
                best_response, _ = self.peer_review.select_best(query, candidates, use_weighted=True)
                response = best_response
                strategy = "Peer-Review Swarm"
        else:  # L4
            response = self._handle_tool_delegation(query, trust_score=trust_score)
            strategy = "Tool-Enhanced"
 
        # Seam 2: persist the CogER classification + execution outcome.
        # Fail-safe by contract — telemetry must never raise into routing.
        try:
            from nexus_os.gmr.telemetry import record_routing_decision
            _resp = response or ""
            record_routing_decision({
                "source": "coger",
                "coger_level": level,
                "strategy": strategy,
                "outcome": (
                    "error"
                    if not _resp or _resp.startswith(("Error:", "Execution Blocked:", "Execution Error:"))
                    else "success"
                ),
            })
        except Exception:
            pass

        return {
            "level": level,
            "strategy": strategy,
            "response": response,
        }
