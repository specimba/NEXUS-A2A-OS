"""GMR Live Telemetry Ingestion"""
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
