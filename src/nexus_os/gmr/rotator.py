"""GMR Core Rotation Engine"""
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from .telemetry import TelemetryIngest
from .domain_mapping import DOMAIN_MAPPING
from .savings import SavingsTracker

logger = logging.getLogger(__name__)

@dataclass
class ContextPacket:
    task_id: str
    original_prompt: str
    intent: str
    budget_remaining: int
    core_facts: List[str]
    decisions_made: List[Dict]
    pending_actions: List[str]
    handoff_count: int = 0
    trace_id: Optional[str] = None

@dataclass
class GMRSelection:
    primary: str
    fallbacks: List[str]
    estimated_cost: float
    estimated_latency_ms: int
    tier_used: int
    reason: str

class CircuitBreaker:
    def __init__(self):
        self.failures = {}
        self.cooldowns = {}
    
    def should_open(self, model: str) -> bool:
        if model in self.cooldowns and time.time() < self.cooldowns[model]: return True
        return False
        
    def record_failure(self, model: str):
        self.failures[model] = self.failures.get(model, 0) + 1
        if self.failures[model] >= 3:
            self.cooldowns[model] = time.time() + 60
            logger.warning(f"Circuit opened for {model}")

class GeniusModelRotator:
    def __init__(self, telemetry: TelemetryIngest):
        self.telemetry = telemetry
        self.circuit_breaker = CircuitBreaker()
        self.savings = SavingsTracker()
    
    def select(self, task_type: str, budget_remaining: int = 100000, required_tier: Optional[int] = None) -> GMRSelection:
        self.telemetry.fetch()
        domain = DOMAIN_MAPPING.get(task_type, DOMAIN_MAPPING["general"])
        
        candidates = []
        for model_spec in domain["primary"]:
            name = model_spec["model"]
            tier = model_spec.get("tier", 0)
            
            if required_tier and tier < required_tier: continue
            if self.circuit_breaker.should_open(name): continue
            
            tel = self.telemetry.cache.get(name)
            if tel and not tel.is_available: continue
            
            # Budget constraint: If broke, force local tier
            if budget_remaining < 50000 and tier > 50: continue
            
            candidates.append(model_spec)
            
        if not candidates:
            # Extreme fallback
            primary = domain["fallback_chain"][0]
            return GMRSelection(primary, domain["fallback_chain"][1:], 0.0, 9999, 40, "Emergency fallback")
            
        # Sort by cost (asc), then latency (asc)
        candidates.sort(key=lambda x: (x.get("cost_per_1m", 0), x.get("latency_ms", 9999)))
        primary = candidates[0]["model"]
        fallbacks = [c["model"] for c in candidates[1:]] + domain["fallback_chain"]
        
        return GMRSelection(
            primary=primary, 
            fallbacks=list(dict.fromkeys(fallbacks)), 
            estimated_cost=candidates[0].get("cost_per_1m", 0), 
            estimated_latency_ms=candidates[0].get("latency_ms", 0),
            tier_used=candidates[0].get("tier", 40),
            reason=f"domain={task_type}, tier={candidates[0].get('tier', 40)}"
        )
