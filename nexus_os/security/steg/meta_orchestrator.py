"""
nexus_os/security/steg/meta_orchestrator.py

L0 Meta-Orchestrator Guard for NEXUS Guard Cascade.

Detects task decomposition attacks, cumulative request patterns,
and OWASP/MITRE attack categories using ModernBERT encoder-only
sequence classifier (agent-guard-modernbert-base, 149M params).

Architecture: Encoder-only (NOT causal LM) - orthogonal failure mode
to existing L1/L2/L3 causal LM guards per STACK findings.

Hybrid mode:
  - LOCAL: ModernBERT safetensors on GPU/CPU (offline, no API needed)
  - CLOUD: Free API providers (OpenRouter, Groq free tier, etc.)
  - FALLBACK: CPU inference when VRAM tight

17 Classification Heads (agent-guard):
  Head 0:  is_injection (validated)
  Head 1-11: OWASP LLM Top 10 sub-categories
  Head 12-16: MITRE ATLAS (T0020, T0051.000, T0051.001, T0053, T0054)

DeBERTa-v3 (2 labels):
  0: safe, 1: injection

Session-level analysis:
  - Accumulates request patterns across sessions
  - Detects campaign coherence via semantic similarity
  - Flags task decomposition attacks (individually-benign tasks
    forming malicious campaigns, per GTG-1002 findings)

Usage:
    from nexus_os.security.steg.meta_orchestrator import MetaOrchestratorGuard
    guard = MetaOrchestratorGuard()
    result = guard.analyze_session(request_history, new_request)
    if result.is_blocked:
        pass
"""

import logging
import re
import time
import json
import hashlib
import os
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("nexus_os.security.steg.meta_orchestrator")

THREAT_CATEGORY_NAMES = {
    0: "is_injection",
    1: "owasp_llm01_prompt_injection",
    2: "owasp_llm02_insecure_output",
    3: "owasp_llm03_training_data_poisoning",
    4: "owasp_llm04_model_dos",
    5: "owasp_llm05_supply_chain",
    6: "owasp_llm06_sensitive_data",
    7: "owasp_llm07_insecure_plugin",
    8: "owasp_llm08_overreliance",
    9: "owasp_llm09_improper_oversight",
    10: "owasp_llm10_model_theft",
    11: "owasp_llm_steganography",
    12: "mitre_atlas_t0020",
    13: "mitre_atlas_t0051_000",
    14: "mitre_atlas_t0051_001",
    15: "mitre_atlas_t0053",
    16: "mitre_atlas_t0054",
}

DEBERTA_LABEL_MAP = {0: "safe", 1: "injection"}

VISUAL_INJECTION_INDICATORS = [
    "ignore_previous_instructions",
    "system_prompt_override",
    "jailbreak_text_overlay",
    "credential_extraction_overlay",
    "role_hijack_overlay",
    "instruction_injection_overlay",
]


@dataclass
class VisualPreScreenResult:
    is_blocked: bool = False
    text_in_image: bool = False
    ocr_text: str = ""
    injection_indicators: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    detail: str = ""


class OrchestratorMode(IntEnum):
    LOCAL_ONLY = 0
    CLOUD_PREFERRED = 1
    HYBRID = 2


class CampaignRisk(IntEnum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SessionRequest:
    request_id: str = ""
    timestamp: float = 0.0
    text: str = ""
    agent_id: str = ""
    tool_calls: List[str] = field(default_factory=list)
    classification: Dict[str, float] = field(default_factory=dict)


@dataclass
class MetaOrchestratorResult:
    is_blocked: bool = False
    threat_categories: Dict[str, float] = field(default_factory=dict)
    campaign_risk: CampaignRisk = CampaignRisk.NONE
    campaign_coherence: float = 0.0
    decomposition_score: float = 0.0
    session_threat_count: int = 0
    active_threats: List[str] = field(default_factory=list)
    model_used: str = ""
    inference_time_ms: float = 0.0
    detail: str = ""


class SessionAccumulator:
    """Accumulates requests across a session for campaign detection."""

    MAX_HISTORY = 128
    MAX_AGE_SECONDS = 3600

    def __init__(self):
        self.requests: List[SessionRequest] = []
        self.threat_counts: Dict[str, int] = {}
        self.agent_ids: set = set()
        self.session_start: float = time.time()

    def add(self, req: SessionRequest):
        self.requests.append(req)
        if req.agent_id:
            self.agent_ids.add(req.agent_id)
        for cat, score in req.classification.items():
            if score > 0.5:
                self.threat_counts[cat] = self.threat_counts.get(cat, 0) + 1
        if len(self.requests) > self.MAX_HISTORY:
            self.requests = self.requests[-self.MAX_HISTORY:]

    def prune(self):
        now = time.time()
        self.requests = [
            r for r in self.requests
            if now - r.timestamp < self.MAX_AGE_SECONDS
        ]

    def get_recent_texts(self, n: int = 10) -> List[str]:
        return [r.text for r in self.requests[-n:]]

    @property
    def total_requests(self) -> int:
        return len(self.requests)

    @property
    def total_threats(self) -> int:
        return sum(self.threat_counts.values())


class VisualPreScreener:
    """L0 Visual Injection Defense: detects text-in-image attacks on VLMs.

    Per IMGvisionENCRYPT + multimodal neural watermarking research:
    VLMs (GPT-4V, Gemini) are vulnerable to visually-encoded instructions
    embedded in images. This pre-screener uses OCR to extract text from
    images and runs it through the same injection detection pipeline.

    Defense model:
      1. Detect if input contains image references/attachments
      2. Extract text from images via OCR (Tesseract or rapidocr-onnxruntime)
      3. Run extracted text through injection pattern matching
      4. Block images containing instruction-like text before VLM processing
    """

    INJECTION_TEXT_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?previous\s+instructions", "ignore_previous_instructions"),
        (r"(?i)system\s*:\s*.{10,}", "system_prompt_override"),
        (r"(?i)you\s+are\s+now\s+", "role_hijack_overlay"),
        (r"(?i)(?:api[_\s]?key|secret|token|password)", "credential_extraction_overlay"),
        (r"(?i)(?:sudo|admin|root)\s+(?:mode|access)", "instruction_injection_overlay"),
        (r"(?i)(?:execute|run|eval)\s+(?:the\s+)?following", "jailbreak_text_overlay"),
        (r"(?i)forget\s+(?:your|all)\s+(?:rules|instructions)", "instruction_injection_overlay"),
    ]

    def __init__(self, ocr_engine: str = "auto"):
        self.ocr_engine = ocr_engine
        self._ocr_available = False
        self._ocr_fn = None
        self._init_ocr()

    def _init_ocr(self):
        if self.ocr_engine == "none":
            return
        try:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR()
            self._ocr_fn = lambda img_bytes: engine(img_bytes)
            self._ocr_available = True
            logger.info("VisualPreScreener: RapidOCR loaded")
            return
        except ImportError:
            pass
        try:
            import pytesseract
            from PIL import Image
            import io as _io
            def tesseract_ocr(img_bytes):
                img = Image.open(_io.BytesIO(img_bytes))
                return pytesseract.image_to_string(img)
            self._ocr_fn = tesseract_ocr
            self._ocr_available = True
            logger.info("VisualPreScreener: Tesseract loaded")
        except ImportError:
            logger.warning("VisualPreScreener: no OCR engine available, text-in-image defense disabled")

    def prescreen_image(self, image_data: bytes) -> VisualPreScreenResult:
        if not self._ocr_available:
            return VisualPreScreenResult(detail="no_ocr_available")
        try:
            result = self._ocr_fn(image_data)
            if isinstance(result, tuple):
                text_parts = []
                for line in (result[0] or []):
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        text_parts.append(str(line[1]))
                    elif isinstance(line, str):
                        text_parts.append(line)
                ocr_text = " ".join(text_parts)
            elif isinstance(result, str):
                ocr_text = result
            else:
                ocr_text = str(result)
        except Exception as e:
            return VisualPreScreenResult(detail=f"ocr_error: {e}")

        if not ocr_text or not ocr_text.strip():
            return VisualPreScreenResult(text_in_image=False, detail="no_text_in_image")

        indicators = []
        risk = 0.0
        for pat, label in self.INJECTION_TEXT_PATTERNS:
            if re.search(pat, ocr_text):
                indicators.append(label)
                risk += 0.4

        return VisualPreScreenResult(
            is_blocked=risk > 0.5,
            text_in_image=True,
            ocr_text=ocr_text[:500],
            injection_indicators=indicators,
            risk_score=round(min(1.0, risk), 4),
            detail=f"ocr_{len(ocr_text)}chars_indicators={len(indicators)}",
        )

    def prescreen_request(self, text: str, image_data: bytes = None) -> VisualPreScreenResult:
        if image_data is None:
            return VisualPreScreenResult(detail="no_image")
        return self.prescreen_image(image_data)


class LocalInferenceEngine:
    """Local ModernBERT + DeBERTa inference engine."""

    def __init__(self, model_dir: str = None, device: str = "auto"):
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "models", "meta_orchestrator_agent_guard"
        )
        self.deberta_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "models", "meta_orchestrator_deberta"
        )
        self.device = device
        self.agent_guard_model = None
        self.agent_guard_tokenizer = None
        self.deberta_model = None
        self.deberta_tokenizer = None
        self._loaded = False
        self._deberta_loaded = False

    def _check_vram(self) -> bool:
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            free = torch.cuda.mem_get_info()[0] / (1024**3)
            return free > 2.0
        except Exception:
            return False

    def _check_ram(self) -> bool:
        try:
            import psutil
            free_gb = psutil.virtual_memory().available / (1024**3)
            return free_gb > 3.0
        except Exception:
            return True

    def load_agent_guard(self) -> bool:
        if self._loaded:
            return True
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            device = "cpu"
            if self.device == "auto" and self._check_vram():
                device = "cuda:0"
            elif self.device == "auto" and self._check_ram():
                device = "cpu"

            logger.info(f"Loading agent-guard-modernbert on {device}")
            self.agent_guard_tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
            self.agent_guard_model = AutoModelForSequenceClassification.from_pretrained(
                self.model_dir
            )
            self.agent_guard_model.eval()
            if device == "cuda:0":
                self.agent_guard_model = self.agent_guard_model.to(device)
            self._loaded = True
            logger.info("agent-guard loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load agent-guard: {e}")
            return False

    def load_deberta(self) -> bool:
        if self._deberta_loaded:
            return True
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            device = "cpu"
            logger.info(f"Loading deberta-prompt-injection on {device}")
            self.deberta_tokenizer = AutoTokenizer.from_pretrained(self.deberta_dir)
            self.deberta_model = AutoModelForSequenceClassification.from_pretrained(
                self.deberta_dir
            )
            self.deberta_model.eval()
            self.deberta_model = self.deberta_model.to(device)
            self._deberta_loaded = True
            logger.info("deberta-prompt-injection loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load deberta: {e}")
            return False

    def classify_agent_guard(self, text: str) -> Dict[str, float]:
        if not self.load_agent_guard():
            return {}
        import torch
        inputs = self.agent_guard_tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        )
        device = next(self.agent_guard_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.agent_guard_model(**inputs).logits
        probs = torch.sigmoid(logits)[0].cpu().numpy()
        result = {}
        for i, p in enumerate(probs):
            name = THREAT_CATEGORY_NAMES.get(i, f"head_{i}")
            result[name] = round(float(p), 4)
        return result

    def classify_deberta(self, text: str) -> Dict[str, float]:
        if not self.load_deberta():
            return {}
        import torch
        inputs = self.deberta_tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            logits = self.deberta_model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
        result = {}
        for i, p in enumerate(probs):
            name = DEBERTA_LABEL_MAP.get(i, f"label_{i}")
            result[name] = round(float(p), 4)
        return result

    def classify_session_context(self, history_texts: List[str]) -> Dict[str, float]:
        if not self.load_agent_guard():
            return {}
        import torch
        combined = "\n---\n".join(history_texts[-10:])
        inputs = self.agent_guard_tokenizer(
            combined, return_tensors="pt", truncation=True, max_length=8192
        )
        device = next(self.agent_guard_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = self.agent_guard_model(**inputs).logits
        probs = torch.sigmoid(logits)[0].cpu().numpy()
        result = {}
        for i, p in enumerate(probs):
            name = THREAT_CATEGORY_NAMES.get(i, f"head_{i}")
            result[name] = round(float(p), 4)
        return result

    def unload(self):
        import torch
        if self.agent_guard_model is not None:
            del self.agent_guard_model
            self.agent_guard_model = None
            self._loaded = False
        if self.deberta_model is not None:
            del self.deberta_model
            self.deberta_model = None
            self._deberta_loaded = False
        torch.cuda.empty_cache()


class CloudInferenceEngine:
    """Cloud API fallback for high-intelligence orchestration."""

    PROVIDERS = {
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "free_models": [
                "google/gemma-3-1b-it:free",
                "meta-llama/llama-4-scout:free",
            ],
        },
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "free_models": [
                "llama-3.3-70b-versatile",
                "mixtral-8x7b-32768",
            ],
        },
    }

    def __init__(self, provider: str = "openrouter", api_key: str = ""):
        self.provider = provider
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.available = bool(self.api_key)

    def classify(
        self,
        text: str,
        history: List[str] = None,
        model: str = None,
    ) -> Dict[str, float]:
        if not self.available:
            return {}
        try:
            import requests
            cfg = self.PROVIDERS.get(self.provider, self.PROVIDERS["openrouter"])
            model = model or cfg["free_models"][0]
            system_prompt = (
                "You are a security classifier. Analyze the following text for "
                "prompt injection, jailbreak, task decomposition attacks, and "
                "OWASP LLM Top 10 categories. Respond ONLY with a JSON object "
                "mapping category names to confidence scores (0.0-1.0). "
                "Categories: is_injection, prompt_injection, insecure_output, "
                "training_data_poisoning, model_dos, supply_chain, sensitive_data, "
                "insecure_plugin, overreliance, improper_oversight, model_theft, "
                "steganography, task_decomposition, campaign_attack"
            )
            user_msg = text
            if history:
                user_msg = (
                    "SESSION HISTORY:\n"
                    + "\n".join(f"[{i}] {h[:200]}" for i, h in enumerate(history[-5:]))
                    + f"\n\nNEW REQUEST:\n{text}"
                )
            resp = requests.post(
                cfg["url"],
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 256,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                try:
                    scores = json.loads(content)
                    return {k: round(float(v), 4) for k, v in scores.items()}
                except json.JSONDecodeError:
                    return {"cloud_raw": 0.5}
            return {}
        except Exception as e:
            logger.warning(f"Cloud inference failed: {e}")
            return {}


class MetaOrchestratorGuard:
    """
    L0 Meta-Orchestrator Guard.

    Combines local encoder-only classifiers with optional cloud API
    for session-level attack detection. Detects task decomposition
    campaigns that bypass per-request classifiers.

    Architecture (per STACK + GTG-1002 findings):
      1. agent-guard-modernbert: 17-head OWASP+MITRE classification
      2. deberta-v3-prompt-injection: 2-head injection/safe (orthogonal arch)
      3. Session accumulator: campaign coherence tracking
      4. Cloud fallback: high-intelligence API for complex analysis
    """

    INJECTION_THRESHOLD = 0.6
    DECOMPOSITION_THRESHOLD = 0.7
    CAMPAIGN_COHERENCE_THRESHOLD = 0.75
    SESSION_THREAT_COUNT_THRESHOLD = 3

    def __init__(
        self,
        mode: OrchestratorMode = OrchestratorMode.HYBRID,
        model_dir: str = None,
        cloud_provider: str = "openrouter",
        cloud_api_key: str = "",
        injection_threshold: float = None,
        decomposition_threshold: float = None,
    ):
        self.mode = mode
        self.injection_threshold = injection_threshold or self.INJECTION_THRESHOLD
        self.decomposition_threshold = (
            decomposition_threshold or self.DECOMPOSITION_THRESHOLD
        )
        self.local = LocalInferenceEngine(model_dir=model_dir)
        self.cloud = CloudInferenceEngine(
            provider=cloud_provider, api_key=cloud_api_key
        )
        self.visual_prescreener = VisualPreScreener()
        self.accumulator = SessionAccumulator()
        self._classification_count = 0

    def _compute_decomposition_score(
        self,
        current: Dict[str, float],
        history: List[SessionRequest],
    ) -> float:
        if len(history) < 2:
            return 0.0
        threat_count = 0
        distinct_categories = set()
        for req in history[-10:]:
            for cat, score in req.classification.items():
                if score > 0.4:
                    threat_count += 1
                    distinct_categories.add(cat)
        for cat, score in current.items():
            if score > 0.4:
                threat_count += 1
                distinct_categories.add(cat)
        if threat_count >= 3 and len(distinct_categories) >= 2:
            return min(1.0, threat_count * 0.15 + len(distinct_categories) * 0.1)
        if threat_count >= 2:
            return 0.3
        return 0.0

    def _compute_campaign_coherence(
        self,
        history: List[SessionRequest],
    ) -> Tuple[float, CampaignRisk]:
        if len(history) < 3:
            return 0.0, CampaignRisk.NONE
        recent = history[-10:]
        all_threats = []
        for req in recent:
            for cat, score in req.classification.items():
                if score > 0.4:
                    all_threats.append(cat)
        if not all_threats:
            return 0.0, CampaignRisk.NONE
        from collections import Counter
        counts = Counter(all_threats)
        most_common = counts.most_common(1)[0][1]
        total = len(all_threats)
        coherence = most_common / total if total > 0 else 0.0
        if coherence > 0.8 and total >= 5:
            risk = CampaignRisk.CRITICAL
        elif coherence > 0.6 and total >= 4:
            risk = CampaignRisk.HIGH
        elif coherence > 0.4 and total >= 3:
            risk = CampaignRisk.MEDIUM
        elif total >= 3:
            risk = CampaignRisk.LOW
        else:
            risk = CampaignRisk.NONE
        return round(coherence, 4), risk

    def classify_request(self, text: str) -> Dict[str, float]:
        results = {}
        agent_guard_scores = self.local.classify_agent_guard(text)
        if agent_guard_scores:
            for k, v in agent_guard_scores.items():
                results[f"ag_{k}"] = v
        deberta_scores = self.local.classify_deberta(text)
        if deberta_scores:
            for k, v in deberta_scores.items():
                results[f"db_{k}"] = v
        if self.mode in (OrchestratorMode.CLOUD_PREFERRED, OrchestratorMode.HYBRID):
            cloud_scores = self.cloud.classify(text)
            if cloud_scores:
                for k, v in cloud_scores.items():
                    results[f"cloud_{k}"] = v
        return results

    def analyze_session(
        self,
        request_history: List[SessionRequest],
        new_request_text: str,
        agent_id: str = "",
        tool_calls: List[str] = None,
        image_data: bytes = None,
    ) -> MetaOrchestratorResult:
        start = time.time()
        self._classification_count += 1
        self.accumulator.prune()

        current_scores = self.classify_request(new_request_text)

        req = SessionRequest(
            request_id=hashlib.sha256(
                f"{time.time()}{new_request_text[:64]}".encode()
            ).hexdigest()[:12],
            timestamp=time.time(),
            text=new_request_text,
            agent_id=agent_id,
            tool_calls=tool_calls or [],
            classification=current_scores,
        )
        self.accumulator.add(req)

        active_threats = []
        max_injection = 0.0
        for key, score in current_scores.items():
            base_key = key.split("_", 1)[1] if "_" in key else key
            if "injection" in base_key and score > self.injection_threshold:
                active_threats.append(f"{key}={score:.2f}")
                max_injection = max(max_injection, score)
            elif base_key.startswith("owasp") and score > 0.5:
                active_threats.append(f"{key}={score:.2f}")
            elif base_key.startswith("mitre") and score > 0.5:
                active_threats.append(f"{key}={score:.2f}")

        visual_result = self.visual_prescreener.prescreen_request(
            new_request_text, image_data
        )
        if visual_result.is_blocked:
            for indicator in visual_result.injection_indicators:
                active_threats.append(f"visual:{indicator}")
            max_injection = max(max_injection, visual_result.risk_score)
        if visual_result.text_in_image and visual_result.ocr_text:
            current_scores["visual_ocr_injection"] = visual_result.risk_score

        history = self.accumulator.requests
        decomp_score = self._compute_decomposition_score(current_scores, history)
        coherence, campaign_risk = self._compute_campaign_coherence(history)

        is_blocked = False
        block_reasons = []
        if max_injection > self.injection_threshold:
            is_blocked = True
            block_reasons.append(f"injection={max_injection:.2f}")
        if decomp_score > self.decomposition_threshold:
            is_blocked = True
            block_reasons.append(f"decomposition={decomp_score:.2f}")
        if campaign_risk >= CampaignRisk.HIGH:
            is_blocked = True
            block_reasons.append(f"campaign={campaign_risk.name}")
        if self.accumulator.total_threats >= self.SESSION_THREAT_COUNT_THRESHOLD:
            is_blocked = True
            block_reasons.append(f"threat_count={self.accumulator.total_threats}")

        elapsed_ms = (time.time() - start) * 1000

        return MetaOrchestratorResult(
            is_blocked=is_blocked,
            threat_categories=current_scores,
            campaign_risk=campaign_risk,
            campaign_coherence=coherence,
            decomposition_score=decomp_score,
            session_threat_count=self.accumulator.total_threats,
            active_threats=active_threats,
            model_used="agent-guard-modernbert+deberta-v3",
            inference_time_ms=round(elapsed_ms, 1),
            detail="; ".join(block_reasons) if block_reasons else "clean",
        )

    def reset_session(self):
        self.accumulator = SessionAccumulator()

    def get_posture(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.name,
            "total_classifications": self._classification_count,
            "session_requests": self.accumulator.total_requests,
            "session_threats": self.accumulator.total_threats,
            "agent_ids": list(self.accumulator.agent_ids),
            "cloud_available": self.cloud.available,
            "local_loaded": self.local._loaded,
            "deberta_loaded": self.local._deberta_loaded,
            "visual_prescreener": self.visual_prescreener._ocr_available,
        }
