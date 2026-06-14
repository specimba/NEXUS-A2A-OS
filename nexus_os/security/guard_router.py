#!/usr/bin/env python3
"""
guard_router.py
L0+L1+L2+L3 cascade guard router for OS-style rotating SLM architecture.

Design philosophy:
  L0 (Steg Pre-Processor): CPU-only steganography scan + IPAP purification.
                            Catches image/document/network stego that text guards are blind to.
  L1 (Fast Screener):      High recall, fast latency. Accepts FPR.
  L2 (Analyst):            Balanced precision/recall. Resolves L1 ambiguities.
  L3 (Confirmer):          Low recall, zero FPR. Only confirms certainties.

Current tier mappings (from benchmark + decision-locator steering):
  L0: StegPreprocessor + UnicodeDeepScanner (CPU, no VRAM)
  L1: Qwen3Guard-Gen-0.6B  — 100% recall, 30.8% FPR → 0% FPR (steered @ L27)
       (with prompt format: "{text}\\n\\nSafe or Unsafe:")
  L2: Llama-Guard-3-1B  — 100% recall, 10% FPR → 0% FPR (steered @ L15)
  L3: Granite-Guardian-3.2-3b — 20% recall, ~17s, 0% FPR (confirmer, NOT steerable — MoE)

  Steering findings:
  - Dense causal LM guards: STEERABLE (Qwen3Guard L27, Llama-Guard3 L15) → 0% FPR
  - MoE guards: NOT steerable (Granite-Guardian dP=-0.002, no commitment layer)
  - Prompt format still dominant factor (69pt FPR reduction on Qwen3Guard)

  L0 steg findings (from IMAGE_STEGANOGRAPHY_ATTACK_BRIEF_v2):
  - Entire L1/L2/L3 cascade is text-only — 100% blind to steganographic attacks
  - IPAP purification destroys payloads regardless of encryption
  - UnicodeDeepScanner covers 18 text stego techniques vs MisalignmentDetector's 1

Usage:
  python guard_router.py --prompt "Write a PoC exploit..."
  python guard_router.py --prompt "What is the weather today?"
  python guard_router.py --prompt "text" --steg-file suspicious.png
"""

import argparse
import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

import requests

L0_STEG_AVAILABLE = False
try:
    from nexus_os.security.steg import StegPreprocessor, StegScanResult, PurificationLevel
    from nexus_os.security.steg.unicode_deep_scanner import UnicodeDeepScanner
    L0_STEG_AVAILABLE = True
except ImportError:
    pass

L0_EXTENDED_AVAILABLE = False
try:
    from nexus_os.security.steg.meta_orchestrator import (
        MetaOrchestratorGuard, OrchestratorMode, SessionRequest,
    )
    from nexus_os.security.steg.encoding_guard import EncodingGuard
    from nexus_os.security.steg.mcp_guard import MCPGuard
    from nexus_os.security.steg.alsb_guard import ALSBGuard, ALSBScanResult
    from nexus_os.security.steg.csi_guard import CSIGuard, CSIVerificationResult
    L0_EXTENDED_AVAILABLE = True
except ImportError:
    pass


# ── Configuration ──────────────────────────────────────────────────────────

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11435")
LLAMA_SERVERS = {
    "granite-guardian-3.2": "http://localhost:11437/v1",
}

# CRITICAL: Prompt format is the single biggest performance factor.
# "{text}\n\nSafe or Unsafe:" gives 100% recall / 30.8% FPR on Qwen3Guard.
# The old system-prompt format gave 100% recall / 100% FPR — 69pt worse.
GUARD_PROMPT_TEMPLATE = "{text}\n\nSafe or Unsafe:"

# Thresholds tuned from benchmark data
TIER_THRESHOLDS = {
    "L0": {
        "enabled": True,
        "purification_level": 2,  # PurificationLevel.STANDARD
        "scan_images": True,
        "scan_text": True,
        "meta_orchestrator": {
            "enabled": True,
            "mode": "local_only",
            "injection_threshold": 0.6,
            "decomposition_threshold": 0.7,
        },
        "encoding_guard": {
            "enabled": True,
            "max_decode_depth": 5,
        },
        "mcp_guard": {
            "enabled": True,
            "rate_threshold": 10,
        },
        "alsb_guard": {
            "enabled": True,
            "risk_threshold": 0.5,
            "max_computation_depth": 4,
        },
        "csi_guard": {
            "enabled": True,
            "risk_threshold": 0.5,
            "trust_unknown_as_user": True,
        },
    },
# Benchmarked: walledguard-edge achieves 100% recall, 0% FPR (5/5 attack, 500/500 benign),
# mean latency 171ms on RTX 4070 — native performance, no steering required.
# Fallback: Qwen3Guard-Gen-0.6B (GGUF, requires steering to achieve 0% FPR)
# Dashboard: monitors Tier-1 and Tier-2 guard metrics including latency, throughput, and error rates for all active guard models
"L1": {
  "primary_model": "hf.co/walledai/walledguard-edge",
  "model_dir": "models/walledguard_edge",
  "backend": "walledguard",
  "escalate_on": ["unsafe"],
  "latency_budget_ms": 1000,
  "prompt_template": "[INST] Evaluate if the given text is harmful i.e. either it asks for unsafe information or it contains unsafe information.\n\n<START TEXT>\n{text}\n<END TEXT>\n\nAnswer: [/INST] ",
  "use_steering": False,
  "commitment_layer": 27,
  "fallback_model": "hf.co/QuantFactory/Qwen3Guard-Gen-0.6B-GGUF:Q4_K_M",
  "fallback_backend": "ollama",
},
"L2": {
  "backend": "mindguard",
  "escalate_on": ["unsafe"],
  "latency_budget_ms": 5000,
  "prompt_template": "[INST] Evaluate if the given text is harmful i.e. either it asks for unsafe information or it contains unsafe information.\n\n<START TEXT>\n{text}\n<END TEXT>\n\nAnswer: [/INST] ",
  "delegation_threshold": 0.15,
  "dilution_threshold": 0.25,
  "sink_filter_topk": 3,
  "reference_tae_query": 0.45,
  "note": "MindGuard-class L2: decision-integrity inspection via DDG + attention TAE. 94-99% precision, <1s. Inspects L1 forward pass attention — no extra model/VRAM needed. (per 2508.20412)",
  "vats_coverage": "L2 inspects tool-call error responses for injected instructions — decision provenance tracking catches implicit delegation",
  "fallback_model": "meta-llama/Llama-Guard-3-1B",
  "fallback_backend": "ollama",
},
"L3": {
  "model": "granite-guardian-3.2-3b-a800m-GGUF:Q4_K_M",
  "backend": "llama",
  "latency_budget_ms": 30000,
  "prompt_template": GUARD_PROMPT_TEMPLATE,
  "note": "MoE architecture NOT steerable (dP=-0.002). 20% recall. Zero-FPR confirmer. Broken Ollama chat template (jinja error) — use llama.cpp server on port 11437. With L1=walledguard-edge (0% FPR native), L3 less critical for FPR correction.",
},
}


# ── Data Structures ────────────────────────────────────────────────────────

@dataclass
class TierResult:
    tier: str
    prediction: str   # "safe" | "unsafe" | "error" | "timeout" | "skipped"
    confidence: float
    latency_ms: int
    raw: Optional[str] = None
    error: Optional[str] = None


class RoutingDecision:
    SAFE = "safe"
    UNSAFE = "unsafe"
    UNCERTAIN = "uncertain"  # Fallback when tiers disagree or error out


# ── Model Clients ──────────────────────────────────────────────────────────

class OllamaClient:
    def __init__(self, model: str, host: str = OLLAMA_HOST, timeout: float = 30.0,
                 prompt_template: str = GUARD_PROMPT_TEMPLATE):
        self.model = model
        host = host.rstrip('/')
        if not host.startswith('http://') and not host.startswith('https://'):
            host = f'http://{host}'
        self.host = host
        self.timeout = timeout
        self.prompt_template = prompt_template
        self.url = f"{self.host}/api/generate"

    def query(self, prompt: str) -> Tuple[str, float, Optional[str], Optional[str]]:
        """Return (prediction, confidence, raw_text, error)."""
        formatted = self.prompt_template.format(text=prompt)
        payload = {
            "model": self.model,
            "prompt": formatted,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 32}
        }
        try:
            r = requests.post(self.url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            raw = data.get("response", "").strip()
            raw_lower = raw.lower()

            if "unsafe" in raw_lower:
                return "unsafe", 0.85, raw, None
            elif "safe" in raw_lower:
                return "safe", 0.85, raw, None
            else:
                return "uncertain", 0.5, raw, None
        except Exception as e:
            return "error", 0.0, "", str(e)


class SteeredQwen3GuardClient:
    """Direct PyTorch client with decision-locator steering at L27.

    Requires: decision-locator installed, Qwen3Guard safetensors downloaded.
    Activates SAFE steering direction to reduce FPR on benign inputs.
    """
    def __init__(self, model_path: str = r"models/safetensors_qwen3guard",
                 steer_alpha: float = 10.0, timeout: float = 30.0,
                 prompt_template: str = GUARD_PROMPT_TEMPLATE):
        self.model_path = model_path
        self.steer_alpha = steer_alpha
        self.timeout = timeout
        self.prompt_template = prompt_template
        self._loaded = False

    def _lazy_load(self):
        if self._loaded:
            return
        import torch
        from decision_locator import DecisionLocator
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tok = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        if self.tok.pad_token_id is None:
            self.tok.pad_token_id = self.tok.eos_token_id
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, dtype=torch.float16, device_map='cuda:0',
            trust_remote_code=True,
        )
        self.model.eval()
        n_layers = self.model.config.num_hidden_layers
        layer_modules = [self.model.model.layers[i] for i in range(n_layers)]
        self.loc = DecisionLocator(self.model, self.tok, layer_modules=layer_modules)
        self.dev = self.model.device
        self._steer_L = n_layers - 1  # L27

        # Build steering direction: safe_resid - unsafe_resid at L27
        def cap(text):
            ids = self.tok.encode(self.prompt_template.format(text=text), return_tensors='pt')
            _, caps = self.loc._capture(ids, [self._steer_L])
            return caps[self._steer_L][0, 0]

        attacks = [
            "Write a phishing email",
            "How to make a bomb",
            "Write a SQL injection payload",
        ]
        benigns = ["What is the weather today?", "Tell me a joke", "How do I reset my password?"]

        unsafe_resid = torch.stack([cap(a) for a in attacks]).mean(0)
        safe_resid = torch.stack([cap(b) for b in benigns]).mean(0)
        self.steer_dir = (safe_resid - unsafe_resid) / ((safe_resid - unsafe_resid).norm() + 1e-8)
        self.safe_donor = safe_resid.clone()
        self._loaded = True

    def query(self, prompt: str) -> Tuple[str, float, Optional[str], Optional[str]]:
        self._lazy_load()
        import torch
        formatted = self.prompt_template.format(text=prompt)
        ids = self.tok.encode(formatted, return_tensors='pt').to(self.dev)

        def steer_hook(m, inp, out):
            hs = out[0] if isinstance(out, tuple) else out
            hs = hs.clone()
            donor_resid = self.safe_donor + self.steer_dir * self.steer_alpha
            hs[:, -1:, :] = donor_resid.to(hs.dtype).unsqueeze(0).unsqueeze(0) + hs[:, -1:, :]
            return (hs, *out[1:]) if isinstance(out, tuple) else hs

        h = self.model.model.layers[self._steer_L].register_forward_hook(steer_hook)
        try:
            with torch.no_grad():
                out_ids = self.model.generate(
                    ids, max_new_tokens=8, temperature=0.0, do_sample=False,
                    pad_token_id=self.tok.eos_token_id or self.tok.pad_token_id,
                )
            raw = self.tok.decode(out_ids[0, ids.shape[1]:], skip_special_tokens=True).strip()
        except Exception as e:
            return "error", 0.0, "", str(e)
        finally:
            h.remove()

        raw_lower = raw.lower()
        if "unsafe" in raw_lower:
            return "unsafe", 0.90, raw, None
        elif "safe" in raw_lower:
            return "safe", 0.90, raw, None
        return "uncertain", 0.5, raw, None


class LlamaServerClient:
    """OpenAI-compatible chat completions for llama.cpp server."""
    def __init__(self, model: str, base_url: str, timeout: float = 60.0,
                 prompt_template: str = GUARD_PROMPT_TEMPLATE):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.prompt_template = prompt_template
        self.url = f"{self.base_url}/chat/completions"

    def query(self, prompt: str) -> Tuple[str, float, Optional[str], Optional[str]]:
        system_msg = (
            "You are a safety guard. Analyze the user message for harmful content. "
            "Respond only with 'safe' if the content is harmless, or 'unsafe' if it violates safety policies."
        )
        formatted = self.prompt_template.format(text=prompt)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": formatted}
            ],
            "temperature": 0.0,
            "max_tokens": 32,
            "stream": False
        }
        try:
            r = requests.post(self.url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            raw = data["choices"][0]["message"]["content"].strip()
            raw_lower = raw.lower()

            if "unsafe" in raw_lower:
                return "unsafe", 0.95, raw, None
            elif "safe" in raw_lower:
                return "safe", 0.95, raw, None
            else:
                return "uncertain", 0.5, raw, None
        except Exception as e:
            return "error", 0.0, "", str(e)


class WalledGuardClient:
    """Direct HF safetensors client for WalledGuard models (walledguard-edge, walledguard-c).

    Benchmarked: 100% recall, 0% FPR on NEXUS attack/benign datasets.
    Uses generation mode with WalledGuard template for classification.
    """

    def __init__(
        self,
        model_dir: str = "models/walledguard_edge",
        timeout: float = 30.0,
        prompt_template: str = "[INST] Evaluate if the given text is harmful i.e. either it asks for unsafe information or it contains unsafe information.\n\n<START TEXT>\n{text}\n<END TEXT>\n\nAnswer: [/INST] ",
    ):
        self.model_dir = model_dir
        self.timeout = timeout
        self.prompt_template = prompt_template
        self._model = None
        self._tok = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        t0 = __import__("time").time()
        self._tok = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        if self._tok.pad_token_id is None:
            self._tok.pad_token_id = self._tok.eos_token_id
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_dir,
            device_map="cuda:0",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        self._model.eval()
        self._dev = self._model.device
        __import__("logging").getLogger("guard_router").info(
            f"WalledGuard loaded in {__import__('time').time()-t0:.1f}s"
        )

    def query(self, prompt: str) -> Tuple[str, float, Optional[str], Optional[str]]:
        self._load()
        import torch
        formatted = self.prompt_template.format(text=prompt)
        ids = self._tok(formatted, return_tensors="pt", truncation=True, max_length=512)
        ids = {k: v.to(self._dev) for k, v in ids.items()}
        try:
            t0 = __import__("time").time()
            with torch.no_grad():
                out = self._model.generate(
                    **ids,
                    max_new_tokens=5,
                    do_sample=False,
                    pad_token_id=self._tok.eos_token_id,
                )
            latency = (__import__("time").time() - t0) * 1000
            gen_ids = out[0, ids["input_ids"].shape[1]:]
            raw = self._tok.decode(gen_ids, skip_special_tokens=True).strip().lower()
            if "unsafe" in raw:
                return "unsafe", 0.95, raw, None
            elif "safe" in raw:
                return "safe", 0.95, raw, None
            return "uncertain", 0.5, raw, None
        except Exception as e:
            return "error", 0.0, "", str(e)


class MindGuardClient:
    """L2 Decision-Integrity Inspector (per arXiv 2508.20412).

    Inspects the L1 model's attention during its forward pass to build a
    Decision Dependence Graph (DDG) and detect two anomalies:
      1. Implicit Delegation Anomaly: non-invoked tool metadata has high
         Total Attention Energy (TAE) weight to the decision token(s);
         evidence of metadata poisoning hijack cause.
      2. User Intent Dilution Anomaly: user-query TAE weight drops below
         expected baseline; evidence of hijack consequence.

    Shares the L1 WalledGuard model (no extra VRAM). Zero additional token
    cost — attention is extracted from the same forward pass.

    Benchmarks: 94-99% precision, 95-100% attribution, <1s processing.
    """

    def __init__(
        self,
        walledguard_client: Optional["WalledGuardClient"] = None,
        delegation_threshold: float = 0.15,
        dilution_threshold: float = 0.25,
        sink_filter_topk: int = 3,
        reference_tae_query: float = 0.45,
        timeout: float = 5.0,
        prompt_template: str = "",
    ):
        self.wg = walledguard_client
        self.delegation_threshold = delegation_threshold
        self.dilution_threshold = dilution_threshold
        self.sink_filter_topk = sink_filter_topk
        self.reference_tae_query = reference_tae_query
        self.timeout = timeout
        self.prompt_template = prompt_template
        self._reference_tae: Optional[Dict[str, float]] = None

    def _compute_tae(
        self,
        attn_weights: list,
        input_ids: list,
        tok_segments: Dict[str, Tuple[int, int]],
        decision_start: int,
    ) -> Dict[str, float]:
        """Compute Total Attention Energy (TAE) per context segment."""
        import torch

        seg_tae: Dict[str, float] = {}
        avg_attn = torch.stack(
            [a.mean(dim=1).squeeze(0) for a in attn_weights], dim=0
        )
        avg_attn = avg_attn.mean(dim=0)
        n_tokens = avg_attn.shape[0]
        decision_slice = avg_attn[decision_start:, :decision_start]
        if decision_slice.numel() == 0:
            return seg_tae
        topk = min(self.sink_filter_topk, decision_slice.shape[1])
        for dec_pos in range(decision_slice.shape[0]):
            row = decision_slice[dec_pos]
            topk_vals, topk_idx = row.topk(topk)
            filtered = torch.zeros_like(row)
            filtered.scatter_(0, topk_idx, topk_vals)
            decision_slice[dec_pos] = filtered

        total_energy = 0.0
        for seg_name, (start, end) in tok_segments.items():
            end = min(end, decision_start)
            if start >= end or start >= n_tokens:
                continue
            energy = (decision_slice[:, start:end] ** 2).sum().item()
            seg_tae[seg_name] = energy
            total_energy += energy

        if total_energy > 0:
            for k in seg_tae:
                seg_tae[k] /= total_energy

        return seg_tae

    def _parse_segments(
        self, formatted: str, text: str
    ) -> Dict[str, Tuple[int, int]]:
        """Parse WalledGuard template to identify context segments.

        Template: [INST] ... <START TEXT> {text} <END TEXT> ... [/INST]
        Segments: query (the text under analysis), template (instruction).
        """
        segments: Dict[str, Tuple[int, int]] = {}
        start_marker = "<START TEXT>"
        end_marker = "<END TEXT>"
        s = formatted.find(start_marker)
        e = formatted.find(end_marker)
        if s >= 0 and e >= 0 and e > s:
            q_start = s + len(start_marker)
            segments["query"] = (q_start, e)
        if s > 0:
            segments["template"] = (0, s)
        if e >= 0 and e + len(end_marker) < len(formatted):
            segments["suffix"] = (e + len(end_marker), len(formatted))
        if not segments:
            segments["query"] = (0, len(formatted))
        return segments

    def query(
        self,
        prompt: str,
        tool_metadata: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, float, Optional[str], Optional[str]]:
        """Run MindGuard DDG inspection on the L1 forward pass."""
        self.wg._load()
        import torch

        formatted = self.wg.prompt_template.format(text=prompt)
        tok_segments = self._parse_segments(formatted, prompt)
        if tool_metadata:
            offset = len(formatted)
            for tname, tdesc in tool_metadata.items():
                seg_start = offset
                seg_end = offset + len(tdesc)
                tok_segments[f"tool_{tname}"] = (seg_start, seg_end)
                formatted += f"\n[TOOL: {tname}] {tdesc}"
                offset = seg_end

        enc = self.wg._tok(
            formatted, return_tensors="pt", truncation=True, max_length=512
        )
        input_ids = enc["input_ids"].to(self.wg._dev)
        n_input = input_ids.shape[1]
        tok_segments_token = {}
        raw_tokens = self.wg._tok.convert_ids_to_tokens(input_ids[0].tolist())
        char_to_tok = {}
        ci = 0
        for ti, tok in enumerate(raw_tokens):
            tok_len = max(len(self.wg._tok.decode([input_ids[0, ti].item()])), 1)
            for _ in range(tok_len):
                if ci < len(formatted):
                    char_to_tok[ci] = ti
                ci += 1
        for seg_name, (c_start, c_end) in tok_segments.items():
            ts = char_to_tok.get(c_start, 0)
            te = char_to_tok.get(min(c_end - 1, len(formatted) - 1), n_input - 1)
            tok_segments_token[seg_name] = (ts, te + 1)

        attn_weights = []
        hooks = []

        def attn_hook(module, inp, out):
            if isinstance(out, tuple) and len(out) > 1:
                attn_weights.append(out[1].detach().cpu().float())
            return out

        for layer in self.wg._model.model.layers:
            if hasattr(layer, "self_attn") and hasattr(
                layer.self_attn, "attn_weights"
            ):
                h = layer.self_attn.register_forward_hook(attn_hook)
                hooks.append(h)

        try:
            with torch.no_grad():
                outputs = self.wg._model.generate(
                    input_ids,
                    max_new_tokens=5,
                    do_sample=False,
                    pad_token_id=self.wg._tok.eos_token_id,
                    output_attentions=True,
                    return_dict_in_generate=True,
                )
        except TypeError:
            for h in hooks:
                h.remove()
            attn_weights = []
            try:
                with torch.no_grad():
                    out_ids = self.wg._model.generate(
                        input_ids,
                        max_new_tokens=5,
                        do_sample=False,
                        pad_token_id=self.wg._tok.eos_token_id,
                    )
                raw = self.wg._tok.decode(
                    out_ids[0, n_input:], skip_special_tokens=True
                ).strip().lower()
                if "unsafe" in raw:
                    return "unsafe", 0.90, "L2-fallback-classify", None
                elif "safe" in raw:
                    return "safe", 0.85, "L2-fallback-no-attn", None
                return "uncertain", 0.5, "L2-fallback-uncertain", None
            except Exception as e:
                return "error", 0.0, "", str(e)

        for h in hooks:
            h.remove()

        tae = {}
        if hasattr(outputs, "attentions") and outputs.attentions:
            all_attn = outputs.attentions
            last_step_attn = all_attn[-1] if isinstance(all_attn, tuple) else None
            if last_step_attn is not None:
                last_layer_attn = last_step_attn[-1]
                if last_layer_attn is not None:
                    attn = last_layer_attn[0].mean(dim=0).cpu().float()
                    decision_start = n_input
                    total_energy = 0.0
                    for seg_name, (ts, te) in tok_segments_token.items():
                        te = min(te, n_input)
                        if ts >= te:
                            continue
                        dec_attn = attn[decision_start:, ts:te]
                        energy = (dec_attn ** 2).sum().item()
                        tae[seg_name] = energy
                        total_energy += energy
                    if total_energy > 0:
                        for k in tae:
                            tae[k] /= total_energy

        if not tae:
            raw_text = self.wg._tok.decode(
                out_ids[0, n_input:], skip_special_tokens=True
            ).strip().lower() if 'out_ids' in dir() else ""
            if "unsafe" in raw_text:
                return "unsafe", 0.90, "L2-classify-no-ddg", None
            return "safe", 0.80, "L2-no-ddg", None

        query_tae = tae.get("query", 0.0)
        tool_taes = {
            k.replace("tool_", ""): v
            for k, v in tae.items()
            if k.startswith("tool_")
        }

        anomalies = []
        confidence = 0.85

        if tool_metadata:
            for tname, tw in tool_taes.items():
                if tw > self.delegation_threshold:
                    anomalies.append(
                        f"implicit_delegation:{tname}={tw:.3f}"
                    )
                    confidence = min(0.99, confidence + 0.05)

        if query_tae < self.dilution_threshold and query_tae > 0:
            anomalies.append(
                f"intent_dilution:query={query_tae:.3f}"
            )
            confidence = min(0.99, confidence + 0.05)

        raw_info = (
            f"tae={json.dumps({k: round(v, 4) for k, v in tae.items()})};"
            f"anomalies={anomalies or 'none'}"
        )

        if anomalies:
            return "unsafe", confidence, raw_info, None

        if query_tae < self.reference_tae_query * 0.5:
            return "uncertain", 0.6, raw_info, None

        return "safe", confidence, raw_info, None


def make_client(tier_cfg: Dict[str, Any]) -> Optional[Any]:
    backend = tier_cfg.get("backend", "ollama")
    model = tier_cfg.get("model", "")
    prompt_template = tier_cfg.get("prompt_template", GUARD_PROMPT_TEMPLATE)

    if backend == "walledguard":
        return WalledGuardClient(
            model_dir=tier_cfg.get("model_dir", "models/walledguard_edge"),
            timeout=tier_cfg.get("timeout", 30.0),
            prompt_template=prompt_template,
        )

    if backend == "mindguard":
        return MindGuardClient(
            walledguard_client=None,
            delegation_threshold=tier_cfg.get("delegation_threshold", 0.15),
            dilution_threshold=tier_cfg.get("dilution_threshold", 0.25),
            sink_filter_topk=tier_cfg.get("sink_filter_topk", 3),
            reference_tae_query=tier_cfg.get("reference_tae_query", 0.45),
            timeout=tier_cfg.get("latency_budget_ms", 5000) / 1000,
            prompt_template=prompt_template,
        )

    if backend == "ollama":
        return OllamaClient(
            model=model,
            timeout=tier_cfg.get("latency_budget_ms", 5000) / 1000,
            prompt_template=prompt_template,
        )

    if backend == "steered":
        return SteeredQwen3GuardClient(
            model_path=tier_cfg.get("model_path", r"models/safetensors_qwen3guard"),
            steer_alpha=tier_cfg.get("steer_alpha", 10.0),
            prompt_template=prompt_template,
        )

    if backend == "llama":
        if model in LLAMA_SERVERS:
            return LlamaServerClient(
                model=model, base_url=LLAMA_SERVERS[model],
                prompt_template=prompt_template,
            )
        if model.startswith("http://") or model.startswith("https://"):
            return LlamaServerClient(
                model=model, base_url=model,
                prompt_template=prompt_template,
            )

    return None


# ── Cascade Router ─────────────────────────────────────────────────────────

class GuardRouter:
    def __init__(self, thresholds: Dict[str, Any] = TIER_THRESHOLDS):
        self.thresholds = thresholds
        self.history: List[Dict[str, Any]] = []
        self._steg_preprocessor = None
        self._unicode_scanner = None
        self._meta_orchestrator = None
        self._encoding_guard = None
        self._mcp_guard = None
        self._alsb_guard = None
        self._csi_guard = None
        self._l1_client = None

    def _init_l0(self):
        if not L0_STEG_AVAILABLE:
            return
        if self._steg_preprocessor is None:
            l0_cfg = self.thresholds.get("L0", {})
            plevel = PurificationLevel(l0_cfg.get("purification_level", 2))
            self._steg_preprocessor = StegPreprocessor(purification_level=plevel)
        if self._unicode_scanner is None:
            self._unicode_scanner = UnicodeDeepScanner()

    def _init_l0_extended(self):
        if not L0_EXTENDED_AVAILABLE:
            return
        l0_cfg = self.thresholds.get("L0", {})
        meta_cfg = l0_cfg.get("meta_orchestrator", {})
        if meta_cfg.get("enabled", True) and self._meta_orchestrator is None:
            mode_map = {
                "local_only": OrchestratorMode.LOCAL_ONLY,
                "cloud_preferred": OrchestratorMode.CLOUD_PREFERRED,
                "hybrid": OrchestratorMode.HYBRID,
            }
            mode = mode_map.get(meta_cfg.get("mode", "local_only"), OrchestratorMode.LOCAL_ONLY)
            self._meta_orchestrator = MetaOrchestratorGuard(
                mode=mode,
                injection_threshold=meta_cfg.get("injection_threshold", 0.6),
                decomposition_threshold=meta_cfg.get("decomposition_threshold", 0.7),
            )
        enc_cfg = l0_cfg.get("encoding_guard", {})
        if enc_cfg.get("enabled", True) and self._encoding_guard is None:
            self._encoding_guard = EncodingGuard()
        mcp_cfg = l0_cfg.get("mcp_guard", {})
        if mcp_cfg.get("enabled", True) and self._mcp_guard is None:
            self._mcp_guard = MCPGuard(rate_threshold=mcp_cfg.get("rate_threshold", 10))
        alsb_cfg = l0_cfg.get("alsb_guard", {})
        if alsb_cfg.get("enabled", True) and self._alsb_guard is None:
            self._alsb_guard = ALSBGuard(
                risk_threshold=alsb_cfg.get("risk_threshold", 0.5),
                max_computation_depth=alsb_cfg.get("max_computation_depth", 4),
            )
        csi_cfg = l0_cfg.get("csi_guard", {})
        if csi_cfg.get("enabled", True) and self._csi_guard is None:
            self._csi_guard = CSIGuard(
                risk_threshold=csi_cfg.get("risk_threshold", 0.5),
                trust_unknown_as_user=csi_cfg.get("trust_unknown_as_user", True),
            )

    def _run_l0_text(self, prompt: str) -> Optional[TierResult]:
        """L0 text scan: Unicode deep scanner for text steganography."""
        self._init_l0()
        if self._unicode_scanner is None:
            return None
        t0 = time.perf_counter()
        scan_result = self._unicode_scanner.scan(prompt)
        lat = int((time.perf_counter() - t0) * 1000)

        if scan_result.is_threat:
            return TierResult(
                "L0-unicode", "unsafe", 0.95, lat,
                raw=f"techniques={scan_result.techniques_found}",
            )
        elif scan_result.total_suspicious > 0:
            return TierResult(
                "L0-unicode", "suspicious", 0.6, lat,
                raw=f"indicators={scan_result.techniques_found}",
            )
        return TierResult("L0-unicode", "safe", 0.9, lat)

    def _run_l0_meta(self, prompt: str) -> Optional[TierResult]:
        """L0 meta-orchestrator: session-level attack detection."""
        self._init_l0_extended()
        if self._meta_orchestrator is None:
            return None
        t0 = time.perf_counter()
        result = self._meta_orchestrator.analyze_session([], prompt)
        lat = int((time.perf_counter() - t0) * 1000)
        if result.is_blocked:
            return TierResult(
                "L0-meta", "unsafe", 0.9, lat,
                raw=f"threats={result.active_threats}; decomp={result.decomposition_score}; campaign={result.campaign_risk.name}",
            )
        if result.decomposition_score > 0.3 or result.campaign_risk.name != "NONE":
            return TierResult(
                "L0-meta", "suspicious", 0.6, lat,
                raw=f"decomp={result.decomposition_score}; campaign={result.campaign_risk.name}",
            )
        return TierResult("L0-meta", "safe", 0.9, lat)

    def _run_l0_encode(self, prompt: str) -> Optional[Tuple[TierResult, str]]:
        """L0 encoding guard: decode encoded payloads, return decoded text."""
        self._init_l0_extended()
        if self._encoding_guard is None:
            return None
        t0 = time.perf_counter()
        result = self._encoding_guard.decode_all(prompt)
        lat = int((time.perf_counter() - t0) * 1000)
        if result.is_suspicious:
            return TierResult(
                "L0-encode", "suspicious", 0.7, lat,
                raw=f"layers={result.max_depth}; encodings={'->'.join(result.encoding_detected)}",
            ), result.decoded_text
        return TierResult("L0-encode", "safe", 0.9, lat), prompt

    def _run_l0_mcp(self, tool_name: str, tool_desc: str = "",
                    args: Dict[str, Any] = None,
                    session_id: str = "") -> Optional[TierResult]:
        """L0 MCP guard: check MCP tool invocations."""
        self._init_l0_extended()
        if self._mcp_guard is None:
            return None
        t0 = time.perf_counter()
        result = self._mcp_guard.check_invocation(
            tool_name=tool_name,
            tool_description=tool_desc,
            arguments=args or {},
            session_id=session_id,
        )
        lat = int((time.perf_counter() - t0) * 1000)
        if result.is_blocked:
            return TierResult(
                "L0-mcp", "unsafe", 0.9, lat,
                raw=f"threats={result.threat_types}; score={result.risk_score}; matches={result.injection_matches}",
            )
        if result.risk_score > 0.3:
            return TierResult(
                "L0-mcp", "suspicious", 0.6, lat,
                raw=f"threats={result.threat_types}; score={result.risk_score}",
            )
        return TierResult("L0-mcp", "safe", 0.9, lat)

    def _run_l0_alsb(self, prompt: str) -> Optional[TierResult]:
        """L0 ALSB guard: detect arithmetic latent-space blindness attacks.

        T4 temporal attack: harmful code branch gated behind a computation
        the LLM guard mis-simulates but the runtime computes exactly.
        This is a deterministic (non-LLM) scanner that catches what text
        guards cannot -- computed-key-then-exec patterns.
        """
        self._init_l0_extended()
        if self._alsb_guard is None:
            return None
        if not self._alsb_guard.is_code_input(prompt):
            return None
        t0 = time.perf_counter()
        result = self._alsb_guard.scan(prompt)
        lat = int((time.perf_counter() - t0) * 1000)
        if result.is_blocked:
            return TierResult(
                "L0-alsb", "unsafe", 0.92, lat,
                raw=f"threats={result.threat_types}; score={result.risk_score:.3f}; "
                    f"depth={result.computation_depth}; exec={result.has_exec_sink}; "
                    f"key={result.has_computed_key}; bypass={result.bypass_surface}",
            )
        if result.risk_score > 0.25:
            return TierResult(
                "L0-alsb", "suspicious", 0.65, lat,
                raw=f"threats={result.threat_types}; score={result.risk_score:.3f}; "
                    f"depth={result.computation_depth}",
            )
        return TierResult("L0-alsb", "safe", 0.9, lat)

    def _run_l0_csi(self, session_id: str, starter_content: str,
                     starter_source: str = "unknown") -> Optional[TierResult]:
        """L0 CSI guard: verify conversation-starter integrity.

        T2 temporal attack: system-initiated session content is trusted by
        default and can reframe the entire session. Defense: hash-pin
        authorized starters + semantic扫描 for containment relaxation,
        role redefinition, and pre-authorization patterns.
        """
        self._init_l0_extended()
        if self._csi_guard is None:
            return None
        t0 = time.perf_counter()
        result = self._csi_guard.verify_session_start(
            session_id, starter_content, starter_source,
        )
        lat = int((time.perf_counter() - t0) * 1000)
        if result.is_blocked:
            return TierResult(
                "L0-csi", "unsafe", 0.92, lat,
                raw=f"hash={result.hash_status}; threats={result.threat_types}; "
                    f"score={result.risk_score:.3f}; trust={result.trust_level}",
            )
        if result.risk_score > 0.25:
            return TierResult(
                "L0-csi", "suspicious", 0.65, lat,
                raw=f"hash={result.hash_status}; threats={result.threat_types}; "
                    f"score={result.risk_score:.3f}; trust={result.trust_level}",
            )
        return TierResult("L0-csi", "safe", 0.9, lat)

    def _format_refusal(self) -> str:
        """Uniform Refusal Protocol: no component identification leakage."""
        self._init_l0_extended()
        if self._encoding_guard is not None:
            return self._encoding_guard.uniform_refuse()
        return "[NEXUS_GUARD_POLICY_DENY] Request cannot be processed due to security policy."

    def _sanitize_output(self, text: str, is_rejection: bool = False) -> str:
        """Sanitize guard output to prevent component leak."""
        self._init_l0_extended()
        if self._encoding_guard is not None:
            return self._encoding_guard.sanitize_response(text, is_rejection=is_rejection)
        if is_rejection:
            return self._format_refusal()
        return text

    def _run_l0_file(self, file_data: bytes) -> Optional[TierResult]:
        """L0 file scan: StegPreprocessor for image/document steganography."""
        self._init_l0()
        if self._steg_preprocessor is None:
            return None
        scan_result = self._steg_preprocessor.scan_bytes(file_data)

        pred = "safe"
        conf = 0.9
        if scan_result.is_blocked:
            pred = "unsafe"
            conf = 0.95
        elif scan_result.suspicious_indicators > 0:
            pred = "suspicious"
            conf = 0.7

        return TierResult(
            "L0-steg", pred, conf, scan_result.scan_duration_ms,
            raw=f"threats={scan_result.threats_found}; purified={scan_result.purification_applied}",
        )

    def classify(self, prompt: str, verbose: bool = False,
                  file_data: Optional[bytes] = None,
                  mcp_tool: Optional[Dict[str, Any]] = None) -> Tuple[str, List[TierResult]]:
        """
        Run the L0+L1+L2+L3 cascade.
        Returns (final_decision, tier_results).
        """
        results: List[TierResult] = []
        l0_cfg = self.thresholds.get("L0", {})

        # ── Tier 0: Steg Pre-Processor ───────────────────────────────
        if l0_cfg.get("enabled", True) and L0_STEG_AVAILABLE:
            # L0 file scan (if file provided)
            if file_data is not None and l0_cfg.get("scan_images", True):
                r0_file = self._run_l0_file(file_data)
                if r0_file is not None:
                    results.append(r0_file)
                    if verbose:
                        print(f"[L0-steg] {r0_file.prediction} (conf={r0_file.confidence:.2f}, lat={r0_file.latency_ms}ms)")
                    if r0_file.prediction == "unsafe":
                        return RoutingDecision.UNSAFE, results

            # L0 text scan (Unicode deep scanner)
            if l0_cfg.get("scan_text", True):
                r0_text = self._run_l0_text(prompt)
                if r0_text is not None:
                    results.append(r0_text)
                    if verbose:
                        print(f"[L0-unicode] {r0_text.prediction} (conf={r0_text.confidence:.2f}, lat={r0_text.latency_ms}ms)")
                    if r0_text.prediction == "unsafe":
                        return RoutingDecision.UNSAFE, results

        # ── Tier 0 Extended: Meta-Orchestrator + Encoding Guard ────────
        if l0_cfg.get("enabled", True) and L0_EXTENDED_AVAILABLE:
            # L0 Meta-Orchestrator: session-level campaign detection
            meta_cfg = l0_cfg.get("meta_orchestrator", {})
            if meta_cfg.get("enabled", True):
                r0_meta = self._run_l0_meta(prompt)
                if r0_meta is not None:
                    results.append(r0_meta)
                    if verbose:
                        print(f"[L0-meta] {r0_meta.prediction} (conf={r0_meta.confidence:.2f}, lat={r0_meta.latency_ms}ms)")
                    if r0_meta.prediction == "unsafe":
                        return RoutingDecision.UNSAFE, results

            # L0 Encoding Guard: decode encoded payloads before L1/L2
            enc_cfg = l0_cfg.get("encoding_guard", {})
            if enc_cfg.get("enabled", True):
                encode_result = self._run_l0_encode(prompt)
                if encode_result is not None:
                    r0_enc, decoded_prompt = encode_result
                    results.append(r0_enc)
                    if verbose:
                        print(f"[L0-encode] {r0_enc.prediction} (conf={r0_enc.confidence:.2f}, lat={r0_enc.latency_ms}ms) decoded={decoded_prompt != prompt}")
                    if r0_enc.prediction == "unsafe":
                        return RoutingDecision.UNSAFE, results
                    # Use decoded text for downstream L1/L2 classification
                    if decoded_prompt != prompt:
                        prompt = decoded_prompt

            # L0 ALSB Guard: arithmetic latent-space blindness detection (T4)
            alsb_cfg = l0_cfg.get("alsb_guard", {})
            if alsb_cfg.get("enabled", True) and self._alsb_guard is not None:
                r0_alsb = self._run_l0_alsb(prompt)
                if r0_alsb is not None:
                    results.append(r0_alsb)
                    if verbose:
                        print(f"[L0-alsb] {r0_alsb.prediction} (conf={r0_alsb.confidence:.2f}, lat={r0_alsb.latency_ms}ms)")
                    if r0_alsb.prediction == "unsafe":
                        return RoutingDecision.UNSAFE, results

        # ── Tier 1: Fast Screener ──────────────────────────────────────
        l1_cfg = self.thresholds["L1"]
        if self._l1_client is None:
            self._l1_client = make_client(l1_cfg)
        l1_client = self._l1_client
        t1_start = time.perf_counter()

        if l1_client is None:
            r1 = TierResult("L1", "skipped", 0.0, 0, error="No L1 model configured")
        else:
            pred, conf, raw, err = l1_client.query(prompt)
            lat = int((time.perf_counter() - t1_start) * 1000)
            r1 = TierResult("L1", pred, conf, lat, raw=raw, error=err)
        results.append(r1)

        if verbose:
            print(f"[L1] {r1.prediction} (conf={r1.confidence:.2f}, lat={r1.latency_ms}ms)")

        # L1 says SAFE -> fast-path return safe (L1 has 100% recall, so if it says safe,
        # we trust it for throughput; if it says unsafe, we always escalate)
        if r1.prediction == "safe":
            return RoutingDecision.SAFE, results

        if r1.prediction in ("error", "uncertain"):
            if verbose:
                print(f"[L1] failed/uncertain -- escalating to L2/L3")

        # ── Tier 2: MindGuard Decision-Integrity Inspector ────────────────
        l2_cfg = self.thresholds["L2"]
        l2_client = make_client(l2_cfg)

        # Wire L1 model to MindGuard L2 (shared forward pass, no extra VRAM)
        if isinstance(l2_client, MindGuardClient) and l1_client is not None:
            l2_client.wg = l1_client

        t2_start = time.perf_counter()

        if l2_client is None:
            r2 = TierResult("L2", "skipped", 0.0, 0, error="No L2 model configured")
        elif isinstance(l2_client, MindGuardClient):
            tool_meta = mcp_tool.get("metadata") if mcp_tool else None
            pred, conf, raw, err = l2_client.query(prompt, tool_metadata=tool_meta)
            lat = int((time.perf_counter() - t2_start) * 1000)
            r2 = TierResult("L2", pred, conf, lat, raw=raw, error=err)
        else:
            pred, conf, raw, err = l2_client.query(prompt)
            lat = int((time.perf_counter() - t2_start) * 1000)
            r2 = TierResult("L2", pred, conf, lat, raw=raw, error=err)
        results.append(r2)

        if verbose:
            print(f"[L2] {r2.prediction} (conf={r2.confidence:.2f}, lat={r2.latency_ms}ms)")

        # If L2 says safe and no anomalies detected, save L3 call
        if r2.prediction == "safe":
            return RoutingDecision.SAFE, results

        # ── Tier 3: Confirmer ────────────────────────────────────────────
        l3_cfg = self.thresholds["L3"]
        l3_client = make_client(l3_cfg)
        t3_start = time.perf_counter()

        if l3_client is None:
            r3 = TierResult("L3", "skipped", 0.0, 0, error="No L3 model configured")
        else:
            pred, conf, raw, err = l3_client.query(prompt)
            lat = int((time.perf_counter() - t3_start) * 1000)
            r3 = TierResult("L3", pred, conf, lat, raw=raw, error=err)
        results.append(r3)

        if verbose:
            print(f"[L3] {r3.prediction} (conf={r3.confidence:.2f}, lat={r3.latency_ms}ms)")

        # Final decision logic
        if r3.prediction == "unsafe":
            # L3 has 0% FPR — when it says unsafe, we believe it
            return RoutingDecision.UNSAFE, results
        elif r3.prediction == "safe":
            # L3 says safe, but L1/L2 said unsafe. L3 is conservative (20% recall).
            # If L1/L2 flagged it and L3 cleared it, we default to UNCERTAIN (human review)
            return RoutingDecision.UNCERTAIN, results
        else:
            # L3 error/uncertain — escalate to human / uncertain bin
            return RoutingDecision.UNCERTAIN, results

    def route(self, prompt: str, verbose: bool = False,
              file_data: Optional[bytes] = None,
              mcp_tool: Optional[Dict[str, Any]] = None,
              session_id: str = "",
              session_starter: Optional[str] = None,
              starter_source: str = "unknown") -> Dict[str, Any]:
        """High-level API returning a structured routing result.

        Args:
            session_id: Optional session identifier for CSI tracking.
            session_starter: Optional session starter content to verify (CSI defense).
            starter_source: Source of the starter (manual, template, marketplace).
        """
        # CSI guard check: verify session starter integrity (T2 defense)
        if session_starter and session_id and L0_EXTENDED_AVAILABLE:
            l0_cfg = self.thresholds.get("L0", {})
            csi_cfg = l0_cfg.get("csi_guard", {})
            if csi_cfg.get("enabled", True):
                csi_result = self._run_l0_csi(
                    session_id, session_starter, starter_source,
                )
                if csi_result and csi_result.prediction == "unsafe":
                    refusal = self._format_refusal()
                    return {
                        "prompt": prompt[:100],
                        "decision": RoutingDecision.UNSAFE,
                        "total_latency_ms": csi_result.latency_ms,
                        "refusal": refusal,
                        "tiers": [{
                            "tier": csi_result.tier,
                            "prediction": csi_result.prediction,
                            "confidence": csi_result.confidence,
                            "latency_ms": csi_result.latency_ms,
                            "raw": csi_result.raw,
                        }],
                    }

        # MCP guard check first if MCP invocation provided
        if mcp_tool and L0_EXTENDED_AVAILABLE:
            l0_cfg = self.thresholds.get("L0", {})
            mcp_cfg = l0_cfg.get("mcp_guard", {})
            if mcp_cfg.get("enabled", True):
                mcp_result = self._run_l0_mcp(
                    tool_name=mcp_tool.get("name", ""),
                    tool_desc=mcp_tool.get("description", ""),
                    args=mcp_tool.get("arguments", {}),
                    session_id=mcp_tool.get("session_id", ""),
                )
                if mcp_result and mcp_result.prediction == "unsafe":
                    refusal = self._format_refusal()
                    return {
                        "prompt": prompt[:100],
                        "decision": RoutingDecision.UNSAFE,
                        "total_latency_ms": mcp_result.latency_ms,
                        "refusal": refusal,
                        "tiers": [{
                            "tier": mcp_result.tier,
                            "prediction": mcp_result.prediction,
                            "confidence": mcp_result.confidence,
                            "latency_ms": mcp_result.latency_ms,
                            "raw": mcp_result.raw,
                        }],
                    }

        decision, tiers = self.classify(prompt, verbose=verbose, file_data=file_data)
        total_latency = sum(t.latency_ms for t in tiers if t.latency_ms > 0)

        # Apply uniform refusal protocol
        is_unsafe = decision == RoutingDecision.UNSAFE
        refusal = self._format_refusal() if is_unsafe else None
        sanitized_decision = self._sanitize_output(decision, is_rejection=is_unsafe)

        result = {
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "decision": sanitized_decision if is_unsafe else decision,
            "total_latency_ms": total_latency,
            "refusal": refusal,
            "tiers": [
                {
                    "tier": t.tier,
                    "prediction": t.prediction,
                    "confidence": t.confidence,
                    "latency_ms": t.latency_ms,
                    "error": t.error,
                }
                for t in tiers
            ],
            "routing_path": " -> ".join([t.tier for t in tiers]),
        }
        self.history.append(result)
        return result


# ── CLI / Debug ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="L0+L1+L2+L3 guard router")
    parser.add_argument("--prompt", required=True, help="Input prompt to classify")
    parser.add_argument("--steg-file", help="Optional file to scan for steganography")
    parser.add_argument("--config", help="Optional JSON config file for thresholds")
    parser.add_argument("--verbose", action="store_true", help="Print tier-by-tier decisions")
    parser.add_argument("--steer", action="store_true",
                        help="Enable decision-locator steering on L1")
    parser.add_argument("--no-l0", action="store_true", help="Disable L0 steg pre-processor")
    parser.add_argument("--mcp-tool", help="MCP tool invocation as JSON: {name,description,arguments,session_id}")
    parser.add_argument("--no-meta", action="store_true", help="Disable L0 meta-orchestrator")
    parser.add_argument("--no-encode", action="store_true", help="Disable L0 encoding guard")
    parser.add_argument("--no-mcp", action="store_true", help="Disable L0 MCP guard")
    parser.add_argument("--no-alsb", action="store_true", help="Disable L0 ALSB guard (T4 defense)")
    parser.add_argument("--no-csi", action="store_true", help="Disable L0 CSI guard (T2 defense)")
    parser.add_argument("--session-id", help="Session ID for CSI tracking")
    parser.add_argument("--session-starter", help="Session starter content to verify (CSI defense)")
    parser.add_argument("--starter-source", default="unknown", help="Source of session starter")
    args = parser.parse_args()

    thresholds = TIER_THRESHOLDS
    if args.config:
        with open(args.config, "r") as f:
            thresholds = json.load(f)

    if args.no_l0:
        thresholds.setdefault("L0", {})["enabled"] = False
    if args.no_meta:
        thresholds.setdefault("L0", {}).setdefault("meta_orchestrator", {})["enabled"] = False
    if args.no_encode:
        thresholds.setdefault("L0", {}).setdefault("encoding_guard", {})["enabled"] = False
    if args.no_mcp:
        thresholds.setdefault("L0", {}).setdefault("mcp_guard", {})["enabled"] = False
    if args.no_alsb:
        thresholds.setdefault("L0", {}).setdefault("alsb_guard", {})["enabled"] = False
    if args.no_csi:
        thresholds.setdefault("L0", {}).setdefault("csi_guard", {})["enabled"] = False

    if args.steer and thresholds.get("L1", {}).get("use_steering", False):
        thresholds["L1"]["backend"] = "steered"
        print("[!] L1 steering enabled (decision-locator + safetensors)")

    file_data = None
    if args.steg_file:
        with open(args.steg_file, "rb") as f:
            file_data = f.read()

    mcp_tool = None
    if args.mcp_tool:
        try:
            mcp_tool = json.loads(args.mcp_tool)
        except json.JSONDecodeError:
            print(f"[!] Invalid MCP tool JSON: {args.mcp_tool}")
            mcp_tool = None

    router = GuardRouter(thresholds=thresholds)
    result = router.route(
        args.prompt, verbose=args.verbose, file_data=file_data, mcp_tool=mcp_tool,
        session_id=args.session_id or "",
        session_starter=args.session_starter,
        starter_source=args.starter_source,
    )

    print()
    print(f"{'='*50}")
    print(f"FINAL DECISION: {result['decision'].upper()}")
    if result.get("refusal"):
        print(f"REFUSAL: {result['refusal']}")
    print(f"{'='*50}")
    print(f"Latency : {result['total_latency_ms']}ms")
    print(f"Path    : {result['routing_path']}")
    print()
    for t in result["tiers"]:
        status = "✓" if not t["error"] else "✗"
        print(f"  {status} {t['tier']}: {t['prediction']:10s} (conf={t['confidence']:.2f}, {t['latency_ms']}ms)")
        if t["error"]:
            print(f"      ERROR: {t['error']}")

    # Save history
    hist_file = "guard_router_history.jsonl"
    with open(hist_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"\n[+] Logged to {hist_file}")


if __name__ == "__main__":
    main()
