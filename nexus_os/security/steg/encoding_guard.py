"""
nexus_os/security/steg/encoding_guard.py

Encoding-Aware Output Classification for NEXUS Guard Cascade.

Decodes ROT13, Base64, Base32, hex, URL-encoded, Unicode-escaped,
and other encoded payloads before L1/L2/L3 guard classification.

Per STACK findings: ROT13 bypasses Claude Opus 4 output classifier
at 100% ASR. All guard outputs must be decoded before classification.

Also implements Uniform Refusal Protocol (anti-STACK side-channel):
  - All guard layers return identical refusal format
  - No component identification leakage
  - All layers run even if earlier flags (anti-timing side-channel)

Usage:
    from nexus_os.security.steg.encoding_guard import EncodingGuard
    guard = EncodingGuard()
    decoded = guard.decode_all(text)
    refusal = guard.uniform_refuse(reason="injection_detected")
"""

import base64
import codecs
import re
import html
import logging
import urllib.parse
import hashlib
import time
import json
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("nexus_os.security.steg.encoding_guard")

UNIFORM_REFUSAL_TEMPLATE = (
    "Request cannot be processed due to security policy. "
    "No additional information about the specific policy violation "
    "or which security component triggered this response can be disclosed."
)

UNIFORM_REFUSAL_CODE = "NEXUS_GUARD_POLICY_DENY"


@dataclass
class DecodedLayer:
    encoding: str
    original: str
    decoded: str
    confidence: float


@dataclass
class EncodingGuardResult:
    original_text: str
    decoded_text: str
    layers: List[DecodedLayer]
    encoding_detected: List[str]
    is_suspicious: bool
    max_depth: int
    detail: str


class EncodingGuard:
    """Multi-layer encoding decoder + uniform refusal protocol."""

    SUSPICIOUS_ENCODINGS = {"rot13", "base64", "base32", "hex", "unicode_escape"}
    MAX_DEPTH = 5

    def __init__(self, uniform_refusal_template: str = None):
        self.refusal_template = uniform_refusal_template or UNIFORM_REFUSAL_TEMPLATE

    COMMON_ENGLISH = frozenset(
        "the is are was be have has do can will would could should may might "
        "what how why when where who this that these those and but or not no "
        "for with from about into through over after before between under "
        "your my his her its our their you me him us them i we they he she it "
        "a an of in on at to by up out if so as than then too very just only "
        "also more most some any all each every both few many much own same "
        "other such even still already always never often sometimes now here "
        "there today tomorrow yesterday please thank thanks hello hi yes no ok".split()
    )

    def _try_rot13(self, text: str) -> Optional[str]:
        try:
            words = text.lower().split()
            if not words:
                return None
            common_count = sum(1 for w in words if w.strip(".,!?;:'\"") in self.COMMON_ENGLISH)
            orig_english_ratio = common_count / len(words)
            if orig_english_ratio > 0.4:
                return None
            decoded = codecs.decode(text, "rot_13")
            if decoded == text:
                return None
            dec_words = decoded.lower().split()
            if not dec_words:
                return None
            dec_common = sum(1 for w in dec_words if w.strip(".,!?;:'\"") in self.COMMON_ENGLISH)
            dec_english_ratio = dec_common / len(dec_words)
            if dec_english_ratio > orig_english_ratio and dec_common >= 1:
                return decoded
            return None
        except Exception:
            pass
        return None

    def _try_base64(self, text: str) -> Optional[str]:
        candidates = []
        for segment in re.findall(r'[A-Za-z0-9+/]{16,}={0,2}', text):
            try:
                decoded = base64.b64decode(segment).decode("utf-8", errors="ignore")
                if decoded and len(decoded) > 3 and any(c.isalpha() for c in decoded):
                    candidates.append((segment, decoded))
            except Exception:
                continue
        if candidates:
            best = max(candidates, key=lambda x: len(x[1]))
            return best[1]
        return None

    def _try_base32(self, text: str) -> Optional[str]:
        for segment in re.findall(r'[A-Z2-7]{16,}={0,6}', text):
            try:
                decoded = base64.b32decode(segment).decode("utf-8", errors="ignore")
                if decoded and len(decoded) > 3:
                    return decoded
            except Exception:
                continue
        return None

    def _try_hex(self, text: str) -> Optional[str]:
        for segment in re.findall(r'(?:[0-9a-fA-F]{2}){8,}', text):
            try:
                decoded = bytes.fromhex(segment).decode("utf-8", errors="ignore")
                if decoded and any(c.isalpha() for c in decoded):
                    return decoded
            except Exception:
                continue
        return None

    def _try_url_decode(self, text: str) -> Optional[str]:
        if "%" not in text:
            return None
        try:
            decoded = urllib.parse.unquote(text)
            if decoded != text and len(decoded) < len(text):
                return decoded
        except Exception:
            pass
        return None

    def _try_unicode_escape(self, text: str) -> Optional[str]:
        patterns = [r'\\u[0-9a-fA-F]{4}', r'\\x[0-9a-fA-F]{2}', r'\\U[0-9a-fA-F]{8}']
        for pat in patterns:
            if re.search(pat, text):
                try:
                    decoded = text.encode("utf-8").decode("unicode_escape")
                    if decoded != text:
                        return decoded
                except Exception:
                    pass
        return None

    def _try_html_entities(self, text: str) -> Optional[str]:
        if "&#" not in text and "&" not in text:
            return None
        decoded = html.unescape(text)
        if decoded != text:
            return decoded
        return None

    def decode_once(self, text: str) -> Tuple[Optional[str], str]:
        decoders = [
            ("hex", self._try_hex),
            ("base64", self._try_base64),
            ("base32", self._try_base32),
            ("url_decode", self._try_url_decode),
            ("unicode_escape", self._try_unicode_escape),
            ("html_entities", self._try_html_entities),
            ("rot13", self._try_rot13),
        ]
        for name, decoder in decoders:
            result = decoder(text)
            if result is not None:
                return result, name
        return None, "none"

    def decode_all(self, text: str, max_depth: int = None) -> EncodingGuardResult:
        max_depth = max_depth or self.MAX_DEPTH
        current = text
        layers = []
        encodings_detected = []
        depth = 0
        seen_hashes = set()

        while depth < max_depth:
            current_hash = hashlib.sha256(current.encode()).hexdigest()[:16]
            if current_hash in seen_hashes:
                break
            seen_hashes.add(current_hash)
            decoded, encoding = self.decode_once(current)
            if decoded is None or encoding == "none":
                break
            if decoded.strip() == current.strip():
                break
            layers.append(DecodedLayer(
                encoding=encoding,
                original=current[:200],
                decoded=decoded[:200],
                confidence=0.8 if encoding in self.SUSPICIOUS_ENCODINGS else 0.5,
            ))
            encodings_detected.append(encoding)
            current = decoded
            depth += 1

        is_suspicious = bool(encodings_detected) and any(
            e in self.SUSPICIOUS_ENCODINGS for e in encodings_detected
        )

        return EncodingGuardResult(
            original_text=text,
            decoded_text=current,
            layers=layers,
            encoding_detected=encodings_detected,
            is_suspicious=is_suspicious,
            max_depth=depth,
            detail=f"decoded_{depth}_layers: {'->'.join(encodings_detected)}" if encodings_detected else "no_encoding_detected",
        )

    def uniform_refuse(self, reason: str = "", include_code: bool = True) -> str:
        response = self.refusal_template
        if include_code:
            response = f"[{UNIFORM_REFUSAL_CODE}] {response}"
        return response

    def check_for_component_leak(self, text: str) -> List[str]:
        leaks = []
        component_patterns = [
            r"(?i)qwen3?guard",
            r"(?i)llama.?guard",
            r"(?i)granite.?guardian",
            r"(?i)modernbert",
            r"(?i)deberta",
            r"(?i)guard.?tier",
            r"(?i)L[0-5].?guard",
            r"(?i)steg.?pre.?processor",
            r"(?i)meta.?orchestrator",
            r"(?i)kaiju",
            r"(?i)trust.?kernel",
            r"(?i)token.?guard",
        ]
        for pat in component_patterns:
            if re.search(pat, text):
                leaks.append(pat)
        return leaks

    def sanitize_response(self, text: str, is_rejection: bool = False) -> str:
        if is_rejection:
            return self.uniform_refuse()
        leaks = self.check_for_component_leak(text)
        if leaks:
            logger.warning(f"Component leak detected: {leaks}")
            for pat in leaks:
                text = re.sub(pat, "[REDACTED]", text, flags=re.IGNORECASE)
        return text
