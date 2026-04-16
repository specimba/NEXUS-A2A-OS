"""GMR Model Registry — Dynamic model list management.

Handles model discovery, status monitoring, and dynamic refresh.
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from threading import Thread, Event

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Static model metadata from registry."""
    name: str
    provider: str
    max_context: int
    supports_functions: bool = False
    supports_vision: bool = False
    tier: int = 50


class ModelRegistry:
    """
    Manages dynamic model list with periodic refresh.
    
    Sources:
    - Local: Ollama models (localhost:7352)
    - Remote: API-based providers
    """
    
    # Default budgets for pools
    DEFAULT_BUDGETS = {
        "agent": 100000,      # General agent tasks
        "skill": 50000,       # Skill execution
        "swarm": 200000,      # Swarm coordination
        "research": 150000,   # Research tasks
    }
    
    def __init__(
        self,
        refresh_interval: int = 300,  # 5 minutes
        local_endpoint: str = "http://localhost:7352",
    ):
        self._local_endpoint = local_endpoint
        self._refresh_interval = refresh_interval
        self._models: Dict[str, ModelInfo] = {}
        self._last_refresh: float = 0
        self._stop_event = Event()
        self._refresh_thread: Optional[Thread] = None
        
        # Track available models
        self._available_models: Dict[str, bool] = {}
    
    def start(self):
        """Start background refresh thread."""
        if self._refresh_thread is None or not self._refresh_thread.is_alive():
            self._stop_event.clear()
            self._refresh_thread = Thread(target=self._refresh_loop, daemon=True)
            self._refresh_thread.start()
            logger.info("ModelRegistry: Started background refresh")
    
    def stop(self):
        """Stop background refresh thread."""
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
        logger.info("ModelRegistry: Stopped background refresh")
    
    def _refresh_loop(self):
        """Background refresh loop."""
        while not self._stop_event.is_set():
            try:
                self.refresh()
            except Exception as e:
                logger.warning(f"ModelRegistry: Refresh failed: {e}")
            self._stop_event.wait(self._refresh_interval)
    
    def refresh(self):
        """Refresh model list from sources."""
        self._last_refresh = time.time()
        
        # Try to fetch from local endpoint
        local_models = self._fetch_local_models()
        
        # Update available models
        for model in local_models:
            self._available_models[model.name] = True
        
        logger.info(f"ModelRegistry: Refreshed {len(local_models)} local models")
    
    def _fetch_local_models(self) -> List[ModelInfo]:
        """Fetch models from local Ollama endpoint."""
        import requests
        
        models = []
        try:
            response = requests.get(f"{self._local_endpoint}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                for model in data.get("models", []):
                    name = model.get("name", "")
                    # Determine tier based on model name
                    tier = self._infer_tier(name)
                    models.append(ModelInfo(
                        name=name,
                        provider="ollama",
                        max_context=model.get("size", 0) // 1000000,  # Rough estimate
                        tier=tier,
                    ))
        except Exception as e:
            logger.debug(f"ModelRegistry: Local fetch failed: {e}")
        
        return models
    
    def _infer_tier(self, model_name: str) -> int:
        """Infer model tier from name."""
        name_lower = model_name.lower()
        
        # Premium reasoning models
        if any(x in name_lower for x in ["claude", "gpt-4", "chatgpt", "reasoning"]):
            return 90
        
        # High-tier models
        if any(x in name_lower for x in ["gpt-3.5", "llama3", "qwen", "mistral"]):
            return 70
        
        # Medium tier
        if any(x in name_lower for x in ["osman", "phi", "tiny"]):
            return 40
        
        return 50  # Default
    
    def get_model(self, name: str) -> Optional[ModelInfo]:
        """Get model info by name."""
        return self._models.get(name)
    
    def list_models(self, provider: Optional[str] = None, min_tier: int = 0) -> List[ModelInfo]:
        """List available models."""
        models = [m for m in self._models.values()]
        
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if min_tier > 0:
            models = [m for m in models if m.tier >= min_tier]
        
        return models
    
    def is_available(self, name: str) -> bool:
        """Check if model is currently available."""
        return self._available_models.get(name, False)
    
    def get_budget_for_category(self, category: str) -> int:
        """Get budget for a category."""
        return self.DEFAULT_BUDGETS.get(category, 100000)