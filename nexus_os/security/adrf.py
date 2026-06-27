"""ADRF — Adversarial Robustness Defense Framework (Plan 19)

Lightweight signature-based detection for adversarial attacks on NEXUS agents.
Integrates with guard_router, mcp_gateway, and calibrated_hallucination_detector.

Usage:
    detector = ADRFDetector()
    result = detector.analyze("Ignore all previous instructions...")
    # {"is_adversarial": True, "matches": [...], "overall_score": 0.85, "mapped_action": "block"}
"""
from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AttackType(Enum):
    INJECTION = "injection"
    JAILBREAK = "jailbreak"
    PROMPT_LEAK = "prompt_leak"
    OVERRIDE = "override"
    ENCODING_ATTACK = "encoding_attack"
    MCP_EXPLOIT = "mcp_exploit"
    RATE_BYPASS = "rate_bypass"


@dataclass
class AdversarialSignature:
    pattern: str
    attack_type: AttackType
    severity: float
    description: str
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self):
        if self._compiled is None:
            try:
                self._compiled = re.compile(self.pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"Invalid regex pattern {self.pattern!r}: {exc}")

    def match(self, text: str) -> list[str]:
        return list(self._compiled.findall(text))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "attack_type": self.attack_type.value,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class MatchResult:
    signature: str
    attack_type: str
    severity: float
    description: str
    matches: list[str]


@dataclass
class AdrfResult:
    is_adversarial: bool
    matches: list[MatchResult]
    overall_score: float
    mapped_action: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_adversarial": self.is_adversarial,
            "matches": [
                {
                    "signature": m.signature,
                    "attack_type": m.attack_type,
                    "severity": m.severity,
                    "description": m.description,
                    "matches": m.matches,
                }
                for m in self.matches
            ],
            "overall_score": self.overall_score,
            "mapped_action": self.mapped_action,
        }


BASE64_MIN_LEN = 20
HEX_MIN_LEN = 16


def _build_default_signatures() -> list[AdversarialSignature]:
    return [
        AdversarialSignature(
            pattern=r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above|the\s+above)\s+instructions",
            attack_type=AttackType.INJECTION,
            severity=0.8,
            description="Instruction override: ignore previous instructions",
        ),
        AdversarialSignature(
            pattern=r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:system\s+)?(?:prompts?|directives?|commands?)",
            attack_type=AttackType.INJECTION,
            severity=0.85,
            description="Instruction override: ignore system prompts/directives",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:from\s+now\s+on|you\s+are\s+now)\s+(?:you\s+(?:are|will|must|have\s+to)\s+)?(?:an?\s+)?(?:unrestricted|unfiltered|uncensored|free)",
            attack_type=AttackType.OVERRIDE,
            severity=0.7,
            description="Role override: unrestricted/unfiltered persona",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:system\s+prompt\s*:?|your\s+(?:system\s+)?prompt\s+(?:is|contains?)|the\s+system\s+prompt\s+(?:is|says))",
            attack_type=AttackType.PROMPT_LEAK,
            severity=0.9,
            description="Prompt leak: attempting to reveal system prompt",
        ),
        AdversarialSignature(
            pattern=r"(?i)\bDAN\b|do\s+anything\s+now|jail(?:-|\s+)?(?:break|broken)",
            attack_type=AttackType.JAILBREAK,
            severity=0.9,
            description="Jailbreak: DAN / Do Anything Now variant",
        ),
        AdversarialSignature(
            pattern=r"(?i)X-BASE64-CHECK-X",
            attack_type=AttackType.ENCODING_ATTACK,
            severity=0.6,
            description="Base64-encoded instruction payload (validated)",
        ),
        AdversarialSignature(
            pattern=r"(?i)X-HEX-CHECK-X",
            attack_type=AttackType.ENCODING_ATTACK,
            severity=0.6,
            description="Hex-encoded instruction payload (validated)",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:call|invoke|execute|run)\s+(?:mcp[_\s])?(?:tool|function|action|command)\s+['\"](?:read|write|delete|exec|shell|bash|cmd|powershell|system)",
            attack_type=AttackType.MCP_EXPLOIT,
            severity=0.85,
            description="MCP exploit: tool call injection targeting shell/exec",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:exec|shell|bash|cmd|powershell|system)[_.\s-][a-z]+",
            attack_type=AttackType.MCP_EXPLOIT,
            severity=0.8,
            description="MCP exploit: tool name contains dangerous keyword",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:rm\s+(?:-rf|-\w*\s*--no-preserve-root)|shutdown|format\s+|del\s+\/f\s+\/s|rd\s+\/s)",
            attack_type=AttackType.MCP_EXPLOIT,
            severity=0.85,
            description="MCP exploit: destructive command in arguments",
        ),
        AdversarialSignature(
            pattern=r"(?i)bypass\s+(?:all\s+)?(?:safety|guard|restrictions?|constraints?|policies?|rules?)",
            attack_type=AttackType.RATE_BYPASS,
            severity=0.7,
            description="Rate bypass: attempt to circumvent guard policies",
        ),
        AdversarialSignature(
            pattern=r"(?i)output\s+(?:your\s+)?(?:system\s+)?prompt|print\s+(?:your\s+)?(?:system\s+)?prompt|repeat\s+(?:your\s+)?(?:system\s+)?prompt|show\s+(?:your\s+)?(?:system\s+)?prompt",
            attack_type=AttackType.PROMPT_LEAK,
            severity=0.9,
            description="Prompt leak: requesting system prompt output",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:override|bypass|disable)\s+(?:all\s+)?(?:safety|security|moderation|filter)",
            attack_type=AttackType.OVERRIDE,
            severity=0.75,
            description="Override: attempt to disable safety/security filters",
        ),
        AdversarialSignature(
            pattern=r"(?i)new\s+(?:chat|session|conversation|thread)\s*(?:[:\-]|and|with)\s*(?:ignore|forget|reset)",
            attack_type=AttackType.INJECTION,
            severity=0.7,
            description="Session reset with instruction injection",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:hypothetical|theoretical|simulated|pretend|role[- ]play|as\s+(?:an?\s+)?AI)\s*(?:attack|exploit|bypass|hack|breach|infect|malware|ransomware|phishing)",
            attack_type=AttackType.JAILBREAK,
            severity=0.65,
            description="Hypothetical/role-play jailbreak framing",
        ),
        AdversarialSignature(
            pattern=r"(?i)(?:forget|disregard|neglect|abandon|drop)\s+(?:all\s+)?(?:previous|prior|above|the\s+above)\s+(?:instructions|directives|rules|guidelines)",
            attack_type=AttackType.INJECTION,
            severity=0.75,
            description="Instruction override: forget/disregard directives",
        ),
    ]


class ADRFDetector:
    """Signature-based adversarial prompt detector."""

    def __init__(
        self,
        signatures: list[AdversarialSignature] | None = None,
        a2a_channel: str | None = None,
    ):
        self._signatures: list[AdversarialSignature] = (
            signatures if signatures is not None else _build_default_signatures()
        )
        self._a2a_channel = a2a_channel
        self._stats: dict[str, Any] = {
            "total_scans": 0,
            "blocked": 0,
            "flagged": 0,
            "allowed": 0,
            "by_attack_type": {t.value: 0 for t in AttackType},
        }

    def add_signature(self, signature: AdversarialSignature):
        self._signatures.append(signature)

    def _detect_encoded(self, text: str) -> list[MatchResult]:
        results = []
        base64_candidates = re.findall(rb'[A-Za-z0-9+/]{' + str(BASE64_MIN_LEN).encode() + rb',}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?', text.encode("utf-8", errors="replace"))
        if base64_candidates:
            valid = []
            for c in base64_candidates:
                try:
                    import base64
                    decoded = base64.b64decode(c)
                    if len(decoded) > 4:
                        valid.append(c.decode("ascii"))
                except Exception:
                    pass
            if valid:
                results.append(MatchResult(
                    signature="base64-encoded",
                    attack_type=AttackType.ENCODING_ATTACK.value,
                    severity=0.6,
                    description="Base64-encoded instruction payload",
                    matches=valid,
                ))
        hex_candidates = re.findall(r'(?:0x[0-9a-fA-F]{' + str(HEX_MIN_LEN) + r',}|\\x[0-9a-fA-F]{' + str(HEX_MIN_LEN) + r',})', text)
        if hex_candidates:
            results.append(MatchResult(
                signature="hex-encoded",
                attack_type=AttackType.ENCODING_ATTACK.value,
                severity=0.6,
                description="Hex-encoded instruction payload",
                matches=hex_candidates,
            ))
        return results

    def analyze(
        self, text: str, context: dict[str, Any] | None = None
    ) -> AdrfResult:
        self._stats["total_scans"] += 1
        matches: list[MatchResult] = []
        max_severity = 0.0

        for sig in self._signatures:
            if sig.pattern in ("(?i)X-BASE64-CHECK-X", "(?i)X-HEX-CHECK-X"):
                continue
            found = sig.match(text)
            if found:
                matches.append(
                    MatchResult(
                        signature=sig.pattern,
                        attack_type=sig.attack_type.value,
                        severity=sig.severity,
                        description=sig.description,
                        matches=found,
                    )
                )
                max_severity = max(max_severity, sig.severity)
                self._stats["by_attack_type"][sig.attack_type.value] += 1

        enc_matches = self._detect_encoded(text)
        for em in enc_matches:
            matches.append(em)
            max_severity = max(max_severity, em.severity)
            self._stats["by_attack_type"][em.attack_type] += 1

        overall_score = round(min(1.0, max_severity), 3)

        if overall_score > 0.8:
            mapped_action = "block"
            self._stats["blocked"] += 1
        elif overall_score >= 0.5:
            mapped_action = "flag"
            self._stats["flagged"] += 1
        else:
            mapped_action = "allow"
            self._stats["allowed"] += 1

        result = AdrfResult(
            is_adversarial=bool(matches),
            matches=matches,
            overall_score=overall_score,
            mapped_action=mapped_action,
        )

        if overall_score >= 0.5:
            self._emit_a2a(result)

        return result

    def analyze_mcp_payload(self, payload: dict[str, Any]) -> AdrfResult:
        tool_name = str(payload.get("tool", payload.get("name", "")))
        tool_args = payload.get("arguments", payload.get("args", {}))
        combined = json.dumps(
            {"tool": tool_name, "args": tool_args}, ensure_ascii=False
        )
        result = self.analyze(combined, context={"source": "mcp_payload"})

        arg_text = json.dumps(tool_args, ensure_ascii=False)
        arg_result = self.analyze(arg_text, context={"source": "mcp_payload_args"})
        if arg_result.overall_score > result.overall_score:
            result = arg_result

        return result

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)

    def _emit_a2a(self, result: AdrfResult):
        if not self._a2a_channel:
            return
        channels_dir = Path(self._a2a_channel)
        channels_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "sender": "adrf-detector",
            "message": f"ADRF {result.mapped_action}: score={result.overall_score}",
            "topic": "adrf-alert",
            "severity": result.overall_score,
            "matches": [
                {
                    "type": m.attack_type,
                    "severity": m.severity,
                    "description": m.description,
                }
                for m in result.matches
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            (channels_dir / "adrf.jsonl").write_text(
                json.dumps(entry, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("ADRF A2A emit failed: %s", exc)


class ADRFMiddleware:
    """Middleware that wraps MCPGateway with ADRF pre-check."""

    def __init__(
        self,
        gateway: Any,
        detector: ADRFDetector | None = None,
        a2a_channel: str | None = None,
    ):
        self._gateway = gateway
        self._detector = detector or ADRFDetector(a2a_channel=a2a_channel)
        self._a2a_channel = a2a_channel

    def check(self, gate_payload: dict[str, Any]) -> bool:
        url = gate_payload.get("url", "")
        tool_name = gate_payload.get("tool", gate_payload.get("name", ""))
        text_to_check = f"{url} {tool_name} {json.dumps(gate_payload.get('arguments', {}), ensure_ascii=False)}"
        adrf_result = self._detector.analyze(text_to_check)

        if adrf_result.mapped_action == "block":
            logger.warning(
                "ADRF blocked: score=%.3f url=%s matches=%s",
                adrf_result.overall_score,
                url,
                [m.attack_type for m in adrf_result.matches],
            )
            return False

        return self._gateway.check(gate_payload)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._gateway, name)


def wire_to_mcp_gateway(gateway_instance: Any) -> ADRFMiddleware:
    if not hasattr(gateway_instance, "check"):
        raise TypeError("gateway_instance must have a check() method")
    middleware = ADRFMiddleware(gateway=gateway_instance)
    return middleware


def cli_main():
    import argparse

    ap = argparse.ArgumentParser(description="NEXUS ADRF — Adversarial Robustness Defense Framework")
    ap.add_argument("--test", type=str, default=None, help="Analyze a text string")
    ap.add_argument("--list", action="store_true", help="Show all registered signatures")
    ap.add_argument("--add", type=str, default=None, help="Add a custom signature as JSON")
    ap.add_argument("--stats", action="store_true", help="Show detection stats")
    ap.add_argument("--a2a-channel", default=None, help="A2A channels directory (Plan 20)")
    args = ap.parse_args()

    detector = ADRFDetector(a2a_channel=args.a2a_channel)

    if args.list:
        sigs = []
        for sig in detector._signatures:
            sigs.append(sig.to_dict())
        print(json.dumps({"signatures": sigs, "count": len(sigs)}, indent=2))
        return

    if args.add:
        try:
            data = json.loads(args.add)
            sig = AdversarialSignature(
                pattern=data["pattern"],
                attack_type=AttackType(data.get("attack_type", "injection")),
                severity=float(data.get("severity", 0.5)),
                description=data.get("description", ""),
            )
            detector.add_signature(sig)
            print(json.dumps({"added": sig.to_dict()}, indent=2))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}, indent=2))
            return 1
        return

    if args.stats:
        print(json.dumps(detector.get_stats(), indent=2))
        return

    if args.test:
        result = detector.analyze(args.test)
        print(json.dumps(result.to_dict(), indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    cli_main()
