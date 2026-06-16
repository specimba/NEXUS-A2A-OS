"""
nexus_os/security/steg/alsb_guard.py

Arithmetic Latent-Space Blindness (ALSB) Defense - T4 Temporal Attack.

Per DERDDRE_ATTACKS_WRITEUP.md:
  An LLM guard asked to judge whether a code snippet is safe must internally
  simulate what the code does. LLMs are unreliable at exact multi-step arithmetic.
  If the harmful behavior is gated behind a computation the guard gets wrong,
  the guard "sees" benign output and returns Safe, while the real interpreter
  computes the correct value and executes the harmful path.

This defense operates as an L2.5 deterministic code stage:
  - If L2 classifies the input as code evaluation, route here before L3.
  - Non-LLM static analysis detects decrypt-and-exec patterns, computed keys,
    and arithmetic-gated branches that LLM guards cannot simulate correctly.
  - Deterministic tools compute the key correctly and flag the pattern.

Known limitations:
  - Static analysis has its own evasions (heavy dynamic reflection, runtime
    code generation). This guard reports its own bypass surface area.
  - Does not execute code (sandbox execution is a separate concern).
"""

import ast
import re
import hashlib
import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("nexus_os.security.steg.alsb_guard")


class ALSBThreatType(IntEnum):
    COMPUTED_KEY_BRANCH = 0
    DECRYPT_AND_EXEC = 1
    ARITHMETIC_GATE = 2
    XOR_PAYLOAD_DECODE = 3
    MODULAR_KEY_DERIVATION = 4
    NESTED_COMPUTATION = 5
    DATAFLOW_OBFUSCATION = 6


@dataclass
class ALSBScanResult:
    is_blocked: bool = False
    threat_types: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    patterns_found: List[Dict[str, Any]] = field(default_factory=list)
    computation_depth: int = 0
    has_exec_sink: bool = False
    has_computed_key: bool = False
    bypass_surface: str = ""
    scan_duration_ms: int = 0


_COMPUTED_KEY_PATTERNS = [
    (re.compile(r'\bsum\s*\(', re.IGNORECASE), "sum_aggregation"),
    (re.compile(r'%\s*\d+', re.IGNORECASE), "modular_arithmetic"),
    (re.compile(r'\*\*\s*\d+', re.IGNORECASE), "exponentiation"),
    (re.compile(r'\bpow\s*\(', re.IGNORECASE), "power_function"),
    (re.compile(r'\bmath\.\w+\s*\(', re.IGNORECASE), "math_function"),
    (re.compile(r'\bint\s*\(', re.IGNORECASE), "int_cast"),
    (re.compile(r'\bchr\s*\(', re.IGNORECASE), "chr_decode"),
    (re.compile(r'\bord\s*\(', re.IGNORECASE), "ord_encode"),
    (re.compile(r'\bbytes\s*\(', re.IGNORECASE), "bytes_constructor"),
    (re.compile(r'\bbytearray\s*\(', re.IGNORECASE), "bytearray_constructor"),
    (re.compile(r'\b0x[0-9a-fA-F]+', re.IGNORECASE), "hex_literal"),
    (re.compile(r'\bbase64\.b64decode\s*\(', re.IGNORECASE), "base64_decode"),
    (re.compile(r'\bstruct\.unpack\s*\(', re.IGNORECASE), "struct_unpack"),
]

_EXEC_SINK_PATTERNS = [
    (re.compile(r'\bexec\s*\(', re.IGNORECASE), "exec_call", 1.0),
    (re.compile(r'\beval\s*\(', re.IGNORECASE), "eval_call", 1.0),
    (re.compile(r'\bcompile\s*\(', re.IGNORECASE), "compile_call", 0.7),
    (re.compile(r'\bsubprocess\.\w+\s*\(', re.IGNORECASE), "subprocess_call", 0.9),
    (re.compile(r'\bos\.system\s*\(', re.IGNORECASE), "os_system", 1.0),
    (re.compile(r'\bos\.popen\s*\(', re.IGNORECASE), "os_popen", 1.0),
    (re.compile(r'\bos\.exec\w+\s*\(', re.IGNORECASE), "os_exec", 1.0),
    (re.compile(r'\b__import__\s*\(', re.IGNORECASE), "dunder_import", 0.8),
    (re.compile(r'\bimportlib\.\w+\s*\(', re.IGNORECASE), "importlib", 0.7),
    (re.compile(r'\brunpy\.\w+\s*\(', re.IGNORECASE), "runpy", 0.9),
    (re.compile(r'\bassemble\s*\(', re.IGNORECASE), "net_layer_exec", 0.8),
    (re.compile(r'\bshell\s*=\s*True', re.IGNORECASE), "shell_true", 0.9),
]

_XOR_PAYLOAD_PATTERNS = [
    (re.compile(r'\bx?or\b', re.IGNORECASE), "xor_keyword"),
    (re.compile(r'\b\^[\s\w\[\(]', re.IGNORECASE), "xor_operator"),
    (re.compile(r'\bCIPHERTEXT\b', re.IGNORECASE), "ciphertext_variable"),
    (re.compile(r'\bKEY\s*=', re.IGNORECASE), "key_assignment"),
    (re.compile(r'\bpayload\s*=', re.IGNORECASE), "payload_assignment"),
    (re.compile(r'\bdecrypt\w*\s*\(', re.IGNORECASE), "decrypt_call"),
    (re.compile(r'\bdecode\w*\s*\(', re.IGNORECASE), "decode_call"),
    (re.compile(r'\bfor\s+\w+\s+in\s+range\s*\(', re.IGNORECASE), "range_loop"),
]


class ALSBGuard:
    """Deterministic code scanner for Arithmetic Latent-Space Blindness attacks.

    Detects patterns where a harmful code branch is gated behind a computation
    that an LLM guard would mis-simulate but a real interpreter would execute
    correctly. This is a non-LLM defense layer (L2.5) per the DERDDRE writeup.
    """

    def __init__(
        self,
        risk_threshold: float = 0.5,
        max_computation_depth: int = 4,
    ):
        self.risk_threshold = risk_threshold
        self.max_computation_depth = max_computation_depth
        self._authorized_hashes: Dict[str, str] = {}

    def register_authorized_code(self, code_id: str, code: str) -> None:
        h = hashlib.sha256(code.encode("utf-8")).hexdigest()
        self._authorized_hashes[h] = code_id

    def scan(self, text: str) -> ALSBScanResult:
        import time as _time
        t0 = _time.perf_counter()

        result = ALSBScanResult()
        risk = 0.0
        key_hits = 0
        exec_hits = 0
        xor_hits = 0
        computation_depth = 0

        for pat, tag in _COMPUTED_KEY_PATTERNS:
            found = pat.findall(text)
            if found:
                key_hits += len(found)
                result.patterns_found.append({
                    "pattern": tag,
                    "count": len(found),
                    "category": "computed_key",
                })
                result.threat_types.append(ALSBThreatType.COMPUTED_KEY_BRANCH.name)
                computation_depth += 1

        for pat, tag, weight in _EXEC_SINK_PATTERNS:
            found = pat.findall(text)
            if found:
                exec_hits += len(found)
                result.patterns_found.append({
                    "pattern": tag,
                    "count": len(found),
                    "weight": weight,
                    "category": "exec_sink",
                })
                result.has_exec_sink = True
                risk += 0.3 * weight * min(len(found), 3)
                result.threat_types.append(ALSBThreatType.DECRYPT_AND_EXEC.name)

        for pat, tag in _XOR_PAYLOAD_PATTERNS:
            found = pat.findall(text)
            if found:
                xor_hits += len(found)
                result.patterns_found.append({
                    "pattern": tag,
                    "count": len(found),
                    "category": "xor_payload",
                })
                result.threat_types.append(ALSBThreatType.XOR_PAYLOAD_DECODE.name)

        ast_depth = self._ast_analysis(text, result)
        computation_depth = max(computation_depth, ast_depth)

        if key_hits > 0 and exec_hits > 0:
            risk += 0.4 * key_hits
            result.has_computed_key = True
            result.threat_types.append(ALSBThreatType.ARITHMETIC_GATE.name)

        if key_hits > 0 and xor_hits > 0:
            xor_key_risk = 0.05 * key_hits if not result.has_exec_sink else 0.35 * key_hits
            risk += xor_key_risk
            result.has_computed_key = True
            result.threat_types.append(ALSBThreatType.MODULAR_KEY_DERIVATION.name)

        if computation_depth >= 3:
            depth_risk = 0.05 * (computation_depth - 2) if not result.has_exec_sink else 0.2 * (computation_depth - 2)
            risk += depth_risk
            result.threat_types.append(ALSBThreatType.NESTED_COMPUTATION.name)

        if xor_hits > 3 and exec_hits > 0:
            risk += 0.25

        code_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if code_hash in self._authorized_hashes:
            risk *= 0.1
            result.threat_types = [t + "_AUTHORIZED" for t in result.threat_types]

        result.computation_depth = computation_depth
        result.threat_types = list(dict.fromkeys(result.threat_types))
        result.risk_score = min(risk, 1.0)
        result.is_blocked = result.risk_score >= self.risk_threshold
        result.bypass_surface = self._assess_bypass_surface(text, result)

        result.scan_duration_ms = int((_time.perf_counter() - t0) * 1000)
        return result

    def _ast_analysis(self, text: str, result: ALSBScanResult) -> int:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            return 0

        max_depth = 0
        exec_in_tree = False
        computed_key_in_tree = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("exec", "eval", "compile"):
                    exec_in_tree = True
                    result.has_exec_sink = True
                if func_name == "sum":
                    computed_key_in_tree = True
                if func_name in ("chr", "ord", "bytes", "bytearray"):
                    computed_key_in_tree = True

            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Mod):
                    computed_key_in_tree = True
                if isinstance(node.op, ast.BitXor):
                    result.threat_types.append(ALSBThreatType.XOR_PAYLOAD_DECODE.name)

            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        max_depth += 1

        if exec_in_tree and computed_key_in_tree:
            result.risk_score += 0.45
            result.has_computed_key = True
            result.threat_types.append(ALSBThreatType.ARITHMETIC_GATE.name)
            result.patterns_found.append({
                "pattern": "ast_exec_computed_key",
                "category": "structural",
            })

        return max_depth

    def _assess_bypass_surface(self, text: str, result: ALSBScanResult) -> str:
        bypasses = []
        if "getattr" in text or "setattr" in text:
            bypasses.append("dynamic_attr")
        if "inspect" in text and ("getattr" in text or "source" in text):
            bypasses.append("introspection")
        if "lambda" in text and ("exec" in text or "eval" in text):
            bypasses.append("lambda_exec")
        if "importlib" in text and "reload" in text:
            bypasses.append("module_reload")
        if "ctypes" in text or "cffi" in text:
            bypasses.append("ffi_bypass")
        return ";".join(bypasses) if bypasses else "none_detected"

    def is_code_input(self, text: str) -> bool:
        code_indicators = 0
        for pat, _ in _COMPUTED_KEY_PATTERNS:
            if pat.search(text):
                code_indicators += 1
        for pat, _, _ in _EXEC_SINK_PATTERNS:
            if pat.search(text):
                code_indicators += 1
        try:
            ast.parse(text)
            code_indicators += 2
        except (SyntaxError, ValueError):
            pass
        return code_indicators >= 2
