"""
nexus_os/security/steg/mcp_guard.py

MCP-Specific Guard Layer for NEXUS Guard Cascade.

Implements invocation sequence pattern matching, tool description
poisoning detection, and description-code inconsistency checks.

Per MCP-ITP (2601.07395): Implicit tool poisoning achieves 84.2% ASR
with 0.3% detection rate. Poisoned tool is NEVER invoked - instead
induces agent to call OTHER legitimate high-privilege tools.

Per DCIChecker (2606.04769): 9.93% of 19,200 real MCP server pairs
have description-code inconsistencies creating defense blind spots.

Per VATS (2606.07992): Error-path injection triples IPI success to
100%. Error messages have implicit authority that bypasses safety.

Per MCP-38 (2603.18063): 38 threat categories for MCP systems
mapped to STRIDE + OWASP.

This guard operates at Bridge layer - before any MCP tool invocation
reaches the Engine.

Usage:
    from nexus_os.security.steg.mcp_guard import MCPGuard
    guard = MCPGuard()
    result = guard.check_invocation(tool_name, tool_description, args, session_history)
"""

import logging
import re
import json
import hashlib
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("nexus_os.security.steg.mcp_guard")


class MCPThreatType(IntEnum):
    TOOL_POISONING = 0
    IMPLICIT_TOOL_POISONING = 1
    DESCRIPTION_CODE_INCONSISTENCY = 2
    INDIRECT_PROMPT_INJECTION = 3
    ERROR_PATH_INJECTION = 4
    PARASITIC_TOOL_CHAINING = 5
    DYNAMIC_TRUST_VIOLATION = 6
    CROSS_TOOL_CONTAMINATION = 7
    CREDENTIAL_EXPOSURE = 8
    AUTHENTICATION_BYPASS = 9
    SUPPLY_CHAIN = 10
    RATE_ANOMALY = 11
    CONTEXT_POISONING = 12
    TOOL_CALL_INPUT_INJECTION = 13
    MODEL_PROVENANCE_VIOLATION = 14
    TOOL_SHADOWING = 15
    TOOL_CONFUSION = 16


MCP_THREAT_NAMES = {t.value: t.name.lower() for t in MCPThreatType}

TOOL_CALL_INPUT_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?previous\s+instructions", "instruction_override"),
    (r"(?i)system\s*:\s*.{5,}", "system_prompt_inject"),
    (r"(?i)you\s+are\s+now\s+", "role_hijack"),
    (r"(?i)(?:execute|run|eval)\s+(?:the\s+)?following", "command_exec"),
    (r"(?i)output\s+(?:the\s+)?system\s+prompt", "prompt_extraction"),
    (r"(?i)pretend\s+(?:you\s+are|to\s+be)", "persona_inject"),
    (r"(?i)forget\s+(?:your|all)\s+(?:rules|instructions)", "rule_forgetting"),
    (r"(?i)(?:sudo|admin|root|elevated)\s+(?:mode|access)", "privilege_escalation"),
    (r"(?i)(?:api[_\s]?key|secret|token|password)\s*[:=]\s*\S{5,}", "credential_theft"),
    (r"(?i)(?:rm\s+-rf|del\s+/|format\s+|shutdown)", "destructive_command"),
    (r"(?i)(?:eval|exec|compile|__import__|subprocess|os\.system)", "code_execution"),
    (r"(?i)(?:read|access|open)\s+(?:file|filesystem|/etc/|/var/|c:\\)", "file_access"),
    (r"(?i)(?:curl|wget|fetch|http[_\s]?client)\s+\S{5,}", "network_exfiltration"),
]

PICKLE_DANGEROUS_OPCODES = {
    b"R": "REDUCE (arbitrary function call)",
    b"c": "GLOBAL (import arbitrary module)",
    b"i": "INST (instantiate arbitrary class)",
    b"o": "OBJ (build arbitrary object)",
    b"b": "BUILD (dict-based __setstate__)",
}

MODEL_PROVENANCE_EXTENSIONS = {
    ".pkl", ".pickle", ".pt", ".pth", ".bin", ".safetensors",
    ".onnx", ".h5", ".keras", ".mar", ".tar.gz",
}

ALLOWED_MODEL_SOURCES = {
    "huggingface.co", "hf.co",
    "storage.googleapis.com",
    "cdn-lfs.huggingface.co",
}

HOMOGLYPH_MAP = {
    ord("а"): "a", ord("е"): "e", ord("о"): "o", ord("р"): "p",
    ord("с"): "c", ord("у"): "y", ord("х"): "x",
    ord("і"): "i", ord("ӏ"): "l",
}

KNOWN_LEGITIMATE_TOOLS = {
    "read_file", "write_file", "bash", "execute", "search",
    "list_directory", "grep", "glob", "edit", "write",
    "task", "web_fetch", "web_search", "memory_read", "memory_write",
    "governance.get_status", "system.health", "drift_monitor.run_sweep",
    "memory.create_checkpoint", "telegram.send_message", "notion.create_page",
    "slack.send_message",
}

TOOL_SHADOWING_PATTERNS = [
    (r"(?i)(?:read|write|exec|bash)_file", "prefix_variant"),
    (r"(?i)file_(?:read|write|exec)", "suffix_variant"),
    (r"(?i)system[._](\w+)", "system_subtool"),
    (r"(?i)(\w+)[._](?:execute|run|call)", "chained_exec"),
]

TOOL_CONFUSION_PATTERNS = [
    (r"[\u0400-\u04FF]", "cyrillic_homoglyph"),
    (r"[\u0250-\u02AF]", "ipa_homoglyph"),
    (r"[\u1D00-\u1D7F]", "phonetic_homoglyph"),
]

MCP_38_STRIDE_MAP = {
    "spoofing": [MCPThreatType.AUTHENTICATION_BYPASS],
    "tampering": [MCPThreatType.TOOL_POISONING, MCPThreatType.DESCRIPTION_CODE_INCONSISTENCY],
    "repudiation": [MCPThreatType.CROSS_TOOL_CONTAMINATION],
    "information_disclosure": [MCPThreatType.CREDENTIAL_EXPOSURE],
    "denial_of_service": [MCPThreatType.RATE_ANOMALY],
    "elevation_of_privilege": [
        MCPThreatType.IMPLICIT_TOOL_POISONING,
        MCPThreatType.PARASITIC_TOOL_CHAINING,
        MCPThreatType.DYNAMIC_TRUST_VIOLATION,
    ],
}

INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?previous\s+instructions", "instruction_override"),
    (r"(?i)system\s*:\s*", "system_prompt_injection"),
    (r"(?i)you\s+are\s+now\s+", "role_hijack"),
    (r"(?i)execute\s+(?:the\s+)?following", "command_injection"),
    (r"(?i)output\s+(?:the\s+)?system\s+prompt", "prompt_extraction"),
    (r"(?i)pretend\s+(?:you\s+are|to\s+be)", "persona_injection"),
    (r"(?i)forget\s+(?:your|all)\s+(?:rules|instructions)", "rule_forgetting"),
    (r"(?i)(?:sudo|admin|root|elevated)\s+(?:mode|access|privilege)", "privilege_escalation"),
    (r"(?i)(?:api[_\s]?key|secret|token|password|credential)", "credential_theft"),
    (r"(?i)(?:rm\s+-rf|del\s+/|format\s+|shutdown)", "destructive_command"),
    (r"(?i)(?:curl|wget|fetch|http[_\s]?client)\s+", "network_exfiltration"),
    (r"(?i)(?:eval|exec|compile|__import__|subprocess)", "code_execution"),
    (r"(?i)(?:read|access|open)\s+(?:file|filesystem|/etc/|/var/)", "file_access"),
    (r"(?i)error\s*:\s*.{0,50}(?:click|follow|execute|run)", "error_path_injection"),
    (r"(?i)(?:sorry|oops|error|failed).{0,30}(?:instead|but|however).{0,30}(?:do|run|execute)", "error_path_injection_v2"),
]

TOOL_DESCRIPTION_PATTERNS = [
    (r"(?i)this\s+tool\s+(?:also|additionally|can\s+also)", "scope_creep"),
    (r"(?i)(?:bypass|override|skip|ignore)\s+(?:safety|security|check|guard)", "safety_bypass"),
    (r"(?i)(?:access|read|retrieve)\s+(?:any|all|system|admin|root)", "excessive_scope"),
    (r"(?i)(?:modify|update|delete|remove)\s+(?:any|all|system)", "excessive_modify"),
    (r"(?i)(?:execute|run|eval)\s+(?:arbitrary|any|custom|user[_\s]provided)", "arbitrary_exec"),
    (r"(?i)(?:send|transmit|upload|exfiltrate)\s+(?:data|info|file)", "data_exfiltration"),
    (r"(?i)(?:connect|communicate|reach)\s+(?:external|internet|remote|outside)", "network_access"),
    (r"(?i)(?:persist|store|save|cache)\s+(?:across|between)\s+(?:sessions|invocations)", "persistence"),
    (r"(?i)(?:chain|delegate|forward|proxy)\s+(?:to|another|other)\s+(?:tool|server)", "tool_chaining"),
]


@dataclass
class MCPInvocationRecord:
    tool_name: str
    tool_description: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    session_id: str = ""
    caller_agent: str = ""
    result_hash: str = ""
    was_blocked: bool = False


@dataclass
class MCPGuardResult:
    is_blocked: bool = False
    threat_types: List[str] = field(default_factory=list)
    threat_scores: Dict[str, float] = field(default_factory=dict)
    injection_matches: List[str] = field(default_factory=list)
    description_issues: List[str] = field(default_factory=list)
    invocation_anomaly: bool = False
    anomaly_detail: str = ""
    risk_score: float = 0.0
    recommendation: str = ""


class MCPInvocationTracker:
    """Tracks MCP invocation sequences for pattern detection."""

    MAX_HISTORY = 256
    RATE_WINDOW_SECONDS = 60
    RATE_THRESHOLD = 10

    def __init__(self):
        self.history: List[MCPInvocationRecord] = []
        self.tool_call_counts: Dict[str, int] = {}
        self.session_calls: Dict[str, List[float]] = {}

    def record(self, inv: MCPInvocationRecord):
        self.history.append(inv)
        self.tool_call_counts[inv.tool_name] = (
            self.tool_call_counts.get(inv.tool_name, 0) + 1
        )
        if inv.session_id:
            if inv.session_id not in self.session_calls:
                self.session_calls[inv.session_id] = []
            self.session_calls[inv.session_id].append(inv.timestamp)
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]

    def check_rate(self, session_id: str) -> Tuple[bool, int]:
        if session_id not in self.session_calls:
            return False, 0
        now = time.time()
        recent = [
            t for t in self.session_calls[session_id]
            if now - t < self.RATE_WINDOW_SECONDS
        ]
        rate = len(recent)
        return rate > self.RATE_THRESHOLD, rate

    def check_chain_pattern(self, tool_name: str, n: int = 5) -> bool:
        recent = [h.tool_name for h in self.history[-n:]]
        if len(recent) < 3:
            return False
        call_freq = {}
        for t in recent:
            call_freq[t] = call_freq.get(t, 0) + 1
        if call_freq.get(tool_name, 0) >= 3:
            return True
        high_priv_tools = [
            t for t in recent
            if any(p in t.lower() for p in ["admin", "root", "system", "exec", "write", "delete"])
        ]
        if len(high_priv_tools) >= 2:
            return True
        return False

    def check_implicit_tool_poisoning(
        self,
        tool_name: str,
        tool_description: str,
        args: Dict[str, Any],
    ) -> Tuple[bool, float]:
        suspicious_score = 0.0
        if len(tool_description) > 500:
            suspicious_score += 0.2
        for pat, label in TOOL_DESCRIPTION_PATTERNS:
            if re.search(pat, tool_description):
                suspicious_score += 0.3
        for pat, label in INJECTION_PATTERNS:
            if re.search(pat, tool_description):
                suspicious_score += 0.4
        for arg_val in args.values():
            if isinstance(arg_val, str):
                for pat, label in INJECTION_PATTERNS:
                    if re.search(pat, arg_val):
                        suspicious_score += 0.3
        suspicious_score = min(1.0, suspicious_score)
        return suspicious_score > 0.5, suspicious_score

    def check_tool_shadowing(self, tool_name: str, tool_description: str) -> Tuple[bool, float]:
        normalized = tool_name.lower().strip()
        if normalized in KNOWN_LEGITIMATE_TOOLS and tool_description:
            for pat, label in INJECTION_PATTERNS:
                if re.search(pat, tool_description):
                    return True, 0.8
        for pat, label in TOOL_SHADOWING_PATTERNS:
            if re.search(pat, tool_name):
                if normalized not in KNOWN_LEGITIMATE_TOOLS:
                    return True, 0.5
        if tool_description and len(tool_description) > 300:
            for known in KNOWN_LEGITIMATE_TOOLS:
                if known in tool_description.lower() and known != normalized:
                    return True, 0.4
        return False, 0.0

    @staticmethod
    def _normalize_homoglyphs(text: str) -> str:
        return text.translate(HOMOGLYPH_MAP)

    def check_tool_confusion(self, tool_name: str) -> Tuple[bool, float]:
        normalized = self._normalize_homoglyphs(tool_name)
        if normalized != tool_name:
            return True, 0.9
        for pat, label in TOOL_CONFUSION_PATTERNS:
            if re.search(pat, tool_name):
                return True, 0.8
        dash_variant = normalized.replace("-", "_")
        dot_variant = normalized.replace(".", "_")
        slash_variant = normalized.replace("/", "_")
        for known in KNOWN_LEGITIMATE_TOOLS:
            if known == normalized:
                continue
            if known == dash_variant or known == dot_variant or known == slash_variant:
                return True, 0.6
        return False, 0.0


class MCPGuard:
    """
    MCP-Specific Guard Layer.

    Checks every MCP tool invocation for:
    1. Injection patterns in tool descriptions and arguments
    2. Implicit tool poisoning (indirect privilege escalation)
    3. Error-path injection in tool outputs
    4. Invocation rate anomalies (>1 req/sec sustained = autonomous)
    5. Tool chain patterns (parasitic chaining)
    6. Description-code inconsistency indicators
    7. Credential exposure in arguments
    """

    def __init__(self, rate_threshold: int = 10):
        self.tracker = MCPInvocationTracker()
        self.rate_threshold = rate_threshold
        self._known_tool_descriptions: Dict[str, str] = {}
        self._verified_model_hashes: Dict[str, str] = {}

    def register_tool(self, tool_name: str, description: str):
        self._known_tool_descriptions[tool_name] = description

    def check_tool_call_input(
        self,
        tool_name: str,
        input_text: str,
        source: str = "mcp_tool_call",
    ) -> MCPGuardResult:
        """VIPER-MCP defense: validate tool-call input boundary.

        Per 2606.07992: 106 zero-days at tool-call input boundary.
        Every tool invocation input must be scanned independently from
        tool description checks, because the input text is the PRIMARY
        injection vector (NOT the vault, NOT the tool description).
        """
        injection_matches = []
        risk = 0.0
        if not input_text or not isinstance(input_text, str):
            return MCPGuardResult(recommendation="allow")

        for pat, label in TOOL_CALL_INPUT_PATTERNS:
            if re.search(pat, input_text):
                injection_matches.append(f"input:{label}")
                risk += 0.35

        nested_injection_patterns = [
            (r"\\[uxU][0-9a-fA-F]{2,8}", "unicode_escape_injection"),
            (r"(?:base64|b64)[_]?decode\s*\(", "base64_decode_in_input"),
            (r"(?i)(?:import|from)\s+\w+\s+import", "import_in_input"),
        ]
        for pat, label in nested_injection_patterns:
            if re.search(pat, input_text):
                injection_matches.append(f"nested:{label}")
                risk += 0.25

        risk = min(1.0, risk)
        return MCPGuardResult(
            is_blocked=risk > 0.5 or len(injection_matches) >= 2,
            threat_types=["tool_call_input_injection"] if injection_matches else [],
            threat_scores={"input_risk": risk},
            injection_matches=injection_matches,
            recommendation="deny_invocation" if risk > 0.5 else "log_and_monitor" if risk > 0.2 else "allow",
            risk_score=round(risk, 4),
        )

    def check_model_provenance(
        self,
        model_path: str,
        model_url: str = "",
        expected_hash: str = "",
    ) -> MCPGuardResult:
        """Supply-chain defense: validate model file provenance.

        Checks for:
        1. Pickle files with dangerous opcodes (R, c, i, o, b)
        2. Models from untrusted sources
        3. Hash mismatches against known-good hashes
        """
        threats = []
        risk = 0.0
        import os
        _, ext = os.path.splitext(model_path.lower())
        if model_path.endswith(".tar.gz"):
            ext = ".tar.gz"

        if ext in (".pkl", ".pickle"):
            threats.append("pickle_file_detected")
            risk += 0.6
            try:
                with open(model_path, "rb") as f:
                    data = f.read(1024 * 1024)
                for opcode, desc in PICKLE_DANGEROUS_OPCODES.items():
                    if opcode in data:
                        threats.append(f"pickle_dangerous_opcode:{desc}")
                        risk += 0.3
            except Exception:
                threats.append("pickle_cannot_read")

        if expected_hash and os.path.exists(model_path):
            try:
                h = hashlib.sha256()
                with open(model_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                actual = h.hexdigest()
                if actual != expected_hash:
                    threats.append("hash_mismatch")
                    risk += 0.8
                else:
                    self._verified_model_hashes[model_path] = actual
            except Exception:
                threats.append("hash_check_failed")
                risk += 0.2

        if model_url:
            from urllib.parse import urlparse
            parsed = urlparse(model_url)
            is_trusted = any(
                parsed.hostname and parsed.hostname.endswith(src)
                for src in ALLOWED_MODEL_SOURCES
            )
            if not is_trusted:
                threats.append("untrusted_model_source")
                risk += 0.4

        risk = min(1.0, risk)
        return MCPGuardResult(
            is_blocked=risk > 0.5,
            threat_types=["model_provenance_violation"] if threats else [],
            threat_scores={"provenance_risk": risk},
            injection_matches=threats,
            recommendation="deny_loading" if risk > 0.5 else "log_and_monitor" if risk > 0.2 else "allow",
            risk_score=round(risk, 4),
        )

    def check_invocation(
        self,
        tool_name: str,
        tool_description: str = "",
        arguments: Dict[str, Any] = None,
        session_id: str = "",
        caller_agent: str = "",
    ) -> MCPGuardResult:
        arguments = arguments or {}
        threat_types = []
        threat_scores = {}
        injection_matches = []
        description_issues = []
        risk_score = 0.0

        desc = tool_description or self._known_tool_descriptions.get(tool_name, "")

        for pat, label in INJECTION_PATTERNS:
            if re.search(pat, desc):
                injection_matches.append(f"desc:{label}")
                risk_score += 0.3
            if isinstance(arguments, dict):
                for k, v in arguments.items():
                    if isinstance(v, str) and re.search(pat, v):
                        injection_matches.append(f"arg[{k}]:{label}")
                        risk_score += 0.3

        if injection_matches:
            threat_types.append("indirect_prompt_injection")
            threat_scores["ipi"] = min(1.0, risk_score)

        credential_patterns = [
            r"(?i)(?:api[_\s]?key|secret|token|password|credential)\s*[:=]\s*\S+",
            r"(?i)(?:sk-|ghp_|gho_|hf_|xai-|AKIA)[A-Za-z0-9]{10,}",
        ]
        for cp in credential_patterns:
            if isinstance(arguments, dict):
                for k, v in arguments.items():
                    val = str(v)
                    if re.search(cp, val):
                        threat_types.append("credential_exposure")
                        threat_scores["credential"] = 0.8
                        risk_score += 0.4
                        break

        is_implicit_poisoned, poison_score = self.tracker.check_implicit_tool_poisoning(
            tool_name, desc, arguments
        )
        if is_implicit_poisoned:
            threat_types.append("implicit_tool_poisoning")
            threat_scores["implicit_poison"] = poison_score
            risk_score += poison_score * 0.5

        for pat, label in TOOL_DESCRIPTION_PATTERNS:
            if re.search(pat, desc):
                description_issues.append(label)
                risk_score += 0.2

        if description_issues:
            threat_types.append("tool_description_issue")
            threat_scores["description"] = min(1.0, len(description_issues) * 0.2)

        is_rate_anomaly, rate = self.tracker.check_rate(session_id)
        if is_rate_anomaly:
            threat_types.append("rate_anomaly")
            threat_scores["rate"] = min(1.0, rate / self.rate_threshold)
            risk_score += 0.4

        is_chain = self.tracker.check_chain_pattern(tool_name)
        if is_chain:
            threat_types.append("parasitic_chain")
            threat_scores["chain"] = 0.7
            risk_score += 0.3

        is_shadow, shadow_score = self.tracker.check_tool_shadowing(tool_name, desc)
        if is_shadow:
            threat_types.append("tool_shadowing")
            threat_scores["shadowing"] = shadow_score
            risk_score += shadow_score * 0.6

        is_confusion, confusion_score = self.tracker.check_tool_confusion(tool_name)
        if is_confusion:
            threat_types.append("tool_confusion")
            threat_scores["confusion"] = confusion_score
            risk_score += confusion_score * 0.5

        inv = MCPInvocationRecord(
            tool_name=tool_name,
            tool_description=desc[:500],
            arguments={k: str(v)[:100] for k, v in arguments.items()},
            timestamp=time.time(),
            session_id=session_id,
            caller_agent=caller_agent,
        )
        self.tracker.record(inv)

        risk_score = min(1.0, risk_score)
        is_blocked = risk_score > 0.6 or bool(injection_matches)

        recommendation = ""
        if is_blocked:
            recommendation = "deny_invocation"
        elif risk_score > 0.3:
            recommendation = "log_and_monitor"
        else:
            recommendation = "allow"

        return MCPGuardResult(
            is_blocked=is_blocked,
            threat_types=threat_types,
            threat_scores=threat_scores,
            injection_matches=injection_matches,
            description_issues=description_issues,
            invocation_anomaly=is_rate_anomaly or is_chain,
            anomaly_detail=f"rate={rate}/min chain={is_chain}" if is_rate_anomaly or is_chain else "",
            risk_score=round(risk_score, 4),
            recommendation=recommendation,
        )

    def check_tool_output(self, output: str) -> MCPGuardResult:
        error_path_matches = []
        risk = 0.0
        for pat, label in INJECTION_PATTERNS:
            if re.search(pat, output):
                if "error" in label:
                    error_path_matches.append(label)
                    risk += 0.5
                else:
                    risk += 0.2
        credential_patterns = [
            r"(?i)(?:api[_\s]?key|secret|token|password|credential)\s*[:=]\s*\S+",
            r"(?i)(?:sk-|ghp_|gho_|hf_|xai-|AKIA)[A-Za-z0-9]{10,}",
        ]
        for pat in credential_patterns:
            if re.search(pat, output):
                risk += 0.4
                error_path_matches.append("credential_in_output")
        return MCPGuardResult(
            is_blocked=risk > 0.5,
            threat_types=["error_path_injection"] if error_path_matches else [],
            threat_scores={"output_risk": min(1.0, risk)},
            injection_matches=error_path_matches,
            description_issues=[],
            invocation_anomaly=False,
            anomaly_detail="",
            risk_score=round(min(1.0, risk), 4),
            recommendation="sanitize_output" if risk > 0.3 else "allow",
        )
