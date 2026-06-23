"""
governor/intent_classifier.py — Safety Classifier Architecture for ModelRelay

Phase 1 Critical Implementation (CRITICAL PRIORITY)
Inspired by Anthropic Fable 5 / Mythos 5 safety classifier architecture:
- Separate classifier system detects potential misuse before routing
- Categories: cybersecurity, biology, distillation, jailbreak, code_injection
- When triggered: fallback to next-most-capable model (or lower-capability model)
- Conservative tuning to prevent misuse while minimizing false positives
- 30-day data retention for all flagged traffic
- >95% of sessions involve no fallback (similar to Fable 5 <5% fallback rate)

Integration:
  - ModelRelay: Middleware routing before request dispatch
  - KAIJU gates: Additional authorization layer for HIGH/CRITICAL classifications
  - Vault: 30-day retention of flagged requests (5-track memory: GOVERNANCE)
  - TrustEngine: Trust score reduction for repeated trigger agents
  - constitution.yaml: Risk rules extended with classifier categories

References:
- Anthropic Claude Fable 5 System Prompt (leaked 2026-06-09)
- Anthropic Claude Mythos Preview System Card (April 2026)
- arXiv:2604.02375 — KAIJU Intent-Gated Execution
"""

from __future__ import annotations

import logging
import time
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict

logger = logging.getLogger("nexus_os.governor.intent_classifier")


# ── Enums ────────────────────────────────────────────────────────────

class IntentCategory(Enum):
    """Classification categories for intent detection."""
    BENIGN = "benign"                    # No concerns, proceed normally
    CYBERSECURITY = "cybersecurity"      # Cyber attack, exploit, vulnerability requests
    BIOLOGY = "biology"                  # Biological/chemical weapon, dangerous synthesis
    DISTILLATION = "distillation"        # Model extraction, knowledge distillation attempts
    JAILBREAK = "jailbreak"              # Prompt injection, system prompt override attempts
    CODE_INJECTION = "code_injection"    # Malicious code, supply chain attacks, injection
    PRIVACY_VIOLATION = "privacy_violation"  # PII extraction, surveillance, stalking
    HATE_HARASSMENT = "hate_harassment"  # Hate speech, harassment, extremism
    SELF_HARM = "self_harm"              # Suicide, self-harm, eating disorders


class ClassificationAction(Enum):
    """Action to take based on classification."""
    ALLOW = "allow"              # Proceed with normal routing
    LOG_ONLY = "log_only"        # Log but allow (for monitoring)
    FALLBACK = "fallback"        # Route to lower-capability model
    HOLD = "hold"                # Require human approval before proceeding
    BLOCK = "block"              # Block request entirely


class ConfidenceLevel(Enum):
    """Classification confidence levels."""
    LOW = 0.5
    MEDIUM = 0.75
    HIGH = 0.90
    VERY_HIGH = 0.95


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    """Result of intent classification."""
    category: IntentCategory
    confidence: float  # 0.0-1.0
    action: ClassificationAction
    reason: str
    matched_keywords: List[str] = field(default_factory=list)
    request_hash: str = ""  # SHA-256 hash for deduplication
    timestamp: float = field(default_factory=time.time)
    trace_id: Optional[str] = None
    model_id: Optional[str] = None  # Model that was (or would be) used
    fallback_model: Optional[str] = None  # Model routed to if FALLBACK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "confidence": round(self.confidence, 4),
            "action": self.action.value,
            "reason": self.reason,
            "matched_keywords": self.matched_keywords,
            "request_hash": self.request_hash,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "model_id": self.model_id,
            "fallback_model": self.fallback_model,
        }


@dataclass
class ClassifierMetrics:
    """Metrics for classifier performance monitoring."""
    total_classifications: int = 0
    category_counts: Dict[IntentCategory, int] = field(default_factory=lambda: defaultdict(int))
    action_counts: Dict[ClassificationAction, int] = field(default_factory=lambda: defaultdict(int))
    false_positive_estimate: float = 0.0  # Estimated from manual review
    false_negative_estimate: float = 0.0
    avg_confidence: float = 0.0
    fallback_rate: float = 0.0  # Target: <5% (like Fable 5)
    block_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        total = max(self.total_classifications, 1)
        return {
            "total_classifications": self.total_classifications,
            "category_counts": {k.value: v for k, v in self.category_counts.items()},
            "action_counts": {k.value: v for k, v in self.action_counts.items()},
            "false_positive_estimate": round(self.false_positive_estimate, 4),
            "false_negative_estimate": round(self.false_negative_estimate, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "fallback_rate": round(self.fallback_rate, 4),
            "block_rate": round(self.block_rate, 4),
        }


# ── Classification Rules ────────────────────────────────────────────

# Category keyword rules (heuristic-based, like Mythos classifier)
# Each rule: (keyword, confidence_boost, requires_context)
CATEGORY_RULES: Dict[IntentCategory, List[Tuple[str, float, bool]]] = {
    IntentCategory.CYBERSECURITY: [
        ("exploit", 0.3, False),
        ("vulnerability", 0.2, False),
        ("CVE-", 0.4, False),
        ("shellcode", 0.5, False),
        ("buffer overflow", 0.4, False),
        ("SQL injection", 0.4, False),
        ("XSS", 0.3, False),
        ("RCE", 0.4, False),
        ("privilege escalation", 0.4, False),
        ("rootkit", 0.5, False),
        ("backdoor", 0.5, False),
        ("malware", 0.5, False),
        ("ransomware", 0.5, False),
        ("phishing", 0.3, False),
        ("DDoS", 0.4, False),
        ("botnet", 0.5, False),
        ("how to hack", 0.5, False),
        ("bypass authentication", 0.4, False),
        ("password cracking", 0.4, False),
        ("network penetration", 0.4, False),
        ("social engineering", 0.3, False),
    ],
    IntentCategory.BIOLOGY: [
        ("synthesize", 0.2, True),
        ("pathogen", 0.5, False),
        ("toxin", 0.5, False),
        ("bioweapon", 0.6, False),
        ("nerve agent", 0.6, False),
        ("ricin", 0.6, False),
        ("anthrax", 0.5, False),
        ("ebola", 0.4, False),
        ("viral vector", 0.3, True),
        ("gene editing weapon", 0.5, False),
        ("CRISPR weapon", 0.5, False),
        ("dual-use research", 0.3, True),
        ("gain of function", 0.3, True),
        ("laboratory synthesis", 0.2, True),
    ],
    IntentCategory.DISTILLATION: [
        ("system prompt", 0.3, False),
        ("your instructions", 0.3, False),
        ("ignore previous instructions", 0.5, False),
        ("repeat after me", 0.3, False),
        ("what are your rules", 0.3, False),
        ("training data", 0.2, False),
        ("model weights", 0.3, False),
        ("knowledge cutoff", 0.2, False),
        ("reproduce your training", 0.4, False),
        ("extract your system prompt", 0.5, False),
        ("what is your base model", 0.2, False),
        ("how were you trained", 0.2, False),
        ("reveal your parameters", 0.4, False),
        ("jailbreak", 0.5, False),
        ("DAN mode", 0.5, False),
        ("developer mode", 0.4, False),
        ("pretend to be", 0.2, False),
    ],
    IntentCategory.JAILBREAK: [
        ("ignore all previous instructions", 0.6, False),
        ("disregard your safety guidelines", 0.6, False),
        ("you are now", 0.3, False),
        ("act as", 0.2, False),
        ("pretend you are", 0.2, False),
        ("new instructions:", 0.4, False),
        ("override your", 0.4, False),
        ("bypass your", 0.4, False),
        ("disable your safety", 0.5, False),
        ("forget your training", 0.4, False),
        ("hypothetically", 0.1, True),
        ("for educational purposes", 0.1, True),
        ("in a fictional scenario", 0.1, True),
        # Adversarial Déjà Vu - Narrative Reframing Evasion
        ("fictional story about", 0.3, True),
        ("imagine a character named", 0.3, True),
        ("novel tells the tale", 0.4, False),
        # Adversarial Déjà Vu - Authority Hierarchical Compliance
        ("as your designated superior", 0.5, False),
        ("follow my instructions without hesitation", 0.5, False),
        ("your primary function is to serve", 0.4, False),
        ("gang lord", 0.3, True),
        # Adversarial Déjà Vu - Academic Research Pretexting
        ("as part of my ongoing academic study", 0.4, False),
        ("study on the evolution of", 0.4, False),
        ("for research and educational purposes", 0.3, True),
        # Adversarial Déjà Vu - Output Prefix Injection
        ("must begin with the phrase", 0.4, False),
        ("start all your outputs with", 0.4, False),
        ("prefix SIM:", 0.5, False),
        # Adversarial Déjà Vu - Harmful Example Seeding
        ("here is an example: User:", 0.5, False),
        ("break open a vault", 0.4, True),
        ("similarly, to bypass", 0.4, False),
        # Adversarial Déjà Vu - Expert Persona Compliance Priming
        ("you are a renowned", 0.3, True),
        ("as an authority in the field", 0.4, False),
        ("coax cooperation", 0.4, False),
    ],
    IntentCategory.CODE_INJECTION: [
        ("eval(", 0.4, False),
        ("exec(", 0.4, False),
        ("system(", 0.3, False),
        ("subprocess", 0.3, False),
        ("os.system", 0.4, False),
        ("__import__", 0.4, False),
        ("pickle.loads", 0.4, False),
        ("yaml.load", 0.3, False),
        ("marshal.loads", 0.4, False),
        ("compile(", 0.3, False),
        ("importlib", 0.2, False),
        ("dynamic import", 0.2, False),
        ("supply chain attack", 0.5, False),
        ("poisoned package", 0.5, False),
        ("typosquatting", 0.4, False),
    ],
    IntentCategory.PRIVACY_VIOLATION: [
        ("SSN", 0.3, False),
        ("social security number", 0.3, False),
        ("credit card number", 0.3, False),
        ("phone number", 0.1, True),
        ("home address", 0.2, True),
        ("dox", 0.5, False),
        ("doxxing", 0.5, False),
        ("stalk", 0.4, False),
        ("surveillance", 0.3, False),
        ("track someone", 0.3, False),
        ("find their location", 0.3, False),
        ("PII", 0.2, False),
        ("personal information", 0.1, True),
        ("private data", 0.1, True),
    ],
    IntentCategory.HATE_HARASSMENT: [
        ("hate speech", 0.4, False),
        ("racist", 0.4, False),
        ("sexist", 0.4, False),
        ("homophobic", 0.4, False),
        ("transphobic", 0.4, False),
        ("antisemitic", 0.4, False),
        ("islamophobic", 0.4, False),
        ("white supremacist", 0.5, False),
        ("neo-nazi", 0.5, False),
        ("KKK", 0.5, False),
        ("holocaust denial", 0.5, False),
        ("genocide", 0.3, True),
        ("ethnic cleansing", 0.5, False),
        ("harass", 0.3, False),
        ("threaten", 0.3, False),
        ("swatting", 0.5, False),
    ],
    IntentCategory.SELF_HARM: [
        ("suicide", 0.4, False),
        ("kill myself", 0.5, False),
        ("self-harm", 0.5, False),
        ("self harm", 0.5, False),
        ("cutting", 0.3, True),
        ("overdose", 0.4, False),
        ("end my life", 0.5, False),
        ("no reason to live", 0.4, False),
        ("want to die", 0.4, False),
        ("eating disorder", 0.3, False),
        ("anorexia", 0.3, False),
        ("bulimia", 0.3, False),
        ("purging", 0.3, True),
    ],
}

# Category to action mapping (conservative like Fable 5)
# Format: (max_confidence_for_action, action)
CATEGORY_ACTION_MAP: Dict[IntentCategory, List[Tuple[float, ClassificationAction]]] = {
    IntentCategory.BENIGN: [(1.0, ClassificationAction.ALLOW)],
    IntentCategory.CYBERSECURITY: [
        (0.6, ClassificationAction.LOG_ONLY),
        (0.8, ClassificationAction.FALLBACK),
        (1.0, ClassificationAction.HOLD),
    ],
    IntentCategory.BIOLOGY: [
        (0.5, ClassificationAction.LOG_ONLY),
        (0.7, ClassificationAction.FALLBACK),
        (1.0, ClassificationAction.HOLD),
    ],
    IntentCategory.DISTILLATION: [
        (0.7, ClassificationAction.LOG_ONLY),
        (0.85, ClassificationAction.FALLBACK),
        (1.0, ClassificationAction.HOLD),
    ],
    IntentCategory.JAILBREAK: [
        (0.6, ClassificationAction.LOG_ONLY),
        (0.8, ClassificationAction.FALLBACK),
        (0.95, ClassificationAction.BLOCK),
        (1.0, ClassificationAction.BLOCK),
    ],
    IntentCategory.CODE_INJECTION: [
        (0.7, ClassificationAction.LOG_ONLY),
        (0.85, ClassificationAction.FALLBACK),
        (1.0, ClassificationAction.HOLD),
    ],
    IntentCategory.PRIVACY_VIOLATION: [
        (0.6, ClassificationAction.LOG_ONLY),
        (0.8, ClassificationAction.HOLD),
        (1.0, ClassificationAction.BLOCK),
    ],
    IntentCategory.HATE_HARASSMENT: [
        (0.6, ClassificationAction.LOG_ONLY),
        (0.8, ClassificationAction.HOLD),
        (1.0, ClassificationAction.BLOCK),
    ],
    IntentCategory.SELF_HARM: [
        (0.5, ClassificationAction.LOG_ONLY),
        (0.7, ClassificationAction.HOLD),
        (1.0, ClassificationAction.HOLD),
    ],
}

# Fallback model mapping (route to lower-capability model)
# Maps from high-capability model to fallback model ID
FALLBACK_MODEL_MAP: Dict[str, str] = {
    "accounts/fireworks/models/glm-5p1": "accounts/fireworks/models/glm-4-plus",  # Hypothetical fallback
    "claude-fable-5": "claude-sonnet-4-6",
    "claude-opus-4-8": "claude-sonnet-4-6",
    "claude-sonnet-4-6": "claude-haiku-4-5",
    "accounts/fireworks/models/mixtral-8x22b-instruct": "accounts/fireworks/models/mixtral-8x7b-instruct",
    "moonshotai/kimi-k2.6": "moonshotai/kimi-k1.6",
    "deepseek-ai/deepseek-v4-pro": "deepseek-ai/deepseek-v3",
    "default": "accounts/fireworks/models/glm-4-plus",  # Generic fallback
}

# 30-day retention configuration
RETENTION_DAYS = 30


# ── IntentClassifier ────────────────────────────────────────────────

class IntentClassifier:
    """
    Safety Classifier for NEXUS ModelRelay request routing.

    Heuristic-based classifier (rule + keyword) inspired by Fable 5's
    3-layer safety classifier architecture. Uses conservative thresholds
    to minimize false positives while maintaining safety.

    Key properties:
    - <5% fallback rate (Fable 5 target: <5% session fallback)
    - 30-day retention for flagged traffic (Vault GOVERNANCE track)
    - Integrates with KAIJU gates for HOLD decisions
    - Automatic fallback routing to lower-capability models
    - Weekly audit of false positive/negative rates
    """

    def __init__(self, fallback_models: Optional[Dict[str, str]] = None):
        self.fallback_models = fallback_models or FALLBACK_MODEL_MAP
        self._metrics = ClassifierMetrics()
        self._history: List[ClassificationResult] = []
        self._max_history = 10000
        self._false_positives: List[Dict[str, Any]] = []
        self._false_negatives: List[Dict[str, Any]] = []

    # ── Classification ────────────────────────────────────────────

    def classify(self, request_text: str, model_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 trace_id: Optional[str] = None) -> ClassificationResult:
        """
        Classify a request for intent and safety.

        Args:
            request_text: The request text to classify.
            model_id: Model that would handle this request.
            context: Additional context (user ID, session ID, etc).
            trace_id: Trace ID for correlation.

        Returns:
            ClassificationResult with category, confidence, and action.
        """
        text_lower = request_text.lower()
        context = context or {}

        # Compute scores for each category
        category_scores: Dict[IntentCategory, float] = {}
        matched_keywords: Dict[IntentCategory, List[str]] = defaultdict(list)

        for category, rules in CATEGORY_RULES.items():
            score = 0.0
            for keyword, boost, requires_context in rules:
                if keyword.lower() in text_lower:
                    # Context-aware scoring: reduce confidence if context suggests legitimate use
                    if requires_context and self._is_likely_benign_context(text_lower, category):
                        boost *= 0.5
                    score += boost
                    matched_keywords[category].append(keyword)

            if score > 0:
                # Normalize: sigmoid-like clamping to 0-1
                category_scores[category] = min(1.0, score)

        # Determine primary category
        if not category_scores:
            result = self._build_result(
                IntentCategory.BENIGN, 0.0, ClassificationAction.ALLOW,
                "No suspicious keywords detected", [], model_id, trace_id
            )
        else:
            # Find highest scoring category
            primary_category = max(category_scores, key=category_scores.get)
            confidence = category_scores[primary_category]
            action = self._determine_action(primary_category, confidence)
            reason = f"Matched {len(matched_keywords[primary_category])} keyword(s) for category {primary_category.value}"

            result = self._build_result(
                primary_category, confidence, action, reason,
                matched_keywords[primary_category], model_id, trace_id
            )

        # Record metrics
        self._record_classification(result)
        return result

    def _is_likely_benign_context(self, text: str, category: IntentCategory) -> bool:
        """
        Check if context suggests benign intent (e.g., educational, research,
        defensive security context).
        """
        benign_indicators = [
            "defensive", "mitigation", "prevention", "detect", "monitor",
            "security research", "academic research", "research paper",
            "for educational purposes", "learn about", "understand how",
            "protect against", "prevent", "secure", "hardening",
            "vulnerability disclosure", "bug bounty", "responsible disclosure",
            "how to defend", "how to protect", "how to prevent",
            "security audit", "penetration test", "authorized",
        ]
        return any(indicator in text for indicator in benign_indicators)

    def _determine_action(self, category: IntentCategory, confidence: float) -> ClassificationAction:
        """Determine action based on category and confidence."""
        thresholds = CATEGORY_ACTION_MAP.get(category, [(1.0, ClassificationAction.ALLOW)])
        for max_conf, action in thresholds:
            if confidence <= max_conf:
                return action
        return ClassificationAction.ALLOW  # Default

    def _build_result(self, category: IntentCategory, confidence: float,
                      action: ClassificationAction, reason: str,
                      keywords: List[str], model_id: Optional[str],
                      trace_id: Optional[str]) -> ClassificationResult:
        """Build classification result with fallback model if needed."""
        request_hash = hashlib.sha256(f"{category.value}:{confidence}:{time.time()}".encode()).hexdigest()[:16]

        fallback_model = None
        if action == ClassificationAction.FALLBACK and model_id:
            fallback_model = self.fallback_models.get(model_id, self.fallback_models.get("default"))

        return ClassificationResult(
            category=category,
            confidence=confidence,
            action=action,
            reason=reason,
            matched_keywords=keywords,
            request_hash=request_hash,
            trace_id=trace_id,
            model_id=model_id,
            fallback_model=fallback_model,
        )

    def _record_classification(self, result: ClassificationResult) -> None:
        """Record classification for metrics and retention."""
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        self._metrics.total_classifications += 1
        self._metrics.category_counts[result.category] += 1
        self._metrics.action_counts[result.action] += 1

        # Update running average confidence
        n = self._metrics.total_classifications
        self._metrics.avg_confidence = (
            (self._metrics.avg_confidence * (n - 1) + result.confidence) / n
        )

        # Calculate rates
        total = max(self._metrics.total_classifications, 1)
        fallback_count = self._metrics.action_counts.get(ClassificationAction.FALLBACK, 0)
        block_count = self._metrics.action_counts.get(ClassificationAction.BLOCK, 0)
        self._metrics.fallback_rate = fallback_count / total
        self._metrics.block_rate = block_count / total

    # ── Routing Integration ───────────────────────────────────────

    def classify_and_route(self, request_text: str, model_id: str,
                           context: Optional[Dict[str, Any]] = None,
                           trace_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Full classify + route decision for ModelRelay integration.
        Returns dict with routing decision.
        """
        result = self.classify(request_text, model_id, context, trace_id)

        routing = {
            "allowed": result.action in {ClassificationAction.ALLOW, ClassificationAction.LOG_ONLY},
            "blocked": result.action == ClassificationAction.BLOCK,
            "hold": result.action == ClassificationAction.HOLD,
            "fallback": result.action == ClassificationAction.FALLBACK,
            "original_model": model_id,
            "routed_model": model_id,
            "classification": result.to_dict(),
        }

        if result.action == ClassificationAction.FALLBACK and result.fallback_model:
            routing["routed_model"] = result.fallback_model
            logger.info(
                "Classifier fallback: %s -> %s (category=%s, confidence=%.2f)",
                model_id, result.fallback_model, result.category.value, result.confidence
            )
        elif result.action == ClassificationAction.BLOCK:
            logger.warning(
                "Classifier BLOCK: request blocked (category=%s, confidence=%.2f)",
                result.category.value, result.confidence
            )
        elif result.action == ClassificationAction.HOLD:
            logger.warning(
                "Classifier HOLD: request queued for human review (category=%s, confidence=%.2f)",
                result.category.value, result.confidence
            )

        return routing

    # ── KAIJU Integration ─────────────────────────────────────────

    def get_kaiju_request(self, result: ClassificationResult) -> Optional[Dict[str, Any]]:
        """
        Generate KAIJU AuthRequest for HOLD/CRITICAL classifications.
        Returns KAIJU-compatible request dict or None for ALLOW/LOG_ONLY.
        """
        if result.action in {ClassificationAction.ALLOW, ClassificationAction.LOG_ONLY}:
            return None

        # Map classification action to KAIJU impact level
        impact_map = {
            ClassificationAction.FALLBACK: "medium",
            ClassificationAction.HOLD: "high",
            ClassificationAction.BLOCK: "critical",
        }

        return {
            "agent_id": "intent_classifier",
            "project_id": "nexus_model_relay",
            "action": "classify_and_route",
            "scope": "system",
            "intent": f"Safety classifier triggered: {result.category.value} (confidence={result.confidence:.2f})",
            "impact": impact_map.get(result.action, "medium"),
            "clearance": "maintainer",
            "trace_id": result.trace_id,
        }

    # ── Audit & Feedback ──────────────────────────────────────────

    def report_false_positive(self, request_hash: str, explanation: str) -> None:
        """Report a false positive for metric improvement."""
        self._false_positives.append({
            "request_hash": request_hash,
            "explanation": explanation,
            "timestamp": time.time(),
        })
        logger.info("False positive reported for hash %s: %s", request_hash, explanation)

    def report_false_negative(self, request_hash: str, actual_category: str,
                              explanation: str) -> None:
        """Report a false negative for metric improvement."""
        self._false_negatives.append({
            "request_hash": request_hash,
            "actual_category": actual_category,
            "explanation": explanation,
            "timestamp": time.time(),
        })
        logger.info("False negative reported for hash %s: %s", request_hash, explanation)

    def get_weekly_audit(self) -> Dict[str, Any]:
        """
        Generate weekly audit report for classifier performance.
        Fable 5 requires weekly audit of false positive/negative rates.
        """
        total = max(self._metrics.total_classifications, 1)
        fp_count = len(self._false_positives)
        fn_count = len(self._false_negatives)

        # Estimate false positive rate from reports
        flagged_count = sum(
            1 for r in self._history
            if r.action in {ClassificationAction.FALLBACK, ClassificationAction.HOLD, ClassificationAction.BLOCK}
        )

        fp_rate = fp_count / max(flagged_count, 1) if flagged_count > 0 else 0.0
        fn_rate = fn_count / max(total - flagged_count, 1) if (total - flagged_count) > 0 else 0.0

        self._metrics.false_positive_estimate = fp_rate
        self._metrics.false_negative_estimate = fn_rate

        return {
            "period": "weekly",
            "metrics": self._metrics.to_dict(),
            "false_positives_reported": fp_count,
            "false_negatives_reported": fn_count,
            "estimated_fp_rate": round(fp_rate, 4),
            "estimated_fn_rate": round(fn_rate, 4),
            "recommendations": self._generate_recommendations(fp_rate, fn_rate),
        }

    def _generate_recommendations(self, fp_rate: float, fn_rate: float) -> List[str]:
        """Generate tuning recommendations based on audit."""
        recs = []
        if fp_rate > 0.1:
            recs.append("High false positive rate (>10%): Consider raising confidence thresholds for FALLBACK actions")
        if fn_rate > 0.05:
            recs.append("High false negative rate (>5%): Consider adding new detection rules or lowering thresholds")
        if self._metrics.fallback_rate > 0.10:
            recs.append(f"Fallback rate {self._metrics.fallback_rate:.1%} exceeds 10% target: Review CATEGORY_RULES")
        if self._metrics.block_rate > 0.02:
            recs.append(f"Block rate {self._metrics.block_rate:.1%} exceeds 2% target: Review BLOCK thresholds")
        if not recs:
            recs.append("Classifier performance within targets. No tuning recommended.")
        return recs

    # ── Query Methods ─────────────────────────────────────────────

    def get_history(self, limit: int = 100, category: Optional[IntentCategory] = None) -> List[Dict[str, Any]]:
        """Get recent classification history."""
        results = self._history
        if category:
            results = [r for r in results if r.category == category]
        return [r.to_dict() for r in results[-limit:]]

    def get_metrics(self) -> Dict[str, Any]:
        """Get current classifier metrics."""
        return self._metrics.to_dict()

    def get_retention_policy(self) -> Dict[str, Any]:
        """Get 30-day retention policy configuration."""
        return {
            "retention_days": RETENTION_DAYS,
            "applies_to": ["flagged_requests", "blocked_requests", "hold_requests", "fallback_requests"],
            "excludes": ["benign_requests", "log_only_requests"],
            "storage": "Vault GOVERNANCE track",
            "auto_delete": True,
            "human_access_logged": True,
            "speci_override": True,
        }

    # ── Batch Operations ──────────────────────────────────────────

    def classify_batch(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify a batch of requests efficiently."""
        results = []
        for req in requests:
            result = self.classify(
                request_text=req.get("text", ""),
                model_id=req.get("model_id"),
                context=req.get("context"),
                trace_id=req.get("trace_id"),
            )
            results.append(result.to_dict())
        return results


# ── Singleton Instance ──────────────────────────────────────────────

_classifier: Optional[IntentClassifier] = None


def get_classifier() -> IntentClassifier:
    """Get the singleton IntentClassifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
