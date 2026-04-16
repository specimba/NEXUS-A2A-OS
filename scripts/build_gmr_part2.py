#!/usr/bin/env python3
"""Phase 1: GMR Core Builder (Part 2)"""
import os

GMR_DIR = os.path.join("src", "nexus_os", "gmr")

FILES = {}

FILES["savings.py"] = r'''"""GMR Token Savings Tracker"""
import threading
from datetime import datetime, timezone
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class TokenSavings:
    timestamp: str
    task_type: str
    primary_model: str
    fallback_model: str
    tokens_used: int
    tokens_saved: int
    cost_saved: float
    reason: str

class SavingsTracker:
    def __init__(self):
        self.savings: List[TokenSavings] = []
        self.total_tokens_used = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0
        self.lock = threading.Lock()
    
    def record(self, task_type: str, primary: str, fallback: str, tokens_used: int, tokens_saved: int, cost_saved: float, reason: str):
        with self.lock:
            saving = TokenSavings(
                timestamp=datetime.now(timezone.utc).isoformat(),
                task_type=task_type, primary_model=primary, fallback_model=fallback,
                tokens_used=tokens_used, tokens_saved=tokens_saved, cost_saved=cost_saved, reason=reason
            )
            self.savings.append(saving)
            self.total_tokens_used += tokens_used
            self.total_tokens_saved += tokens_saved
            self.total_cost_saved += cost_saved
    
    def get_report(self) -> Dict:
        with self.lock:
            rate = (self.total_tokens_saved / max(self.total_tokens_used, 1)) * 100
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_tokens_used": self.total_tokens_used,
                    "total_tokens_saved": self.total_tokens_saved,
                    "total_cost_saved": round(self.total_cost_saved, 4),
                    "savings_rate": rate,
                },
                "recent_savings": [{"task": s.task_type, "saved": s.tokens_saved} for s in self.savings[-10:]]
            }
'''

FILES["scheduler.py"] = r'''"""GMR Telemetry Refresh Scheduler"""
import time
import threading
from typing import Callable, List, Optional
from datetime import datetime, timezone

class RefreshScheduler:
    def __init__(self, ingest, interval_seconds: int = 300):
        self.ingest = ingest
        self.interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
    
    def on_refresh(self, callback: Callable):
        self._callbacks.append(callback)
        
    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self._thread: self._thread.join(timeout=5)
        
    def _loop(self):
        while self._running:
            try:
                self.ingest.fetch()
                for cb in self._callbacks:
                    try: cb(self.ingest.cache)
                    except: pass
                time.sleep(self.interval)
            except:
                time.sleep(10)
'''

FILES["rotator.py"] = r'''"""GMR Core Rotation Engine"""
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
'''

for filename, content in FILES.items():
    filepath = os.path.join(GMR_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[✅] Created {filepath}")

print("\n[🚀] Phase 1 Part 2 Complete. GMR Core is fully assembled.")