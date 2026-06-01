"""NEXUS OS — Engine module: Intent routing + Metis v2 tool discipline gates.

P1c upgrade: ToolDisciplineGate — necessity check, appropriateness check,
result audit gate. Blocks wasteful or inappropriate tool calls before they happen.
"""
from enum import Enum
from typing import Optional


class Domain(Enum):
    CODE     = "code"
    REASON  = "reason"
    RESEARCH = "research"
    FAST    = "fast"
    SEC     = "sec"


_KEYWORDS = {
    Domain.CODE:      ["code", "function", "debug", "api", "python", "write", "class"],
    Domain.REASON:    ["think", "analyze", "logic", "reason", "explain"],
    Domain.RESEARCH:  ["search", "find", "investigate", "research", "lookup"],
    Domain.FAST:      ["quick", "brief", "short", "fast", "simple"],
    Domain.SEC:       ["security", "auth", "encrypt", "audit", "safe"],
}

# Map domains to allowed tool categories (minimal viable set for NEXUS OS)
_DOMAIN_TOOLS = {
    Domain.CODE:      ["read_file", "edit_file", "run_bash_command", "create_or_rewrite_file"],
    Domain.REASON:    ["read_file", "run_bash_command"],
    Domain.RESEARCH:  ["read_file", "run_bash_command", "web_search", "grep_search"],
    Domain.FAST:      ["read_file"],
    Domain.SEC:       ["read_file", "run_bash_command", "grep_search"],
}


class Hermes:
    def classify(self, text: str) -> Domain:
        text = text.lower()
        scores = {d: sum(1 for kw in kws if kw in text) for d, kws in _KEYWORDS.items()}
        if max(scores.values()) == 0:
            return Domain.REASON
        return max(scores, key=scores.get)

    def route(self, desc: str) -> dict:
        domain = self.classify(desc)
        return {"domain": domain.value, "keywords": _KEYWORDS[domain]}


class ToolDisciplineGate:
    """P1c: Metis v2-style tool discipline — 3 gates before any tool call."""

    def __init__(self):
        self.hermes = Hermes()
        self._call_log: list[dict] = []

    # ── Gate 1: Necessity ───────────────────────────────────────────────

    def necessity_check(self, prompt: str) -> dict:
        """
        Gate 1 — Does this task actually need a tool?
        Returns {'allowed': bool, 'reason': str}.
        Fast keyword heuristic (replaces full classifier for now).
        """
        tool_indicators = [
            "read", "write", "edit", "create", "delete", "run", "execute",
            "search", "find", "fetch", "download", "list", "check", "get",
            "build", "compile", "test", "deploy",
        ]
        text = prompt.lower()
        need_score = sum(1 for w in tool_indicators if w in text)
        # If fewer than 2 tool indicators, skip tools and answer directly
        if need_score < 2:
            return {
                "allowed": False,
                "reason": "Task doesn't need tools — answering directly",
                "gate": "necessity",
            }
        return {"allowed": True, "reason": "passed", "gate": "necessity"}

    # ── Gate 2: Appropriateness ────────────────────────────────────────

    def appropriateness_check(self, prompt: str, tool_name: str) -> dict:
        """
        Gate 2 — Is the selected tool appropriate for this domain?
        Returns {'allowed': bool, 'reason': str}.
        """
        domain = self.hermes.classify(prompt)
        allowed = _DOMAIN_TOOLS.get(domain, [])
        if tool_name not in allowed:
            return {
                "allowed": False,
                "reason": f"'{tool_name}' inappropriate for domain '{domain.value}'",
                "gate": "appropriateness",
                "domain": domain.value,
                "allowed_tools": allowed,
            }
        return {"allowed": True, "reason": "passed", "gate": "appropriateness"}

    # ── Gate 3: Result audit ────────────────────────────────────────────

    def audit_result(self, prompt: str, tool_name: str, result: str) -> dict:
        """
        Gate 3 — Did the tool output satisfy the intent?
        Returns {'satisfied': bool, 'reason': str}.
        """
        # Heuristic: empty result or error keyword → not satisfied
        result_lower = result.lower() if result else ""
        if not result or len(result) < 5:
            return {"satisfied": False, "reason": "Empty result", "gate": "audit"}
        if "error" in result_lower and "error" not in prompt.lower():
            return {
                "satisfied": False,
                "reason": "Tool returned error; consider alternative",
                "gate": "audit",
            }
        return {"satisfied": True, "reason": "passed", "gate": "audit"}

    # ── Full 3-gate pipeline ───────────────────────────────────────────

    def gates(self, prompt: str, tool_name: str, result: Optional[str] = None) -> dict:
        """
        Run all 3 gates in sequence. Returns dict with per-gate results.
        If gate 1 blocks, gates 2+3 are skipped.
        """
        g1 = self.necessity_check(prompt)
        out = {"necessity": g1}
        if not g1["allowed"]:
            out["appropriateness"] = {"allowed": True, "reason": "skipped"}
            out["audit"] = {"satisfied": True, "reason": "skipped"}
            return out

        g2 = self.appropriateness_check(prompt, tool_name)
        out["appropriateness"] = g2
        if not g2["allowed"]:
            out["audit"] = {"satisfied": True, "reason": "skipped"}
            return out

        if result is not None:
            out["audit"] = self.audit_result(prompt, tool_name, result)
        else:
            out["audit"] = {"satisfied": True, "reason": "skipped (no result)"}
        return out

    # ── Logging ───────────────────────────────────────────────────────

    def log_call(self, prompt: str, tool_name: str, result: str):
        self._call_log.append({
            "prompt": prompt[:100],
            "tool": tool_name,
            "gates": self.gates(prompt, tool_name, result),
        })

    def call_log(self) -> list[dict]:
        return list(self._call_log)
