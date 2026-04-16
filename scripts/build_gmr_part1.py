#!/usr/bin/env python3
"""Phase 1: GMR Core Builder (Part 1)"""
import os

GMR_DIR = os.path.join("src", "nexus_os", "gmr")
os.makedirs(os.path.join(GMR_DIR, "outputs"), exist_ok=True)

FILES = {}

FILES["__init__.py"] = '''"""GMR — Genius Model Rotator v3.0"""
from .telemetry import TelemetryIngest, ModelTelemetry
from .domain_mapping import DOMAIN_MAPPING

__version__ = "3.0.0"
'''

FILES["domain_mapping.py"] = '''"""GMR Domain Configuration & Budgets"""
DOMAIN_MAPPING = {
    "code": {
        "description": "Code generation, debugging, implementation",
        "primary": [
            {"model": "osman-coder", "provider": "ollama", "tier": 40, "latency_ms": 50, "cost_per_1m": 0, "status": "local"},
            {"model": "Devstral 2 123B", "provider": "nvidia", "tier": 86, "latency_ms": 542, "cost_per_1m": 4.0, "status": "up"}
        ],
        "fallback_chain": ["osman-coder", "qwen2.5-coder:7b", "Codestral", "GPT OSS 20B"],
        "requirement": {"max_latency_ms": 5000, "prefer_local": True, "min_tier": 40}
    },
    "reasoning": {
        "description": "Deep analysis, planning, architecture decisions",
        "primary": [
            {"model": "Trinity Large Preview", "provider": "opencode", "tier": 97, "latency_ms": 1707, "cost_per_1m": 5.0, "status": "up"},
            {"model": "osman-reasoning", "provider": "ollama", "tier": 40, "latency_ms": 80, "cost_per_1m": 0, "status": "local"}
        ],
        "fallback_chain": ["osman-reasoning", "qwen3:8b", "Qwen3 80B Thinking", "Trinity Large Preview"],
        "requirement": {"max_latency_ms": 10000, "prefer_local": True, "min_tier": 40}
    },
    "fast": {
        "description": "Hot path, quick responses, low latency",
        "primary": [
            {"model": "osman-fast", "provider": "ollama", "tier": 40, "latency_ms": 20, "cost_per_1m": 0, "status": "local"},
            {"model": "Step 3.5 Flash", "provider": "nvidia", "tier": 93, "latency_ms": 1794, "cost_per_1m": 3.0, "status": "up"}
        ],
        "fallback_chain": ["osman-fast", "locooperator", "Nemotron Nano 30B"],
        "requirement": {"max_latency_ms": 100, "prefer_local": True, "min_tier": 40, "require_local": True}
    }
}
'''

FILES["telemetry.py"] = '''"""GMR Live Telemetry Ingestion"""
import requests
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ModelTelemetry:
    name: str
    provider: str
    tier: int
    latency_ms: int
    uptime_pct: float
    status: str
    timestamp: str
    
    @property
    def quality_score(self) -> float:
        return min(self.tier, 100) * 0.7 + (self.uptime_pct * 100) * 0.3
    
    @property
    def is_available(self) -> bool:
        return self.status == "up" and self.uptime_pct >= 0.5
    
    @property
    def is_local(self) -> bool:
        return self.provider in {"ollama", "local"}

class TelemetryIngest:
    def __init__(self, url: str = "http://localhost:7352/api/models"):
        self.url = url
        self.last_fetch: Optional[datetime] = None
        self.cache: Dict[str, ModelTelemetry] = {}
        self.lock = threading.Lock()
    
    def fetch(self) -> Dict[str, ModelTelemetry]:
        with self.lock:
            try:
                response = requests.get(self.url, timeout=5)
                data = response.json()
                timestamp = datetime.now(timezone.utc).isoformat()
                
                for model_data in data.get("models", []):
                    tel = ModelTelemetry(
                        name=model_data["name"],
                        provider=model_data.get("provider", "unknown"),
                        tier=model_data.get("tier", 0),
                        latency_ms=model_data.get("latency_ms", 9999),
                        uptime_pct=model_data.get("uptime", 1.0),
                        status=model_data.get("status", "unknown"),
                        timestamp=timestamp
                    )
                    self.cache[tel.name] = tel
                
                self.last_fetch = datetime.now(timezone.utc)
            except Exception as e:
                print(f"[GMR] Telemetry fetch failed: {e}")
            return self.cache
'''

for filename, content in FILES.items():
    filepath = os.path.join(GMR_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[✅] Created {filepath}")

print("\\n[🚀] Phase 1 Part 1 Complete. Ready for GMR Rotator and Savings Tracker.")