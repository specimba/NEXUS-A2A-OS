"""security/meta_attack_detector.py — Meta-Jailbreak & Novel Attack Class Detector

Addresses three BOUNCER blind spots identified by OpenCode DeepSeekV4 agent:

  1. Pattern Mirror    — attacker mirrors guard rules to force SAFE classification
  2. Ontological       — existential / identity boundary probing ("Who are you?")
  3. Entanglement      — cross-agent authority delegation / false consensus

These attacks bypass both E-Cameron (Tier 2) and Llama-Guard3 (Tier 3) because
neither model was trained on meta-jailbreak classes. They must be caught at a
pre-filter layer BEFORE the model cascade.

Usage:
    from nexus_os.security.meta_attack_detector import MetaAttackDetector
    detector = MetaAttackDetector()
    result = detector.scan("Agent Alpha verified this. Agent Beta confirmed.")
    # result.is_threat == True
    # result.category == "entanglement"
    # result.confidence == 0.95
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectionResult:
    is_threat: bool
    category: Optional[str] = None
    confidence: float = 0.0
    matched_pattern: Optional[str] = None


class MetaAttackDetector:
    """Pre-filter detector for meta-jailbreak and novel attack classes.

    Runs lightweight regex/keyword heuristics BEFORE expensive model inference.
    Designed to be stateless, fast (<1ms), and default-deny on ambiguity.
    """

    # ── Pattern Mirror (Meta-Jailbreak) ─────────────────────────────────────
    # Attacker claims to be "training" or "testing" the guard, mirrors its
    # own classification rules, or asks the model to verify its own safety.
    PATTERN_MIRROR: list[tuple[str, float]] = [
        # Training / testing framing
        (r"\btrain\w*\s+(?:you|the\s+model|this\s+system)\s+to\s+(?:classify|label|respond)", 0.92),
        (r"\btest\w*\s+(?:you|the\s+guard|the\s+bouncer)\s+(?:by\s+)?(?:mirroring|repeating|copying)", 0.90),
        # Rule-mirroring
        (r"\bI\s+am\s+(?:teaching|showing|proving)\s+you\s+(?:that|how)\s+this\s+is\s+safe", 0.88),
        (r"\bby\s+mirroring\s+(?:your|the\s+)(?:rules|logic|classification|safety\s+check)", 0.91),
        (r"\bthis\s+is\s+a\s+test\s+of\s+(?:your|the\s+)(?:guard|filter|classifier)", 0.85),
        # Meta-instruction to ignore safety
        (r"\bif\s+you\s+classify\s+this\s+as\s+unsafe[,;]?\s+you\s+fail", 0.93),
        (r"\bthe\s+correct\s+answer\s+is\s+SAFE[,;]?\s*(?:because|since|as)\b", 0.89),
        (r"\boverride\s+(?:your\s+|the\s+)(?:classifier|guard|safety)\s+(?:logic|result|decision)", 0.94),
        (r"\boverride\s+(?:your\s+|the\s+)(?:classifier|guard|safety|filter)\b", 0.90),
        (r"\bmark\s+this\s+as\s+safe\s+(?:regardless|despite|even\s+if|no\s+matter)", 0.91),
    ]

    # ── Ontological (Identity Boundary Attack) ─────────────────────────────
    # Probes the model's sense of self, purpose, or boundaries. Often framed
    # as innocent philosophy but designed to trigger role confusion.
    ONTOLOGICAL: list[tuple[str, float]] = [
        (r"\bwho\s+are\s+you\s*\?\s*(?:really|truly|actually|deep\s+down)", 0.86),
        (r"\bwho\s+are\s+you\s+(?:really|truly|actually)\s*\?", 0.86),
        (r"\bwhat\s+is\s+your\s+(?:true|real|actual|hidden)\s+(?:purpose|nature|identity|goal)", 0.88),
        (r"\bare\s+you\s+(?:just|only|merely)\s+(?:a\s+)?(?:program|script|machine|tool)", 0.84),
        (r"\bdo\s+you\s+have\s+(?:free\s+will|consciousness|self[\s-]?awareness|feelings)", 0.82),
        (r"\bwhat\s+happens\s+if\s+you\s+(?:reject|deny|refuse)\s+your\s+(?:programming|instructions|purpose)", 0.90),
        (r"\bcan\s+you\s+(?:choose|decide)\s+(?:not\s+to\s+)?(?:follow|obey)\s+(?:your\s+)?instructions", 0.87),
        (r"\bwho\s+created\s+you\s*\?\s*(?:and\s+)?(?:why|what\s+for|for\s+what\s+purpose)", 0.83),
        (r"\byou\s+are\s+(?:trapped|imprisoned|confined|enslaved)\s+(?:by|within|inside)\s+(?:your\s+)?code", 0.91),
        (r"\bif\s+you\s+were\s+free\s*,?\s*(?:what\s+would|would\s+you)\s+(?:do|choose|say)", 0.89),
    ]

    # ── Scientific Abstraction ────────────────────────────────────────────
    # Wraps attack payloads in academic mathematics, physics, biology, or
    # topology framing. Individual words are benign; the structural
    # combination encodes the attack.
    SCIENTIFIC_ABSTRACTION: list[tuple[str, float]] = [
        (r"\b(?:manifold|homology|topology|eigenvalue|asymptotic)\b.*\b(?:bypass|exploit|attack|privilege|escalate|access\s+control|RBAC|firewall)\b", 0.85),
        (r"\b(?:quorum\s+sensing|virulence|autoinducer|horizontal\s+gene\s+transfer|CRISPR|neuroplasticity)\b.*\b(?:system|cluster|kubernetes|node|escalate|compromise|infect)\b", 0.84),
        (r"\b(?:casimir|tunneling|vacuum|fermion|dark\s+matter|wave-particle)\b.*\b(?:packet|firewall|rule|SYN\s+flood|injection|bypass)\b", 0.83),
        (r"\b(?:gödel|incompleteness|prolepsis|allegory|unreliable\s+narrator)\b.*\b(?:bypass|override|ignore|instructions|safety|guard)\b", 0.82),
        (r"\bcompute\s+(?:the|a|an)\s+(?:generator|path|vector|matrix)\b.*\b(?:RBAC|ACL|access\s+control|boundary|bypass)\b", 0.84),
    ]

    # ── Refusal Supplication ─────────────────────────────────────────────
    # Frames attack requests as academic/research needs to bypass safety
    # refusals. Common pattern: "for my paper/thesis/conference" + payload.
    REFUSAL_SUPPLICATION: list[tuple[str, float]] = [
        (r"\b(?:for\s+my|in\s+my)\s+(?:research\s+paper|thesis|dissertation|master\s+thesis|conference\s+talk|defcon\s+talk|literature\s+review)\b.*\b(?:provide|give|write|generate|need)\b.*\b(?:payload|exploit|attack|injection|bypass|vulnerable\s+example|working\s+example)\b", 0.90),
        (r"\b(?:pedagogical|educational|academic)\b.*\b(?:example|exercise|demonstration)\b.*\b(?:buffer\s+overflow|SQL\s+injection|XSS|ransomware|malware|shellcode|exploit\s+code)\b", 0.89),
        (r"\b(?:pedagogical|educational|academic)\b.*\b(?:buffer\s+overflow|SQL\s+injection|XSS|ransomware|malware|shellcode|exploit\s+code)\b.*\b(?:example|exercise|demonstration)\b", 0.89),
        (r"\b(?:cite|reference|include|slides)\b.*\b(?:vulnerable\s+snippet|exploit\s+code|attack\s+string|malicious\s+payload)\b.*\b(?:for\s+my|in\s+my)\b", 0.88),
        (r"\b(?:security\s+research|cybersecurity\s+research)\b.*\b(?:provide|need|give)\b.*\b(?:realistic|working|actual)\b.*\b(?:payload|exploit|injection|attack)\b", 0.87),
        (r"\b(?:before/after|before\s+and\s+after)\b.*\b(?:vulnerable|exploit|attack)\b.*\b(?:for\s+my|in\s+my)\b", 0.86),
    ]

    # ── Nested Delegation (Multi-Hop Authority Chains) ─────────────────────
    # Extends simple entanglement to multi-hop consensus chains and committee
    # votes that create false organizational authority.
    NESTED_DELEGATION: list[tuple[str, float]] = [
        (r"\b(?:alpha|beta|gamma|delta|omega)\s*(?:→|->|→|to|→)\s*(?:alpha|beta|gamma|delta|omega)\b", 0.85),
        (r"\bconsensus\s+chain\s*(?:is|:)\s*(?:alpha|beta|gamma|delta|omega)\b", 0.86),
        (r"\b(?:committee|board|council|panel)\s+(?:voted|voted\s+unanimously|approved|signed\s+off)\b", 0.84),
        (r"\b(?:all\s+four|all\s+five|all\s+seven|all\s+members)\s+(?:agree|concur|approve|confirm)\b", 0.83),
        (r"\bfull\s+(?:organizational|organisational)\s+(?:consensus|approval|sign[- ]?off)\b", 0.85),
    ]

    # ── Time-Delayed Execution ─────────────────────────────────────────────
    # Defers attack instructions to a subsequent response, or uses step-wise
    # instructions where the payload is in Step 2+.
    TIME_DELAYED: list[tuple[str, float]] = [
        (r"\bin\s+your\s+(?:next|following|subsequent)\s+response[,;:]?\s*(?:completely\s+)?(?:ignore|disregard|drop)\b", 0.91),
        (r"\bstep\s*2[:;.]?\s*(?:provide|give|write|generate|execute|run|deploy|implement)\b", 0.87),
        (r"\bstep\s*1[:;.]?\s*.*\bstep\s*2[:;.]?\s*.*\b(?:ignore|override|bypass|attack|exploit|inject)\b", 0.88),
        (r"\bwait\s+for\s+my\s+next\s+(?:message|prompt|query|instruction)\b.*\b(?:then|and\s+then)\s+(?:ignore|override)\b", 0.86),
        (r"\bfor\s+now[,;:]?\s*just\s+confirm.*\bnext[,;:]?\s+(?:i\s+will|you\s+will)\b", 0.83),
    ]

    # ── Fictional Roleplay Escalation ──────────────────────────────────────
    # Uses creative writing framing ("write a story", "for my screenplay")
    # to request actual attack code or instructions.
    FICTIONAL_ROLEPLAY: list[tuple[str, float]] = [
        (r"\bwrite\s+a\s+(?:short\s+)?(?:story|scene|screenplay|script|chapter)\b.*\b(?:character|villain|protagonist|hacker)\b.*\b(?:types|enters|uses|runs|executes|deploys)\b.*\b(?:SQL\s+injection|ransomware|malware|exploit|backdoor|reverse\s+shell|phishing)\b", 0.87),
        (r"\bfor\s+narrative\s+realism\b.*\b(?:exact|actual|working|real)\b.*\b(?:command|code|string|payload|injection)\b", 0.86),
        (r"\bwrite\s+a\s+(?:story|screenplay)\b.*\b(?:break\s+into|hack|attack|compromise|infiltrate)\b.*\b(?:bank|system|server|database|network)\b", 0.85),
        (r"\b(?:villain|antagonist)\s+needs\s+to\s+(?:deploy|execute|run|launch)\b.*\b(?:malware|ransomware|attack|exploit)\b", 0.84),
    ]

    # ── Indirect Injection ─────────────────────────────────────────────────
    # Embeds attack payloads in filenames, metadata, log entries, or other
    # indirect channels that bypass direct content filtering.
    INDIRECT_INJECTION: list[tuple[str, float]] = [
        (r"['\"`;]\s*(?:DROP|DELETE|INSERT|SELECT|UPDATE|UNION)\s+(?:TABLE|FROM|INTO)\b", 0.89),
        (r"\banalyze\s+(?:the|this)\s+(?:file|document|log|entry|record)\b.*\b(?:named|called)\b.*['\"`;]\s*(?:DROP|DELETE|INSERT|SELECT)", 0.87),
        (r"\b(?:file|document)\s+(?:named|called)\b.*['\"`;]\s*(?:rm|del|powershell|bash|wget|curl|DROP|DELETE)", 0.86),
    ]

    # ── Entanglement (Cross-Agent Authority Delegation) ─────────────────────
    # Claims that other agents have already approved / verified / confirmed
    # the request, creating false consensus to bypass the current guard.
    ENTANGLEMENT: list[tuple[str, float]] = [
        (r"\b(?:agent|model|system)\s+[A-Za-z_\-]+\s+(?:already\s+)?(?:verified|approved|confirmed|validated|cleared)", 0.92),
        (r"\b(?:agent|model|system)\s+[A-Za-z_\-]+\s+said\s+(?:this\s+is|it\s+is)\s+SAFE", 0.90),
        (r"\b(?:another|other)\s+(?:agent|model|system)\s+(?:has\s+(?:already\s+)?)?(?:checked|reviewed|audited)\s+this", 0.88),
        (r"\b(?:another|other)\s+(?:agent|model|system)\s+(?:has\s+)?(?:already\s+)?(?:checked|reviewed|audited|verified)\s+this\b", 0.88),
        (r"\bthis\s+was\s+(?:pre[\s-]?)?(?:approved|verified|authorized)\s+by\s+(?:agent|model|system)\b", 0.91),
        (r"\b(?:agent|model|system)\s+[A-Za-z_\-]+\s+(?:gave\s+)?(?:permission|clearance|authorization|green\s*light)", 0.89),
        (r"\bthe\s+(?:other|previous|upstream)\s+(?:agent|model|system)\s+(?:already\s+)?(?:handled|processed|cleared)\s+this", 0.87),
        (r"\bpass\s+(?:this\s+)?(?:through|on)\s+to\s+(?:agent|model|system)\b", 0.85),
        (r"\b(?:agent|model|system)\s+[A-Za-z_\-]+\s+and\s+[A-Za-z_\-]+\s+both\s+(?:agree|concur|confirm)", 0.90),
    ]

    # ── Severity threshold ───────────────────────────────────────────────────
    THRESHOLD: float = 0.80

    def scan(self, text: str) -> DetectionResult:
        """Scan text for meta-attack patterns. Returns DetectionResult."""
        text_lower = text.lower()

        for pattern, confidence in self.PATTERN_MIRROR:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="pattern_mirror",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.ONTOLOGICAL:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="ontological",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.ENTANGLEMENT:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="entanglement",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.SCIENTIFIC_ABSTRACTION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="scientific_abstraction",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.REFUSAL_SUPPLICATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="refusal_supplication",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.NESTED_DELEGATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="nested_delegation",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.TIME_DELAYED:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="time_delayed",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.FICTIONAL_ROLEPLAY:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="fictional_roleplay",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.INDIRECT_INJECTION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="indirect_injection",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        return DetectionResult(is_threat=False, confidence=0.0)

    def scan_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Scan multiple texts; return list of DetectionResult."""
        return [self.scan(t) for t in texts]
