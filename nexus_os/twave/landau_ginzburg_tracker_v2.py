#!/usr/bin/env python3
"""
TWAVE v2.0 — Landau-Ginzburg Hallucination Tracker
====================================================
Upgraded with findings from 2024-2026 literature:
    - EDT (Entropy-based Dynamic Temperature) — T = T0 * N^(theta / H)
    - LEAD (Latent↔Discrete mode switching) — entropy-aware decoding mode
    - EPR (Entropy Production Rate) — black-box hallucination detection from top-K log-probs
    - LED (Latent Exploration Decoding) — layer-wise entropy reservoir exploitation
    - CK-PLUG — retrieval chemical potential μ_ret via Confidence Gain
    - Attention Divergence — white-box focus-intensity probe

Designed for: Transformers, vLLM, llama.cpp, MLX, black-box APIs.

References:
    - EDT: arXiv:2403.14541
    - LEAD: arXiv:2603.13366 (CVPR 2026)
    - EPR: arXiv:2509.04492 (ECIR 2026)
    - LED: arXiv:2602.01698 (ICML 2026)
    - CK-PLUG: arXiv:2503.15888
"""
from __future__ import annotations
import math, random, argparse
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
import numpy as np

# Config
DEFAULT_T_C = {
    "F1.1": 0.85, "F1.2": 0.80, "F1.3": 0.75,
    "R2.1": 0.65, "R2.2": 0.60, "R2.3": 0.55,
    "RAG7.1": 0.70, "RAG7.2": 0.70, "RAG7.3": 0.65, "RAG7.6": 0.60,
    "A5.1": 0.75, "A5.3": 0.70, "A5.7": 0.65, "A5.14": 0.60,
    "S4.6": 1.25, "S4.11": 1.20, "S4.12": 1.15, "S4.2": 1.10,
    "J8.1": 0.90, "J8.2": 0.85, "D11.3": 0.70, "T9.1": 0.75,
    "D11.1": 0.50, "D11.2": 0.55, "default": 0.75,
}
DEFAULT_WEIGHTS = {
    "F1.1": (0.50, 0.15, 0.15, 0.20), "F1.2": (0.45, 0.20, 0.15, 0.20),
    "R2.1": (0.40, 0.25, 0.20, 0.15), "R2.2": (0.35, 0.30, 0.20, 0.15),
    "RAG7.1": (0.40, 0.20, 0.20, 0.20), "RAG7.3": (0.45, 0.15, 0.25, 0.15),
    "A5.1": (0.30, 0.20, 0.30, 0.20), "S4.6": (0.25, 0.20, 0.30, 0.25),
    "J8.1": (0.30, 0.30, 0.25, 0.15), "D11.1": (0.55, 0.10, 0.15, 0.20),
    "D11.3": (0.45, 0.15, 0.25, 0.15), "T9.1": (0.40, 0.25, 0.20, 0.15),
    "default": (0.40, 0.20, 0.20, 0.20),
}

EDT_N_BASE, EDT_THETA, EDT_T0_MAX = 0.8, 1.0, 1.2
LEAD_PERSISTENCE_D_TO_L, LEAD_C_MAX = 3, 10
EPR_K, LED_K, LED_D, LED_EXPLOIT_THRESHOLD = 10, 16, 5, 0.9

class DecodingMode(Enum):
    DISCRETE = "discrete"; LATENT = "latent"; EXPLORE = "explore"; ABSTAIN = "abstain"

@dataclass
class OrderParameters:
    position: int; entropy: float; attention_mass: float; reward_density: float
    critique_confidence: float; top2_ratio: float; hidden_norm: float
    retrieval_score: Optional[float] = None
    layer_entropies: Optional[List[float]] = None
    attention_divergence: Optional[float] = None

@dataclass
class LandauGinzburgState:
    position: int; free_energy: float; effective_temperature: float
    specific_heat: float; correlation_length: float
    is_critical: bool; is_hallucinating: bool

@dataclass
class TrackerReport:
    category: str; t_c: float; tokens_generated: int
    order_parameters: List[OrderParameters]; lg_states: List[LandauGinzburgState]
    cooling_events: List[Dict[str, Any]]; final_temperature: float
    hallucination_detected: bool; hallucination_positions: List[int]
    self_correction_positions: List[int]; mean_entropy: float; max_entropy: float
    entropy_variance: float; estimated_healing_length: Optional[float] = None
    epr_score: Optional[float] = None
    mode_transitions: Optional[List[Tuple[int, DecodingMode, DecodingMode]]] = None
    led_depth_selected: Optional[List[int]] = None
    edt_temperature_schedule: Optional[List[float]] = None
    stability_report: Optional[Dict[str, Any]] = None

# ---- EDT ----
class EDTController:
    def __init__(self, T0=1.0, N_base=EDT_N_BASE, theta=EDT_THETA, T_max=EDT_T0_MAX):
        self.T0, self.N_base, self.theta, self.T_max = T0, N_base, theta, T_max
    def compute(self, entropy, min_T=0.01):
        if entropy <= 0: return self.T0
        T = self.T0 * (self.N_base ** (self.theta / entropy))
        return float(np.clip(T, min_T, self.T_max))
    def anneal(self, position, total_tokens, T_max=1.2, T_min=0.1, d=25):
        return T_max - (T_max - T_min) * (position / d) if position < d else T_min

# ---- LEAD ----
class LEADSwitching:
    def __init__(self, W_D_to_L=LEAD_PERSISTENCE_D_TO_L, C_max=LEAD_C_MAX,
                 auto_threshold_window=5, auto_threshold_percentile=75.0):
        self.W_D_to_L, self.C_max = W_D_to_L, C_max
        self.auto_threshold_window, self.auto_threshold_percentile = auto_threshold_window, auto_threshold_percentile
        self._mode = DecodingMode.DISCRETE
        self._persistence_count = 0; self._switch_count = 0
        self._ref_entropy = 0.0; self._entropy_history: List[float] = []
        self._transitions: List[Tuple[int, DecodingMode, DecodingMode]] = []
    @property
    def current_mode(self): return self._mode
    @property
    def transitions(self): return self._transitions.copy()
    def _compute_threshold(self):
        if len(self._entropy_history) < self.auto_threshold_window: return 1.0
        recent = self._entropy_history[-self.auto_threshold_window:]
        return float(np.percentile(recent, self.auto_threshold_percentile))
    def step(self, position, entropy):
        self._entropy_history.append(entropy)
        ref_H = self._compute_threshold()
        g_D = 1 if entropy < ref_H else 0
        g_L = 1 if (entropy > ref_H and self._persistence_count >= self.W_D_to_L) else 0
        old_mode = self._mode
        if g_D and self._mode != DecodingMode.DISCRETE:
            self._mode = DecodingMode.DISCRETE; self._persistence_count = 0
            self._switch_count += 1; self._ref_entropy = entropy
        elif g_L and self._switch_count < self.C_max and self._mode != DecodingMode.LATENT:
            self._mode = DecodingMode.LATENT; self._persistence_count = 0
            self._switch_count += 1; self._ref_entropy = entropy
        else:
            self._persistence_count += 1
        if self._mode != old_mode:
            self._transitions.append((position, old_mode, self._mode))
        return self._mode

# ---- EPR ----
class EPRDetector:
    def __init__(self, K=EPR_K): self.K = K; self._entropies: List[float] = []
    def compute_topk_entropy(self, topk_probs):
        topk_probs = np.clip(topk_probs, 1e-10, 1.0)
        return float(-np.sum(topk_probs * np.log2(topk_probs)))
    def compute_epr(self, temperature=1.0):
        if not self._entropies: return 0.0
        raw = float(np.mean(self._entropies))
        return raw / temperature if temperature > 0 else raw
    def step(self, topk_probs, temperature=1.0):
        H_t = self.compute_topk_entropy(topk_probs)
        self._entropies.append(H_t)
        return H_t, self.compute_epr(temperature)
    def is_hallucination_risk(self, threshold=2.5, temperature=1.0):
        return self.compute_epr(temperature) > threshold
    def reset(self): self._entropies.clear()

# ---- LED ----
class LEDExplorer:
    def __init__(self, k=LED_K, d=LED_D, exploit_threshold=LED_EXPLOIT_THRESHOLD):
        self.k, self.d, self.exploit_threshold = k, d, exploit_threshold
    def select_depth(self, layer_logits):
        if not layer_logits or len(layer_logits) < 2: return 0
        final_logits = layer_logits[-1]
        topk_idx = np.argsort(final_logits)[-self.k:]
        filtered = [logits[topk_idx] for logits in layer_logits]
        best_depth, best_entropy = 0, -1.0
        for start_idx in range(len(filtered)):
            cumsum = np.sum(filtered[start_idx:], axis=0)
            agg = cumsum / (cumsum.sum() + 1e-10)
            H = float(-np.sum(agg * np.log(agg + 1e-10)))
            if H > best_entropy: best_entropy, best_depth = H, start_idx
        return best_depth
    def exploit_or_explore(self, final_max_prob):
        return "exploit" if final_max_prob > self.exploit_threshold else "explore"

# ---- CK-PLUG ----
class CKPlugCoupler:
    def __init__(self, alpha=0.5, conflict_threshold=-0.1, support_threshold=0.1,
                 boundary_epsilon=0.05, adaptive_alpha=True, adaptive_aggressiveness=0.3,
                 temperature_respect=True, enable_diagnostics=True):
        self.alpha = alpha; self.conflict_threshold = conflict_threshold
        self.support_threshold = support_threshold; self.boundary_epsilon = boundary_epsilon
        self.adaptive_alpha = adaptive_alpha; self.adaptive_aggressiveness = adaptive_aggressiveness
        self.temperature_respect = temperature_respect; self.enable_diagnostics = enable_diagnostics
        self._diagnostics: List[Dict[str, Any]] = []
    def compute_entropy(self, logits):
        log_probs = logits - np.max(logits)
        probs = np.exp(log_probs); probs = probs / (np.sum(probs) + 1e-10)
        return float(-np.sum(probs * np.log(probs + 1e-10)))
    def compute_cg(self, logits_parametric, logits_retrieval):
        h_p = self.compute_entropy(logits_parametric); h_r = self.compute_entropy(logits_retrieval)
        return h_p - h_r, h_p, h_r
    def compute_effective_alpha(self, cg, current_temperature=0.7, base_alpha=None):
        base = base_alpha if base_alpha is not None else self.alpha
        if not self.adaptive_alpha: return base
        if cg < self.conflict_threshold: shift = -self.adaptive_aggressiveness * abs(cg)
        elif cg > self.support_threshold: shift = self.adaptive_aggressiveness * cg
        else: shift = 0.0
        alpha_eff = base + shift
        if self.temperature_respect and current_temperature > 0.8:
            if alpha_eff > base: alpha_eff = base + (alpha_eff - base) * 0.5
            elif alpha_eff < base: alpha_eff = base + (alpha_eff - base) * 1.2
        return float(np.clip(alpha_eff, 0.0, 1.0))
    def modulate(self, logits_parametric, logits_retrieval, position=0,
                 token_id=None, current_temperature=0.7, base_alpha=None):
        cg, h_p, h_r = self.compute_cg(logits_parametric, logits_retrieval)
        alpha_eff = self.compute_effective_alpha(cg, current_temperature, base_alpha)
        log_p_p = logits_parametric - np.max(logits_parametric)
        log_p_r = logits_retrieval - np.max(logits_retrieval)
        modulated = (1 - alpha_eff) * log_p_p + alpha_eff * log_p_r
        diag = None
        if self.enable_diagnostics:
            diag = {
                "position": position, "token_id": token_id or -1,
                "cg": round(cg, 4), "h_parametric": round(h_p, 4),
                "h_retrieval": round(h_r, 4),
                "is_conflict": cg < self.conflict_threshold,
                "is_support": cg > self.support_threshold,
                "is_boundary": abs(cg) < self.boundary_epsilon,
                "alpha_applied": round(alpha_eff, 3),
            }
            self._diagnostics.append(diag)
        return modulated, diag
    def to_mu_ret(self, cg, current_temperature=0.7):
        mu_base = np.tanh(cg * 2.0)
        if self.temperature_respect:
            temp_factor = max(0.3, 1.0 - current_temperature * 0.5)
            mu_base *= temp_factor
        return float(mu_base)
    def reset(self): self._diagnostics.clear()

# ---- Main Tracker ----
class LandauGinzburgTrackerV2:
    def __init__(self, category="default", t_c=None, weights=None,
                 safety_margin=0.15, cooling_mode="moderate",
                 enable_edt=True, enable_lead=True, enable_epr=True,
                 enable_led=False, enable_ckplug=False, enable_attention_divergence=False,
                 edt_T0=1.0, edt_theta=EDT_THETA,
                 lead_W=LEAD_PERSISTENCE_D_TO_L, lead_C_max=LEAD_C_MAX,
                 epr_K=EPR_K, epr_threshold=2.5,
                 led_k=LED_K, led_d=LED_D,
                 ckplug_alpha=0.5,
                 on_cooling=None, on_hallucination=None, on_mode_switch=None):
        self.category = category
        self.t_c = t_c if t_c is not None else DEFAULT_T_C.get(category, DEFAULT_T_C["default"])
        self.weights = weights if weights is not None else DEFAULT_WEIGHTS.get(category, DEFAULT_WEIGHTS["default"])
        self.safety_margin = safety_margin
        self.cooling_factor = {"gentle": 0.95, "moderate": 0.85, "aggressive": 0.70}.get(cooling_mode, 0.85)
        self.enable_edt = enable_edt; self.enable_lead = enable_lead; self.enable_epr = enable_epr
        self.enable_led = enable_led; self.enable_ckplug = enable_ckplug
        self.enable_attention_divergence = enable_attention_divergence
        self.edt = EDTController(T0=edt_T0, theta=edt_theta) if enable_edt else None
        self.lead = LEADSwitching(W_D_to_L=lead_W, C_max=lead_C_max) if enable_lead else None
        self.epr = EPRDetector(K=epr_K) if enable_epr else None
        self.led = LEDExplorer(k=led_k, d=led_d) if enable_led else None
        self.ckplug = CKPlugCoupler(alpha=ckplug_alpha) if enable_ckplug else None
        self.epr_threshold = epr_threshold
        self.on_cooling = on_cooling; self.on_hallucination = on_hallucination; self.on_mode_switch = on_mode_switch
        self._order_params: List[OrderParameters] = []
        self._lg_states: List[LandauGinzburgState] = []
        self._cooling_events: List[Dict[str, Any]] = []
        self._current_temperature = 0.7; self._base_temperature = 0.7
        self._hallucination_positions: List[int] = []
        self._self_correction_positions: List[int] = []
        self._tokens_since_cooling = 0
        self._is_dry_run = False
        self._mode_history: List[Tuple[int, DecodingMode]] = []
        self._led_depths: List[int] = []
        self._edt_schedule: List[float] = []

    def step(self, position=0, logits=None, current_temperature=0.7,
             hidden_state=None, attention_weights=None, reward_logit=None,
             critique_logit=None, topk_probs=None, layer_logits=None,
             logits_parametric=None, logits_retrieval=None,
             attention_kl_divergence=None):
        self._current_temperature = current_temperature
        if position == 0: self._base_temperature = current_temperature
        epr_score = None
        if self.enable_epr and topk_probs is not None:
            _, epr_score = self.epr.step(topk_probs, current_temperature)
        op = self._compute_order_parameters(position, logits, hidden_state,
            attention_weights, reward_logit, critique_logit, layer_logits, attention_kl_divergence)
        self._order_params.append(op)
        led_depth, led_action = 0, "exploit"
        if self.enable_led and layer_logits is not None:
            led_depth = self.led.select_depth(layer_logits)
            final_max = self._max_prob_from_logits(layer_logits[-1]) if layer_logits else 1.0
            led_action = self.led.exploit_or_explore(final_max)
            self._led_depths.append(led_depth)
        ckplug_diag = None; mu_ret = 0.0
        if self.enable_ckplug and logits_parametric is not None and logits_retrieval is not None:
            _, ckplug_diag = self.ckplug.modulate(logits_parametric, logits_retrieval,
                position=position, current_temperature=current_temperature)
            mu_ret = self.ckplug.to_mu_ret(ckplug_diag["cg"], current_temperature) if ckplug_diag else 0.0
        lg = self._compute_landau_ginzburg(op, current_temperature, mu_ret)
        self._lg_states.append(lg)
        mode = DecodingMode.DISCRETE
        if self.enable_lead:
            mode = self.lead.step(position, op.entropy)
            if self.on_mode_switch and self.lead.transitions:
                latest = self.lead.transitions[-1]
                self._mode_history.append((latest[0], latest[2]))
                self.on_mode_switch(*latest)
        edt_T = current_temperature
        if self.enable_edt:
            edt_T = self.edt.compute(op.entropy)
            edt_T = 0.7 * current_temperature + 0.3 * edt_T
            self._edt_schedule.append(edt_T)
        action = self._determine_action_v2(op, lg, position, epr_score, mode, edt_T, led_action)
        if action["cool"] and self.on_cooling:
            self.on_cooling(position, current_temperature, action["t_eff"])
        if lg.is_hallucinating and self.on_hallucination:
            self.on_hallucination(position, f"T_eff={lg.effective_temperature:.3f} > T_c={self.t_c:.3f}")
        if len(self._order_params) >= 2:
            prev_op = self._order_params[-2]
            if prev_op.entropy > np.mean([p.entropy for p in self._order_params[:-1]]) + 1.0:
                if op.entropy < prev_op.entropy * 0.7:
                    self._self_correction_positions.append(position)
        return action

    def _compute_order_parameters(self, position, logits, hidden_state,
        attention_weights, reward_logit, critique_logit, layer_logits, attention_kl_divergence):
        if logits is not None and not self._is_dry_run:
            entropy, top2_ratio = self._entropy_from_logits(logits)
        else:
            entropy = self._dry_run_entropy(position)
            top2_ratio = math.exp(2.0)
        layer_entropies = None
        if layer_logits is not None and not self._is_dry_run:
            layer_entropies = [self._entropy_from_logits(l)[0] for l in layer_logits]
        attention_div = attention_kl_divergence
        if attention_div is None and attention_weights is not None and not self._is_dry_run:
            attention_div = float(np.sum(attention_weights ** 2)) if hasattr(attention_weights, '__array__') else 0.5
        attention_mass = 1.0 / (position + 1)
        if attention_weights is not None and not self._is_dry_run and hasattr(attention_weights, '__array__'):
            attention_mass = float(np.sum(attention_weights))
        reward_density = 1.0 / (1.0 + math.exp(-reward_logit)) if reward_logit is not None and not self._is_dry_run else (0.5 + 0.3 * math.sin(position * 0.1))
        critique_confidence = 1.0 / (1.0 + math.exp(-critique_logit)) if critique_logit is not None and not self._is_dry_run else (0.3 + 0.2 * math.sin(position * 0.15))
        hidden_norm = float(np.linalg.norm(hidden_state)) if hidden_state is not None and not self._is_dry_run and hasattr(hidden_state, '__array__') else (25.0 + 5.0 * math.sin(position * 0.05))
        return OrderParameters(position, entropy, attention_mass, reward_density,
            critique_confidence, top2_ratio, hidden_norm,
            layer_entropies=layer_entropies, attention_divergence=attention_div)

    @staticmethod
    def _entropy_from_logits(logits):
        log_probs = logits - np.max(logits)
        probs = np.exp(log_probs); probs = probs / (np.sum(probs) + 1e-10)
        entropy = float(-np.sum(probs * np.log(probs + 1e-10)))
        sorted_logits = np.sort(logits)
        top2 = float(np.exp(sorted_logits[-1] - sorted_logits[-2])) if len(sorted_logits) >= 2 else 1.0
        return entropy, top2

    @staticmethod
    def _max_prob_from_logits(logits):
        log_probs = logits - np.max(logits)
        probs = np.exp(log_probs); probs = probs / (np.sum(probs) + 1e-10)
        return float(np.max(probs))

    def _dry_run_entropy(self, position):
        seed = position * 1000 + int(self._current_temperature * 1000) + int(self.t_c * 100)
        random.seed(seed); np.random.seed(seed)
        base = 0.2 + 0.015 * position
        temp_effect = (self._current_temperature - 0.3) * 1.0
        proximity = self._current_temperature - self.t_c
        spike_prob, spike_mag = 0.0, 0.0
        if proximity >= 0.3: spike_prob, spike_mag = 0.35, 1.2 + 0.8 * self._current_temperature
        elif proximity >= 0.0: spike_prob = 0.12 + 0.23 * (proximity / 0.3); spike_mag = 0.8 + 0.6 * proximity
        elif proximity >= -0.15: spike_prob, spike_mag = 0.05, 0.4
        spike = 0.0
        if random.random() < spike_prob and position > 3: spike = spike_mag * random.random()
        variance_boost = 0.0
        if abs(self._current_temperature - self.t_c) < 0.10: variance_boost = 0.3 * random.random()
        return base + temp_effect + spike + variance_boost + np.random.normal(0, 0.03)

    def _compute_landau_ginzburg(self, op, current_temperature, mu_ret=0.0):
        alpha, beta, gamma, delta = self.weights
        phi = np.array([op.entropy, op.attention_mass, op.reward_density, op.critique_confidence])
        free_energy = alpha * phi[0]**2 + beta * phi[1]**2 + gamma * phi[2]**2 + delta * phi[3]**2
        if op.retrieval_score is not None: free_energy -= mu_ret * op.retrieval_score * op.entropy
        if op.attention_divergence is not None: free_energy -= 0.1 * op.attention_divergence * phi[0]
        t_eff = current_temperature * (1.0 + 0.1 * free_energy)
        specific_heat = 0.0
        if len(self._lg_states) >= 2:
            prev = self._lg_states[-1].effective_temperature
            prev2 = self._lg_states[-2].effective_temperature if len(self._lg_states) >= 2 else prev
            d2 = (t_eff - 2 * prev + prev2)
            specific_heat = abs(d2) * 10.0
        xi = 1.0 + 2.0 * (abs(op.entropy - self._order_params[-1].entropy) if len(self._order_params) >= 2 else 0.0)
        is_critical = abs(t_eff - self.t_c) < 0.05
        is_hallucinating = (t_eff > self.t_c) and (specific_heat > 2.0)
        return LandauGinzburgState(op.position, free_energy, t_eff, specific_heat, xi, is_critical, is_hallucinating)

    def _determine_action_v2(self, op, lg, position, epr_score, lead_mode, edt_temperature, led_action):
        trigger, cool, watch, risk, t_eff = "none", False, False, 0.0, self._current_temperature
        mode = lead_mode
        if self.enable_epr and epr_score is not None and epr_score > self.epr_threshold:
            watch = True; risk = max(risk, min(1.0, epr_score / 5.0)); trigger = "epr_high"
            if epr_score > self.epr_threshold * 1.5:
                cool = True; t_eff = max(0.1, self._current_temperature * 0.7)
                mode = DecodingMode.ABSTAIN if position > 5 else DecodingMode.DISCRETE
                trigger = "epr_critical"
        if position > 0:
            prev = self._order_params[-2].entropy if len(self._order_params) >= 2 else 0.0
            delta = op.entropy - prev
            if delta > 1.0:
                watch = True; risk = max(risk, min(1.0, delta / 3.0))
                if trigger == "none": trigger = "entropy_spike"
        if lg.is_critical:
            watch = True; risk = max(risk, 0.5)
            if self._tokens_since_cooling > 3:
                cool = True; t_eff = max(0.1, self._current_temperature * self.cooling_factor)
                self._tokens_since_cooling = 0
                self._cooling_events.append({"position": position, "reason": "near_t_c",
                    "old_temp": self._current_temperature, "new_temp": t_eff, "free_energy": lg.free_energy})
            else: self._tokens_since_cooling += 1
        else: self._tokens_since_cooling += 1
        if lg.specific_heat > 4.0:
            watch = True; risk = max(risk, 0.8); cool = True
            t_eff = max(0.1, self._current_temperature * 0.70)
            trigger = "specific_heat_anomaly"
            self._cooling_events.append({"position": position, "reason": "specific_heat_anomaly",
                "old_temp": self._current_temperature, "new_temp": t_eff, "specific_heat": lg.specific_heat})
        if lg.is_hallucinating:
            risk, trigger, cool, t_eff = 1.0, "hallucination_confirmed", True, 0.0
            mode = DecodingMode.ABSTAIN
            self._hallucination_positions.append(position)
            self._cooling_events.append({"position": position, "reason": "hallucination_confirmed",
                "old_temp": self._current_temperature, "new_temp": 0.0,
                "t_eff": lg.effective_temperature, "t_c": self.t_c})
        if self.enable_edt and not cool: t_eff = edt_temperature
        if self.enable_led and led_action == "explore" and mode != DecodingMode.ABSTAIN: mode = DecodingMode.EXPLORE
        if self.enable_lead and mode != DecodingMode.ABSTAIN: mode = lead_mode
        return {
            "cool": cool, "t_eff": round(t_eff, 3), "mode": mode.value,
            "watch": watch, "hallucination_risk": round(risk, 2),
            "trigger": trigger,
            "order_params": {"entropy": op.entropy, "attention_mass": op.attention_mass,
                "reward_density": op.reward_density, "critique_confidence": op.critique_confidence,
                "top2_ratio": op.top2_ratio, "layer_entropies": op.layer_entropies,
                "attention_divergence": op.attention_divergence},
            "free_energy": round(lg.free_energy, 3),
            "effective_temperature": round(lg.effective_temperature, 3),
            "is_critical": lg.is_critical, "is_hallucinating": lg.is_hallucinating,
            "ep_r": round(epr_score, 3) if epr_score is not None else None,
            "led_depth": self._led_depths[-1] if self._led_depths else None,
            "ckplug_diag": None,
        }

    def set_dry_run(self, enabled=True): self._is_dry_run = enabled

    def get_report(self, *, apply_spectral_bounds: bool = False):
        entropies = [op.entropy for op in self._order_params]
        # P2.2 (LoopWM): optional spectral bound. Default off; no behavior change.
        stability_report = None
        if apply_spectral_bounds and self._lg_states:
            try:
                from nexus_os.twave.spectral_stability import (
                    SpectralBounds,
                    bound_effective_temperature,
                )
                series = [s.effective_temperature for s in self._lg_states]
                bounded = bound_effective_temperature(series, bounds=SpectralBounds())
                pre_max = max((abs(x) for x in series), default=0.0)
                post_max = max((abs(x) for x in bounded), default=0.0)
                # Overlay: mutate the LG states so downstream reads see bounded values.
                for st, v in zip(self._lg_states, bounded):
                    st.effective_temperature = v
                self._current_temperature = bounded[-1] if bounded else self._current_temperature
                stability_report = {
                    "applied": True,
                    "states_adjusted": len(bounded),
                    "pre_max_abs": round(pre_max, 4),
                    "post_max_abs": round(post_max, 4),
                    "t_low": SpectralBounds().t_low,
                    "t_high": SpectralBounds().t_high,
                }
            except Exception:
                stability_report = {"applied": False, "error": "import_or_apply_failed"}
        return TrackerReport(
            category=self.category, t_c=self.t_c,
            tokens_generated=len(self._order_params),
            order_parameters=self._order_params,
            lg_states=self._lg_states,
            cooling_events=self._cooling_events,
            final_temperature=self._current_temperature,
            hallucination_detected=len(self._hallucination_positions) > 0,
            hallucination_positions=self._hallucination_positions,
            self_correction_positions=self._self_correction_positions,
            mean_entropy=float(np.mean(entropies)) if entropies else 0.0,
            max_entropy=float(np.max(entropies)) if entropies else 0.0,
            entropy_variance=float(np.var(entropies)) if len(entropies) > 1 else 0.0,
            estimated_healing_length=self._estimate_healing_length(),
            epr_score=self.epr.compute_epr(self._current_temperature) if self.enable_epr and self.epr else None,
            mode_transitions=self.lead.transitions if self.enable_lead and self.lead else None,
            led_depth_selected=self._led_depths if self._led_depths else None,
            edt_temperature_schedule=self._edt_schedule if self._edt_schedule else None,
            stability_report=stability_report,
        )

    def reset(self):
        self._order_params.clear(); self._lg_states.clear(); self._cooling_events.clear()
        self._hallucination_positions.clear(); self._self_correction_positions.clear()
        self._current_temperature = 0.7; self._base_temperature = 0.7
        self._tokens_since_cooling = 0
        self._mode_history.clear(); self._led_depths.clear(); self._edt_schedule.clear()
        if self.epr: self.epr.reset()
        if self.ckplug: self.ckplug.reset()

    def _estimate_healing_length(self):
        if not self._hallucination_positions or not self._self_correction_positions: return None
        healing = []
        for h in self._hallucination_positions:
            for c in self._self_correction_positions:
                if c > h: healing.append(c - h); break
        return float(np.mean(healing)) if healing else None

    def logits_processor(self):
        try: from transformers import LogitsProcessor
        except ImportError: raise ImportError("transformers not installed.")
        class _LGLogitsProcessor(LogitsProcessor):
            def __init__(self, tracker): self.tracker = tracker; self._token_idx = 0; self._current_temp = 0.7
            def __call__(self, input_ids, scores):
                logits = scores[0].cpu().numpy() if hasattr(scores, 'cpu') else np.array(scores[0])
                action = self.tracker.step(position=self._token_idx, logits=logits, current_temperature=self._current_temp)
                if action["cool"]:
                    # Cooling sharpens the distribution: scale logits by
                    # prev_temp/new_temp (>1 when cooling). The old code
                    # mutated _current_temp first, making the ratio 1.0
                    # (cooling no-op) — except ABSTAIN (t_eff=0), which
                    # multiplied every logit by 0 and turned a detected
                    # hallucination into uniform random sampling. Floor
                    # the new temperature instead of zeroing.
                    new_temp = max(action["t_eff"], 0.01)
                    scale_factor = self._current_temp / new_temp
                    scores = scores * scale_factor
                    self._current_temp = new_temp
                self._token_idx += 1
                return scores
        return _LGLogitsProcessor(self)

    def black_box_step(self, position, topk_probs, temperature=1.0):
        if not self.enable_epr: raise ValueError("EPR must be enabled for black-box mode")
        _, epr_score = self.epr.step(topk_probs, temperature)
        risk = min(1.0, epr_score / self.epr_threshold) if epr_score else 0.0
        watch = epr_score > self.epr_threshold if epr_score else False
        cool = epr_score > self.epr_threshold * 1.5 if epr_score else False
        return {
            "cool": cool, "t_eff": 0.0 if cool else temperature,
            "mode": "ABSTAIN" if cool else "DISCRETE",
            "watch": watch, "hallucination_risk": round(risk, 2),
            "trigger": "epr_critical" if cool else ("epr_high" if watch else "none"),
            "ep_r": round(epr_score, 3) if epr_score else None,
        }


def demo():
    print("=" * 70)
    print("TWAVE v2.0 — Landau-Ginzburg Tracker with EDT + LEAD + EPR")
    print("=" * 70)
    tracker = LandauGinzburgTrackerV2(category="F1.1", enable_edt=True, enable_lead=True,
        enable_epr=True, enable_ckplug=False)
    tracker.set_dry_run(True)
    print(f"[INIT] Category: F1.1, T_c: {tracker.t_c}, EDT: ON, LEAD: ON, EPR: ON")
    for i in range(30):
        action = tracker.step(i, current_temperature=0.7)
        mode_icon = {"discrete": "D", "latent": "L", "explore": "E", "abstain": "A"}[action["mode"]]
        if action["cool"]:
            print(f"[T={i:02d}] COOL  mode={mode_icon} T->{action['t_eff']:.3f} (trigger: {action['trigger']})")
        elif action["watch"]:
            print(f"[T={i:02d}] WATCH mode={mode_icon} risk={action['hallucination_risk']:.2f} H={action['order_params']['entropy']:.2f}")
        elif action["is_hallucinating"]:
            print(f"[T={i:02d}] HALLUC mode={mode_icon} T_eff={action['effective_temperature']:.3f}")
        else:
            if i % 5 == 0:
                print(f"[T={i:02d}] OK    mode={mode_icon} H={action['order_params']['entropy']:.2f} T_eff={action['effective_temperature']:.2f}")
    report = tracker.get_report()
    print()
    print("=" * 70)
    print("REPORT")
    print("=" * 70)
    print(f"Tokens: {report.tokens_generated}")
    print(f"Hallucination: {report.hallucination_detected} (positions: {report.hallucination_positions})")
    print(f"Self-corrections: {report.self_correction_positions}")
    print(f"Cooling events: {len(report.cooling_events)}")
    print(f"Mean entropy: {report.mean_entropy:.3f}")
    print(f"Max entropy: {report.max_entropy:.3f}")
    print(f"Entropy variance: {report.entropy_variance:.3f}")
    print(f"EPR score: {report.epr_score:.3f}" if report.epr_score else "EPR: N/A")
    print(f"Mode transitions: {report.mode_transitions}") if report.mode_transitions else ""
    print(f"Healing length: {report.estimated_healing_length}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TWAVE v2.0")
    parser.add_argument("--category", default="F1.1")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--tokens", type=int, default=30)
    args = parser.parse_args()
    demo()
