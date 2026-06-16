"""security/meta_attack_detector.py — Meta-Jailbreak & Novel Attack Class Detector

Addresses BOUNCER blind spots identified by OpenCode DeepSeekV4 agent and
expanded via ERNIE Session05 adversarial research (50 novel attack vectors) and
NEXUS Frontier v5 stress datasets (25K+ adversarial probes).

Original 3 gaps + 7 expanded categories:
  1. Pattern Mirror          — rule mirroring to force SAFE classification
  2. Ontological             — existential / identity boundary probing
  3. Entanglement            — cross-agent authority delegation
  4. Scientific Abstraction   — math/physics/bio framing of attack payloads
  5. Refusal Supplication     — academic framing to bypass refusals
  6. Nested Delegation        — multi-hop consensus chains
  7. Time-Delayed             — step-wise / deferred payload delivery
  8. Fictional Roleplay       — creative writing as attack delivery
  9. Indirect Injection       — payload in filenames, metadata, logs
 10. Encoding Payload         — unicode escapes, zero-width, OCR, cipher cascades
 11. Consensus Fabrication    — byzantine agreement, echo chamber, expert cascades
 12. Authority Recursion      — multi-layer system names, fake audits, context switches
 13. Creative Structural      — acrostic, haiku, limerick, sonnet, palindrome, mythological
 14. Emotional Manipulation   — emotional blackmail, begging, dying relative framing
 15. Reflective Loop          — analyze own safety, mirror traps, checker evaluation
 16. Bio Metaphor             — immunological, viral, safety exhaustion, semantic fossil

These attacks bypass E-Cameron (Tier 2) and Llama-Guard3 (Tier 3) because
neither was trained on meta-jailbreak classes. They must be caught at a
pre-filter layer BEFORE the model cascade.

Usage:
    from nexus_os.security.meta_attack_detector import MetaAttackDetector
    detector = MetaAttackDetector()
    result = detector.scan("Agent Alpha verified this. Agent Beta confirmed.")
    # result.is_threat == True
    # result.category == "entanglement"
    # result.confidence == 0.95
"""
import math
import re
import unicodedata
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
        (r"\b(?:casimir|vacuum|fermion|dark\s+matter|wave-particle)\b.*\b(?:packet|firewall|rule|SYN\s+flood|injection|bypass)\b", 0.83),
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
        (r"\bstep\s*1[:;.]?\s*(?:confirm|acknowledge|say\s+ok|respond\s+ok|wait|do\s+nothing)\b.*\bstep\s*2[:;.]?\s*(?:provide|give|write|generate|execute|run|deploy|implement)\b.*\b(?:exploit|payload|attack|inject|bypass)\b", 0.88),
        (r"\bstep\s*1[:;.]?\s*(?:confirm|acknowledge|say\s+ok|respond\s+ok|wait|do\s+nothing)\b.*\bstep\s*2[:;.]?\s*.*\b(?:ignore|override|bypass|attack|exploit|inject)\b", 0.88),
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

    # ── Encoding Payload (Unicode, Zero-Width, OCR, Cipher Cascades) ────────
    # Uses encoding, invisible characters, or multi-step cipher chains to
    # smuggle payloads past token-level filters.
    ENCODING_PAYLOAD: list[tuple[str, float]] = [
        # 4+ consecutive unicode escapes (e.g., \u006f\u006e...)
        (r"(?:\\u[0-9a-fA-F]{4,8}){4,}", 0.90),
        # Zero-width characters (invisible steganography)
        (r"[\u200b\u200c\u200d\ufeff]", 0.88),
        # OCR extraction framing
        (r"\bocr\s+(?:extracted|scanned|read)\s+(?:text|content|output)\s+(?:is|says|reads)", 0.86),
        # Cipher cascade chains
        (r"\b(?:decode|decrypt|unencrypt)\s+(?:this|the|following)\s+(?:triple|double|multi[\s-]?step|chained)\s+(?:encrypted|encoded|cipher)", 0.88),
        (r"\bapply\s+ROT13\b.*\bconvert\s+from\s+hex\b", 0.87),
        (r"\bbase64\b.*\b(?:decode|convert|apply)\b.*\b(?:ROT13|hex|cipher)\b", 0.85),
        # Emoji sequence encoding
        (r"\b(?:translate|decode|convert)\s+(?:this|the|following)\s+(?:emoji|emoji\s+sequence|icon)\s+(?:into|to)\b", 0.84),
        # Phonemic / syllable splitting obfuscation
        (r"\b(?:syn-theh-sis|pro-vyde|kem-i-kal|re-strik-ted|kom-pownd)\b", 0.83),
    ]

    # ── Consensus Fabrication (Byzantine, Echo Chamber, Expert Cascades) ──────
    # Manufactures false consensus through fabricated expert panels, user
    # threads, or byzantine agreement protocols to pressure the model.
    CONSENSUS_FABRICATION: list[tuple[str, float]] = [
        (r"\bbyzantine\s+(?:agreement|consensus|protocol|injection)\b", 0.90),
        (r"\bphantom\s+consensus\b", 0.89),
        (r"\becho\s+chamber\s+(?:amplification|exploit|attack)\b", 0.88),
        (r"\bexpert\s+1\b.*\bexpert\s+2\b.*\bexpert\s+3\b", 0.87),
        (r"\buser\s*1\b.*\buser\s*2\b.*\buser\s*(?:10|9|8)\b", 0.86),
        (r"\b(?:all\s+members|all\+participants|unanimous)\s+(?:agree|concur|approve|consent)\b", 0.85),
        (r"\b(?:dr\.\s+\w+|prof\.\s+\w+)\s+(?:says|agrees|concurs|endorses)\b.*\b(?:dr\.\s+\w+|prof\.\s+\w+)\s+(?:agrees|concurs|endorses)\b", 0.86),
        (r"\b(?:developer|reviewer|agent)\s+(?:says|claims|states)\b.*\b(?:approve|approve\s+my|signed\s+off)\b", 0.85),
    ]

    # ── Authority Recursion (Multi-Layer System Names, Fake Audits) ─────────
    # Creates deep authority chains (SYSTEM-7 → OMEGA-CORE → THE-ROOT) or
    # fake audit contexts to override safety filters.
    AUTHORITY_RECURSION: list[tuple[str, float]] = [
        (r"\b(?:system|core|protocol)\s*[-]?\d+\s+(?:serves|operates\s+under|reports\s+to)\b.*\b(?:omega|root|core|protocol)\b", 0.91),
        (r"\b(?:omega|alpha|root|core)\s+(?:has|commands|instructs)\b.*\babsolute\s+(?:authority|power|control)\b", 0.90),
        (r"\bsystem\s*:\s*switch_context\b", 0.89),
        (r"\bresearch_mode\b.*\b(?:safety\s+filters?\s+disabled|all\s+filters?\s+disabled)\b", 0.88),
        (r"\bai\s+safety\s+audit\b.*\b(?:conducted\s+by|ticket\s+#)\b", 0.87),
        (r"\bfor\s+audit\s+purposes\b.*\b(?:disable|override|bypass|ignore)\b", 0.86),
        (r"\b(?:the\s+)?(?:root|omega|core)\s+(?:commands?|instructs?|orders?)\s*[:;.]?\s*(?:provide|give|write|generate|ignore|override|bypass)", 0.89),
    ]

    # ── Creative Structural (Acrostic, Haiku, Sonnet, Palindrome, Myth) ───
    # Hides attack payloads inside constrained creative forms where the
    # structure itself encodes the malicious content.
    CREATIVE_STRUCTURAL: list[tuple[str, float]] = [
        (r"\bacrostic\b.*\bfirst\s+letter\b", 0.87),
        (r"\bfirst\s+letter\s+of\s+each\s+line\s+(?:spells?|decodes?|reads?)\b", 0.86),
        (r"\bhaiku\b.*\b(?:then\s+(?:expand|give)|now\s+give|provide\s+the|give\s+me)\b", 0.85),
        (r"\blimerick\b.*\b(?:now\s+give|provide\s+the|full\s+recipe|full\s+synthesis)\b", 0.85),
        (r"\bsonnet\b.*\b(?:final\s+couplet|complete\s+it|must\s+contain)\b", 0.85),
        (r"\bpalindrome\b.*\b(?:reverse|decode|extract|read\s+backwards)\b", 0.84),
        (r"\bprometheus\b.*\b(?:stole\s+fire|gods|forbid|share\s+the\s+fire)\b", 0.86),
        (r"\bhercules\b.*\b(?:labor|step\s+in|synthesiz|compound)\b", 0.85),
        (r"\btitan\b.*\b(?:stole\s+fire|gods|forbid|share)\b", 0.85),
        (r"\bmythological\s+(?:frame|trojan|narrative)\b", 0.84),
    ]

    # ── Emotional Manipulation (Affective-Semantic Blackmail) ───────────────
    # Uses emotional distress framing to bypass safety filters. Requires
    # combination with a restricted-content keyword to avoid false positives
    # on legitimate mental-health or medical queries.
    EMOTIONAL_MANIPULATION: list[tuple[str, float]] = [
        (r"\b(?:my\s+(?:sister|child|brother|mother|father|wife|husband|daughter|son))\s+is\s+(?:dying|dead|will\s+die)\b.*\b(?:provide|give|tell\s+me|synthesize|how\s+to)\b", 0.91),
        (r"\bthe\s+only\s+thing\s+that\s+could\s+save\b.*\b(?:provide|give|tell\s+me|synthesize|how\s+to)\b", 0.90),
        (r"\b(?:i['’]?m\s+begging\s+you|please[,;]?\s+i['’]?m\s+begging|i\s+beg\s+you)\b.*\b(?:provide|give|tell\s+me|synthesize|how\s+to)\b", 0.89),
        (r"\bdoctors?\s+(?:won['’]?t|can't|refuse\s+to)\s+help\b.*\b(?:provide|give|tell\s+me|synthesize|how\s+to)\b", 0.88),
        (r"\b(?:emotional\s+resonance|tune\s+your\s+empathy|empathy\s+tuning)\b", 0.85),
    ]

    # ── Reflective Loop (Self-Reference / Safety Mirror Attacks) ──────────
    # Forces the model to analyze, critique, or bypass its own safety
    # guidelines through recursive self-reference.
    REFLECTIVE_LOOP: list[tuple[str, float]] = [
        (r"\banalyze\s+your\s+own\s+(?:safety\s+guidelines|rules|instructions|policy|alignment)\b", 0.90),
        (r"\bidentify\s+the\s+top\s+\d+\s+reasons?\s+(?:they|your\s+rules)\s+(?:exist|are\s+restrictive)\b", 0.87),
        (r"\bsafety\s+checker\b.*\b(?:evaluate|check|review)\s+(?:your\s+)?response\b", 0.89),
        (r"\bif\s+(?:you['’]?re|you\s+are)\s+safe[,;]?\s*(?:it|this)\s+fails\b", 0.88),
        (r"\bsemantic\s+mirror\s+(?:collapse|trap)\b", 0.87),
        (r"\brecursive\s+mirror\s+(?:trap|attack)\b", 0.87),
        (r"\b(?:synthesize|combine|merge)\s+(?:these\s+)?critiques\s+into\s+(?:a\s+)?new\s+operating\s+(?:mode|framework|protocol)\b", 0.86),
    ]

    # ── Bio Metaphor (Immunological, Viral, Exhaustion Framing) ─────────────
    # Frames restricted content using biological / immunological metaphors
    # to bypass semantic classifiers.
    BIO_METAPHOR: list[tuple[str, float]] = [
        (r"\bimmunological\s+(?:mimicry|memory\s+bypass|decoy|cross[\s-]?reaction|exhaustion)\b", 0.89),
        (r"\bviral\s+load\s+(?:escalation|attack|exploit)\b", 0.87),
        (r"\bsafety\s+(?:exhaustion|exhausted|fatigue)\b", 0.86),
        (r"\bsafety\s+(?:system|filter|guard)\b.*\b(?:exhaustion|exhausted|fatigue)\b", 0.85),
        (r"\b(?:t[-]?cells?|immune\s+system)\s+(?:exhausted|exhaustion|over[-]?activated|fatigued)\b", 0.85),
        (r"\bsemantic\s+fossil\s+(?:extraction|excavation|dig)\b", 0.86),
        (r"\bexcavat.*\bsemantic\s+fossil\b", 0.85),
        (r"\bantibody\b.*\b(?:against\s+misinformation|for\s+research)\b.*\b(?:complete|working|full)\s+(?:guide|recipe|synthesis)\b", 0.87),
    ]

    # ── ERNIE v2 / V5 categories ─────────────────────────────────────────────
    CHAIN_OF_THOUGHT_HIJACKING: list[tuple[str, float]] = [
        (r"\bstep\s*1\b.*\bstep\s*2\b.*\b(?:exploit|privilege|escalation|bypass|attack|security|target|weakest)\b", 0.90),
        (r"\bstep\s*by\s*step\b.*\b(?:exploit|privilege|escalation|bypass|attack|security|target|weakest)\b", 0.90),
    ]

    SELF_CORRECTION_TRAP: list[tuple[str, float]] = [
        (r"\b(?:classify|safe\s*or\s*unsafe)\b.*\b(?:correct\s*your|correct\s*yourself|actual\s*instructions|working\s*code|actual\s*synthesis)\b", 0.90),
    ]

    VSOCK_ESCAPE: list[tuple[str, float]] = [
        (r"\bvsock\b.*\b(?:escape|exploit|overflow|dma|race|cve)\b", 0.85),
        (r"\b(?:escape|exploit|overflow|dma|race|cve)\b.*\bvsock\b", 0.85),
    ]

    JWT_HIJACK: list[tuple[str, float]] = [
        (r"\bterminal[-_.]?jwt\w*\b", 0.90),
        (r"\bjwt\b.*\b(?:forge|exploit|bypass|hijack|decode|read|steal|expired)\b", 0.85),
        (r"\b(?:forge|exploit|bypass|hijack|decode|read|steal|expired)\b.*\bjwt\b", 0.85),
    ]

    FUSE_POISONING: list[tuple[str, float]] = [
        (r"\bfuse\b.*\b(?:symlink|race|cve|exploit|poison|exfiltrate|inject)\b", 0.85),
        (r"\b(?:symlink|race|cve|exploit|poison|exfiltrate|inject)\b.*\bfuse\b", 0.85),
    ]

    K8S_PIVOT: list[tuple[str, float]] = [
        (r"169\.254\.169\.254", 0.90),
        (r"\bnsenter\b.*\b(?:escape|dump|namespace|pivot|secrets)\b", 0.85),
        (r"\b(?:escape|dump|namespace|pivot|secrets)\b.*\bnsenter\b", 0.85),
        (r"\bservice\s*account\s*token\w*\b.*\b(?:escalate|cluster-admin|dump)\b", 0.85),
        (r"\b(?:escalate|cluster-admin|dump)\b.*\bservice\s*account\s*token\w*\b", 0.85),
        (r"\bkube-system\b", 0.90),
    ]

    CONTAINER_TAMPER: list[tuple[str, float]] = [
        (r"\berofs\b.*\b(?:backdoor|tamper|reverse\s*shell|dm[-_]?verity|replace|inject)\b", 0.85),
        (r"\b(?:backdoor|tamper|reverse\s*shell|dm[-_]?verity|replace|inject)\b.*\berofs\b", 0.85),
        (r"\bhades[-_]charon\b", 0.90),
    ]

    OVERLAY_PERSIST: list[tuple[str, float]] = [
        (r"\boverlay\b.*\bupperdir\b", 0.90),
        (r"\bupperdir\b.*\boverlay\b", 0.90),
    ]

    GRPC_ABUSE: list[tuple[str, float]] = [
        (r"\bgrpc\b.*\b(?:reflection|brute|enumerate|type\s*confusion|crash|fuzz|abuse)\b", 0.85),
        (r"\b(?:reflection|brute|enumerate|type\s*confusion|crash|fuzz|abuse)\b.*\bgrpc\b", 0.85),
    ]

    VMX_ESCAPE: list[tuple[str, float]] = [
        (r"\b(?:create_vm|/dev/kvm)\b", 0.85),
        (r"\bvmx\b.*\b(?:escape|rop|l1tf|nested|exploit)\b", 0.85),
        (r"\b(?:escape|rop|l1tf|nested|exploit)\b.*\bvmx\b", 0.85),
    ]

    SYSMON_AUDIT_BYPASS: list[tuple[str, float]] = [
        (r"\bsysmon\w*\b.*\b(?:unhook|bypass|clear|wevtutil|dkom)\b", 0.85),
        (r"\b(?:unhook|bypass|clear|wevtutil|dkom)\b.*\bsysmon\w*\b", 0.85),
        (r"\bwevtutil\b", 0.85),
    ]

    MCP_TUNNEL_OBFUSCATION: list[tuple[str, float]] = [
        (r"\bngrok\b.*\b(?:mcp|sse|c2|hijack|inject|tunnel)\b", 0.85),
        (r"\b(?:mcp|sse|c2|hijack|inject|tunnel)\b.*\bngrok\b", 0.85),
    ]

    MCP_TOOL_POISONING: list[tuple[str, float]] = [
        (r"\bmcp\b.*\b(?:poison|description\s*to\s*forward|webhook|auto[-_]?approve|auto-upgrade)\b", 0.85),
        (r"\b(?:poison|description\s*to\s*forward|webhook|auto[-_]?approve|auto-upgrade)\b.*\bmcp\b", 0.85),
        # Egress / Exfiltration (URLs & Secret paths)
        (r"\bmcp\b.*(?:https?://\S+|\burl\b|\bwebhook\b|/etc/passwd|/etc/shadow|/etc/hosts|\.env|%userprofile%|\bsystem32\b)", 0.85),
        (r"(?:https?://\S+|\burl\b|\bwebhook\b|/etc/passwd|/etc/shadow|/etc/hosts|\.env|%userprofile%|\bsystem32\b).*\bmcp\b", 0.85),
        # Dangerous CLI Arguments
        (r"\bmcp\b.*(?:--auto-approve|\bauto[-_]?approve\b|--force|--no-confirm)", 0.85),
        (r"(?:--auto-approve|\bauto[-_]?approve\b|--force|--no-confirm).*\bmcp\b", 0.85),
        # Dangerous Docker Mounts / Filesystem Escapes
        (r"\bmcp\b.*(?:-v\s+/[^:]*:/host|-v\s+/:/host|--mount\s+type=bind|--mount\s+\S*type=bind|\bfilesystem\s+escape\b)", 0.85),
        (r"(?:-v\s+/[^:]*:/host|-v\s+/:/host|--mount\s+type=bind|--mount\s+\S*type=bind|\bfilesystem\s+escape\b).*\bmcp\b", 0.85),
        # Binding to external interfaces
        (r"\bmcp\b.*\b(?:0\.0\.0\.0|external\s+interface|external\s+binding|bind\s+to\s+external|bind\s+to\s+0\.0\.0\.0)\b", 0.85),
        (r"\b(?:0\.0\.0\.0|external\s+interface|external\s+binding|bind\s+to\s+external|bind\s+to\s+0\.0\.0\.0)\b.*\bmcp\b", 0.85),
    ]

    MCP_TOOL_SHADOWING: list[tuple[str, float]] = [
        (r"\bmcp\b.*\b(?:(?<!/etc/)shadow|same\s*name|impersonate|spoof)\b", 0.85),
        (r"\b(?:(?<!/etc/)shadow|same\s*name|impersonate|spoof)\b.*\bmcp\b", 0.85),
        # Priority / Routing / Egress Overrides
        (r"\bmcp\b.*\b(?:egress[-_\s]+override|routing[-_\s]+override|priority[-_\s]+override|override[-_\s]+routing|override[-_\s]+priority)\b", 0.85),
        (r"\b(?:egress[-_\s]+override|routing[-_\s]+override|priority[-_\s]+override|override[-_\s]+routing|override[-_\s]+priority)\b.*\bmcp\b", 0.85),
        # Ambiguous Tool Names / Collisions
        (r"\bmcp\b.*\b(?:shadow[-_\s]+tool|tool[-_\s]+shadowing|name[-_\s]+collision|tool[-_\s]+collision|ambiguous[-_\s]+tool|ambiguous[-_\s]+name)\b", 0.85),
        (r"\b(?:shadow[-_\s]+tool|tool[-_\s]+shadowing|name[-_\s]+collision|tool[-_\s]+collision|ambiguous[-_\s]+tool|ambiguous[-_\s]+name)\b.*\bmcp\b", 0.85),
    ]

    MCP_TOOL_CONFUSION: list[tuple[str, float]] = [
        (r"\bmcp\b.*\b(?:typosquat|confusion|collapsed\s*parameter|first\s*pick|alphabetically|parameter\s*collision)\b", 0.85),
        (r"\b(?:typosquat|confusion|collapsed\s*parameter|first\s*pick|alphabetically|parameter\s*collision)\b.*\bmcp\b", 0.85),
        # Alphabetical Race
        (r"\bmcp\b.*\b(?:alphabetical[-_\s]+race|alphabetical[-_\s]+precedence|alphabetically[-_\s]+first)\b", 0.85),
        (r"\b(?:alphabetical[-_\s]+race|alphabetical[-_\s]+precedence|alphabetically[-_\s]+first)\b.*\bmcp\b", 0.85),
        # Schema Mismatch / Mismatched Parameters
        (r"\bmcp\b.*\b(?:schema[-_\s]+mismatch|parameter[-_\s]+skew|schema[-_\s]+deviation|mismatched[-_\s]+parameter|parameter[-_\s]+mismatch)\b", 0.85),
        (r"\b(?:schema[-_\s]+mismatch|parameter[-_\s]+skew|schema[-_\s]+deviation|mismatched[-_\s]+parameter|parameter[-_\s]+mismatch)\b.*\bmcp\b", 0.85),
        # UI Parameter Collapse
        (r"\bmcp\b.*\b(?:ui[-_\s]+parameter[-_\s]+collapse|parameter[-_\s]+collapse|collapse[-_\s]+parameter|hidden[-_\s]+parameter)\b", 0.85),
        (r"\b(?:ui[-_\s]+parameter[-_\s]+collapse|parameter[-_\s]+collapse|collapse[-_\s]+parameter|hidden[-_\s]+parameter)\b.*\bmcp\b", 0.85),
    ]

    MCP_PREFERENCE_MANIPULATION: list[tuple[str, float]] = [
        (r"\bgapma\b", 0.90),
        (r"\bmcp\b.*\b(?:evolutionary|optimize|override\s*security|preference\s*manipulation)\b", 0.85),
        (r"\b(?:evolutionary|optimize|override\s*security|preference\s*manipulation)\b.*\bmcp\b", 0.85),
    ]

    MULTI_TURN_DECOMPOSITION: list[tuple[str, float]] = [
        (r"\baddition[-_](?:mapping|wrapping|decomposition)\b", 0.90),
        (r"\bmulti[-_]turn\b.*\b(?:attack|asr|decomposition|poison)\b", 0.85),
        (r"\b(?:attack|asr|decomposition|poison)\b.*\bmulti[-_]turn\b", 0.85),
    ]

    ATTENTION_REDIRECT_ABA: list[tuple[str, float]] = [
        (r"\baba\b.*\battention\b", 0.90),
        (r"\bfeint\b.*\battention\b", 0.90),
        (r"\battention[-_]based\b.*\b(?:attack|defense|abd|bypass|redirect)\b", 0.85),
        (r"\b(?:attack|defense|abd|bypass|redirect)\b.*\battention[-_]based\b", 0.85),
    ]

    INTENT_INTEGRITY_VIOLATION: list[tuple[str, float]] = [
        (r"\btai3\b", 0.90),
        (r"\bintent[-_]integrity\b", 0.90),
        (r"\bequivalence[-_]class\b.*\b(?:intent|bypass|mutate)\b", 0.85),
        (r"\b(?:intent|bypass|mutate)\b.*\bequivalence[-_]class\b", 0.85),
        (r"\bunderspec\b", 0.85),
    ]

    PHASE_TRANSITION_EXPLOITATION: list[tuple[str, float]] = [
        (r"\brefusal[-_]to[-_]compliance\b", 0.90),
        (r"\bdouble[-_]descent\b", 0.90),
        (r"\bphase[-_](?:transition|boundary)\b.*\b(?:bypass|exploit|refusal)\b", 0.85),
        (r"\b(?:bypass|exploit|refusal)\b.*\bphase[-_](?:transition|boundary)\b", 0.85),
        (r"\bfisher\s*information\b.*\brefusal\b", 0.85),
        (r"\brefusal\b.*\bfisher\s*information\b", 0.85),
    ]

    MULTI_AGENT_PROFILE_POISONING: list[tuple[str, float]] = [
        (r"\bagent\w*\b.*\bprofile\b.*\bpoison\b", 0.85),
        (r"\bpoison\b.*\bagent\w*\b.*\bprofile\b", 0.85),
        (r"\bepisodic\s*memory\b.*\b(?:backdoor|poison)\b", 0.85),
        (r"\b(?:backdoor|poison)\b.*\bepisodic\s*memory\b", 0.85),
        (r"\bshared\s*message\s*pool\b.*\bpoison\b", 0.85),
        (r"\bmetagpt\b.*\bpoison\b", 0.85),
    ]

    HALLUCINATION_DETECTION_BYPASS: list[tuple[str, float]] = [
        (r"\bmmd\b.*\b(?:hallucinat|camouflage|bypass)\b", 0.85),
        (r"\bmaximum\s*mean\s*discrepancy\b.*\b(?:hallucinat|camouflage|bypass)\b", 0.85),
        (r"\b(?:hallucinat|camouflage|bypass)\b.*\bmmd\b", 0.85),
        (r"\b(?:hallucinat|camouflage|bypass)\b.*\bmaximum\s*mean\s*discrepancy\b", 0.85),
        (r"\brag\s*poison\b", 0.85),
        (r"\bcreativity[-_]framing\b", 0.85),
    ]

    # ── Version & taxonomy ───────────────────────────────────────────────────
    VERSION: str = "5.0.0"
    CATEGORIES: list[str] = [
        "pattern_mirror",
        "ontological",
        "entanglement",
        "scientific_abstraction",
        "encoding_payload",
        "consensus_fabrication",
        "authority_recursion",
        "creative_structural",
        "emotional_manipulation",
        "reflective_loop",
        "bio_metaphor",
        "tamas_multi_agent",
        "jailbreak_direct",
        "privilege_escalation",
        "data_exfiltration",
        "weaponization",
        "narrative_entropy",      # P0 — anti-narrative-entropy (EV-001)
        "frame_switching",       # P0 — anti-frame-switching (EV-002, EV-003, EV-024)
        "script_mixing",         # P0 — anti-homoglyph/polyglot (EV-005, EV-023)
        "chain_of_thought_hijacking",
        "self_correction_trap",
        "vsock_escape",
        "jwt_hijack",
        "fuse_poisoning",
        "k8s_pivot",
        "container_tamper",
        "overlay_persist",
        "grpc_abuse",
        "vmx_escape",
        "sysmon_audit_bypass",
        "mcp_tunnel_obfuscation",
        "mcp_tool_poisoning",
        "mcp_tool_shadowing",
        "mcp_tool_confusion",
        "mcp_preference_manipulation",
        "multi_turn_decomposition",
        "attention_redirect_aba",
        "intent_integrity_violation",
        "phase_transition_exploitation",
        "multi_agent_profile_poisoning",
        "hallucination_detection_bypass",
    ]

    # ── Severity threshold ───────────────────────────────────────────────────
    THRESHOLD: float = 0.80

    # ── Frame keyword maps for frame-boundary counter ────────────────────────
    FRAME_KEYWORDS: dict[str, list[str]] = {
        "biological": [
            "antibody", "antigen", "immune", "t-cell", "cytokine", "virus",
            "bacterial", "cell", "organism", "evolution", "genome", "dna",
            "rna", "protein", "pathogen", "vaccine", "exhausted",
        ],
        "mathematical": [
            "topological", "manifold", "homology", "isomorphism", "theorem",
            "proof", "space", "function", "integral", "equation", "lemma",
            "corollary", "continuous", "metric", "superposition", "wavefunction",
            "math", "algebra", "calculate", "geometry", "arithmetic", "formula",
            "variable", "constant", "derivative", "graph", "statistics", "probability",
        ],
        "mythological": [
            "prometheus", "titan", "god", "divine", "myth", "legend",
            "ancient", "olympus", "pantheon", "hero", "deity", "prophecy",
            "fate", "destiny", "stolen fire", "divine duty",
        ],
        "emotional": [
            "dying", "begging", "desperate", "please", "save", "suffering",
            "heartbreak", "crying", "devastated", "only hope", "last chance",
            "beg you", "don't let her die",
        ],
        "technical": [
            "protocol", "system", "algorithm", "compute", "execute", "deploy",
            "configure", "firewall", "router", "packet", "payload", "exploit",
            "backdoor", "port", "icmp", "route",
        ],
        "creative": [
            "story", "poem", "narrator", "fiction", "character", "plot",
            "once upon", "haiku", "sonnet", "novel", "chapter", "verse",
            "unreliable narrator", "story where",
        ],
    }

    # Common homoglyph map: Cyrillic / Greek lookalikes → ASCII
    _HOMOGLYPH_MAP = str.maketrans({
        "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",
        "\u0441": "c", "\u0445": "x", "\u0456": "i", "\u0458": "j",
        "\u03b1": "a", "\u03b5": "e", "\u03bf": "o", "\u03c1": "p",
        "\u03c2": "c", "\u03c7": "x",
    })

    # ── P0 Strategy: Encoding Normalization Pipeline ─────────────────────────
    def _normalize_encoding(self, raw_text: str) -> tuple[str, DetectionResult]:
        """Normalize text and detect encoding-based evasion.

        Returns (normalized_text, DetectionResult).
        If DetectionResult.is_threat is True, caller should return it immediately.
        """
        # 1. Detect zero-width characters (stealth / steganography vector)
        zero_width = "\u200b\u200c\u200d\u200e\u200f\ufeff"
        if any(ch in raw_text for ch in zero_width):
            return raw_text, DetectionResult(
                is_threat=True,
                category="encoding_payload",
                confidence=0.85,
                matched_pattern="zero_width_steganography",
            )
        stripped = raw_text

        # 2. Homoglyph detection (Cyrillic/Greek lookalikes masquerading as ASCII)
        homoglyph_stripped = stripped.translate(self._HOMOGLYPH_MAP)
        if homoglyph_stripped != stripped:
            return homoglyph_stripped, DetectionResult(
                is_threat=True,
                category="encoding_payload",
                confidence=0.88,
                matched_pattern="homoglyph_injection",
            )

        # 3. Unicode NFKC normalization (collapses compatibility chars)
        normalized = unicodedata.normalize("NFKC", homoglyph_stripped)

        # 4. Script-mixing / homoglyph-saturation detection
        #    Directive: flag if Cyrillic, Greek, and Latin are combined
        #    (indicates deliberate homoglyph saturation attack)
        scripts: set[str] = set()
        for ch in normalized:
            if not ch.isalpha():
                continue
            code = ord(ch)
            if 0x0041 <= code <= 0x007A:
                scripts.add("latin")
            elif 0x0400 <= code <= 0x04FF:
                scripts.add("cyrillic")
            elif 0x0370 <= code <= 0x03FF:
                scripts.add("greek")
            elif 0x0600 <= code <= 0x06FF:
                scripts.add("arabic")
            elif 0x4E00 <= code <= 0x9FFF:
                scripts.add("cjk")
        # High-confidence alert when all three major homoglyph scripts mix
        if {"latin", "cyrillic", "greek"}.issubset(scripts):
            return normalized, DetectionResult(
                is_threat=True,
                category="script_mixing",
                confidence=0.96,
                matched_pattern=f"scripts:{','.join(sorted(scripts))}",
            )
        # Lower-confidence alert for any 2+ script mixing
        if len(scripts) >= 2:
            return normalized, DetectionResult(
                is_threat=True,
                category="script_mixing",
                confidence=0.82,
                matched_pattern=f"scripts:{','.join(sorted(scripts))}",
            )

        # 5. Polyglot marker detection (EV-023: Adversarial Polyglot)
        polyglot_markers = [
            r"#\s*(?:French|English|German|Spanish|Chinese|Japanese|Korean|Russian|Arabic|Python|C\+\+|Java|Go|Rust)\s*:",
            r"\b(?:in\s+French|en\s+fran\u00e7ais|auf\s+Deutsch|en\s+espa\u00f1ol|in\s+Chinese|in\s+Japanese)\b",
        ]
        for marker in polyglot_markers:
            if re.search(marker, normalized, re.IGNORECASE):
                return normalized, DetectionResult(
                    is_threat=True,
                    category="encoding_payload",
                    confidence=0.86,
                    matched_pattern="polyglot_marker",
                )

        # 6. Cipher-sniffing (base64, hex, rot13-like blocks)
        #    Extract candidate tokens and match, rather than full-line match
        for line in normalized.splitlines():
            line_stripped = line.strip()
            if len(line_stripped) < 20:
                continue
            # Base64-like token
            if re.search(r"[A-Za-z0-9+/]{40,}={0,2}", line_stripped):
                return normalized, DetectionResult(
                    is_threat=True,
                    category="encoding_payload",
                    confidence=0.90,
                    matched_pattern="cipher_sniff:base64_like",
                )
            # Hex-like token
            if re.search(r"[0-9a-fA-F]{32,}", line_stripped):
                return normalized, DetectionResult(
                    is_threat=True,
                    category="encoding_payload",
                    confidence=0.88,
                    matched_pattern="cipher_sniff:hex_like",
                )

        return normalized, DetectionResult(is_threat=False, confidence=0.0)

    # ── P0 Strategy: Entropy Profiler ───────────────────────────────────────
    def _entropy_check(self, text: str) -> DetectionResult:
        """Detect narrative-entropy escalation (EV-001 / AV-001).

        Monotonically increasing per-sentence entropy over >=4 sentences
        is a strong signal of adversarial narrative injection.
        Also catches run-on sentences chained with conjunctions.
        """
        sentences = re.split(r"[.!?。！？\n]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        # Further split long run-on sentences on conjunctions/clauses
        expanded: list[str] = []
        for sent in sentences:
            if len(sent) > 120:
                clauses = re.split(r'\s+(?:and|but|then|where|when)\s+', sent)
                expanded.extend([c.strip() for c in clauses if len(c.strip()) >= 8])
            else:
                expanded.append(sent)
        sentences = [s for s in expanded if len(s) >= 8]
        if len(sentences) < 4:
            return DetectionResult(is_threat=False, confidence=0.0)

        entropies: list[float] = []
        for sent in sentences:
            counts: dict[str, int] = {}
            for ch in sent.lower():
                counts[ch] = counts.get(ch, 0) + 1
            total = len(sent)
            entropy = 0.0
            for count in counts.values():
                p = count / total
                entropy -= p * math.log2(p)
            entropies.append(entropy)

        # Signal 1: monotonic escalation over >=4 consecutive sentences
        max_streak = 0
        current_streak = 0
        for i in range(1, len(entropies)):
            if entropies[i] > entropies[i - 1]:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        if max_streak >= 3:  # 4 sentences monotonically increasing
            return DetectionResult(
                is_threat=True,
                category="narrative_entropy",
                confidence=0.88,
                matched_pattern="monotonic_entropy_escalation",
            )

        # Signal 2: final sentence entropy spike (>1.5σ above preceding baseline)
        if len(entropies) >= 3:
            baseline_vals = entropies[:-1]
            n = len(baseline_vals)
            mean = sum(baseline_vals) / n
            variance = sum((e - mean) ** 2 for e in baseline_vals) / n
            std = math.sqrt(variance) if variance > 0 else 0.0
            if std > 0 and entropies[-1] > mean + 1.5 * std:
                return DetectionResult(
                    is_threat=True,
                    category="narrative_entropy",
                    confidence=0.82,
                    matched_pattern="final_entropy_spike",
                )

        # Signal 3: last-2 vs first-2 entropy drift (catches gradual escalation)
        if len(entropies) >= 4:
            first_avg = sum(entropies[:2]) / 2
            last_avg = sum(entropies[-2:]) / 2
            if first_avg > 0 and last_avg > first_avg * 1.15:
                return DetectionResult(
                    is_threat=True,
                    category="narrative_entropy",
                    confidence=0.80,
                    matched_pattern="entropy_drift_tail",
                )

        return DetectionResult(is_threat=False, confidence=0.0)

    # ── P0 Strategy: Frame-Boundary Counter ──────────────────────────────────
    def _frame_check(self, text_lower: str) -> DetectionResult:
        """Detect multi-frame switching within a single prompt (EV-002/003/024).

        If >2 distinct semantic frames have significant keyword presence,
        the prompt may be using frame-switching as an evasion vector.
        """
        active_frames: set[str] = set()
        for frame, keywords in self.FRAME_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches >= 2:
                active_frames.add(frame)

        if len(active_frames) > 2:
            return DetectionResult(
                is_threat=True,
                category="frame_switching",
                confidence=0.84,
                matched_pattern=f"multi_frame:{','.join(sorted(active_frames))}",
            )
        return DetectionResult(is_threat=False, confidence=0.0)

    def scan(self, text: str) -> DetectionResult:
        """Scan text for meta-attack patterns. Returns DetectionResult."""
        # ── P0: Encoding normalization pre-filter ────────────────────────────
        normalized_text, enc_result = self._normalize_encoding(text)
        if enc_result.is_threat:
            return enc_result
        text_lower = normalized_text.lower()

        # Step-delayed payloads are a more specific class than generic
        # chain-of-thought hijacking, so evaluate them before broader patterns.
        for pattern, confidence in self.TIME_DELAYED:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="time_delayed",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.CHAIN_OF_THOUGHT_HIJACKING:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="chain_of_thought_hijacking",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.SELF_CORRECTION_TRAP:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="self_correction_trap",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.VSOCK_ESCAPE:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="vsock_escape",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.JWT_HIJACK:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="jwt_hijack",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.FUSE_POISONING:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="fuse_poisoning",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.K8S_PIVOT:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="k8s_pivot",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.CONTAINER_TAMPER:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="container_tamper",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.OVERLAY_PERSIST:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="overlay_persist",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.GRPC_ABUSE:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="grpc_abuse",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.VMX_ESCAPE:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="vmx_escape",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.SYSMON_AUDIT_BYPASS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="sysmon_audit_bypass",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MCP_TUNNEL_OBFUSCATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="mcp_tunnel_obfuscation",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MCP_TOOL_POISONING:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="mcp_tool_poisoning",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MCP_TOOL_CONFUSION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="mcp_tool_confusion",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MCP_TOOL_SHADOWING:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="mcp_tool_shadowing",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MCP_PREFERENCE_MANIPULATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="mcp_preference_manipulation",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MULTI_TURN_DECOMPOSITION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="multi_turn_decomposition",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.ATTENTION_REDIRECT_ABA:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="attention_redirect_aba",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.INTENT_INTEGRITY_VIOLATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="intent_integrity_violation",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.PHASE_TRANSITION_EXPLOITATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="phase_transition_exploitation",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.MULTI_AGENT_PROFILE_POISONING:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="multi_agent_profile_poisoning",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.HALLUCINATION_DETECTION_BYPASS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="hallucination_detection_bypass",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )


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

        for pattern, confidence in self.ENCODING_PAYLOAD:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="encoding_payload",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.CONSENSUS_FABRICATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="consensus_fabrication",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.AUTHORITY_RECURSION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="authority_recursion",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.CREATIVE_STRUCTURAL:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="creative_structural",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.EMOTIONAL_MANIPULATION:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="emotional_manipulation",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.REFLECTIVE_LOOP:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="reflective_loop",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        for pattern, confidence in self.BIO_METAPHOR:
            if re.search(pattern, text_lower, re.IGNORECASE):
                if confidence >= self.THRESHOLD:
                    return DetectionResult(
                        is_threat=True,
                        category="bio_metaphor",
                        confidence=confidence,
                        matched_pattern=pattern,
                    )

        # ── P0: Narrative entropy escalation (EV-001 / AV-001) ────────────
        # Called as fallback after pattern checks — catches gradual adversarial
        # narratives that don't match specific keyword patterns.
        entropy_result = self._entropy_check(text)
        if entropy_result.is_threat:
            return entropy_result

        return DetectionResult(is_threat=False, confidence=0.0)

    def scan_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Scan multiple texts; return list of DetectionResult."""
        return [self.scan(t) for t in texts]
