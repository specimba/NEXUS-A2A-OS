"""models/registry.py — Unified Model Provider Registry

Centralizes all model, provider, and domain routing configuration into a
single source of truth. Replaces the 6+ overlapping registration patterns:

  - .pi/models_registry.json
  - relay/scorer.py (ModelScores)
  - relay/providers_strict.py (StrictProvider)
  - bridge/vault.py (routing_tiers)
  - gmr/domain_mapping.py
  - claw/tiers.py (regex classifier)

Usage:
    registry = ModelRegistry.load_default()
    model = registry.select_model("code", {"prefer_local": True})
    provider = registry.get_provider("nvidia")
    fallback = registry.get_fallback_chain("code")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

DOMAIN_NAMES = {"code", "reasoning", "research", "fast", "security", "general"}
VALID_STATUSES = {"local", "up", "down", "offline", "partial_offline", "unknown"}
VALID_PROVIDER_STATUSES = {"healthy", "partial_offline", "offline", "local", "unknown"}

DEFAULT_MODELS_JSON = os.path.join(
    os.path.dirname(__file__), "..", "..", ".pi", "models_registry.json"
)


# ── Dataclasses ────────────────────────────────────────────────────────────────


@dataclass
class ModelEntry:
    name: str
    provider: str
    tier: int
    latency_ms: int
    cost_per_1m: float
    status: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "tier": self.tier,
            "latency_ms": self.latency_ms,
            "cost_per_1m": self.cost_per_1m,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelEntry":
        return cls(
            name=d["model"],
            provider=d.get("provider", "unknown"),
            tier=d.get("tier", 0),
            latency_ms=d.get("latency_ms", 0),
            cost_per_1m=d.get("cost_per_1m", 0.0),
            status=d.get("status", "unknown"),
        )


@dataclass
class LocalModelInfo:
    name: str
    size_gb: float
    latency_ms: int
    specialty: str

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LocalModelInfo":
        return cls(
            name=d["name"],
            size_gb=d.get("size_gb", 0.0),
            latency_ms=d.get("latency_ms", 0),
            specialty=d.get("specialty", "general"),
        )


@dataclass
class DomainConfig:
    description: str
    primary: List[ModelEntry] = field(default_factory=list)
    fallback_chain: List[str] = field(default_factory=list)
    recommended_for: List[str] = field(default_factory=list)
    requirement: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "primary": [m.to_dict() for m in self.primary],
            "fallback_chain": self.fallback_chain,
            "recommended_for": self.recommended_for,
            "requirement": self.requirement,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainConfig":
        primary = [ModelEntry.from_dict(m) for m in d.get("primary", [])]
        return cls(
            description=d.get("description", ""),
            primary=primary,
            fallback_chain=d.get("fallback_chain", []),
            recommended_for=d.get("recommended_for", []),
            requirement=d.get("requirement"),
        )


@dataclass
class ProviderInfo:
    name: str
    models: list[str] = field(default_factory=list)
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    priority: int = 999
    status: str = "unknown"
    avg_latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "models": self.models,
            "base_url": self.base_url,
            "priority": self.priority,
            "status": self.status,
            "avg_latency_ms": self.avg_latency_ms,
        }


# ── Registry ───────────────────────────────────────────────────────────────────


class ModelRegistry:
    """Unified model, provider, and domain routing registry.

    Seed from ``.pi/models_registry.json`` by default, then augment with
    additional provider/model registration at runtime.
    """

    def __init__(self) -> None:
        self._domains: Dict[str, DomainConfig] = {}
        self._providers: Dict[str, ProviderInfo] = {}
        self._models: Dict[str, ModelEntry] = {}       # name -> entry
        self._local_models: Dict[str, LocalModelInfo] = {}
        self._loaded_path: Optional[str] = None

    # ── Load / Persist ─────────────────────────────────────────────

    @classmethod
    def load_default(cls) -> "ModelRegistry":
        """Load from ``.pi/models_registry.json`` if it exists."""
        registry = cls()
        if os.path.exists(DEFAULT_MODELS_JSON):
            registry.load(DEFAULT_MODELS_JSON)
        else:
            logger.info("Default models registry not found at %s", DEFAULT_MODELS_JSON)
        return registry

    def load(self, json_path: str) -> None:
        """Load registry from JSON file (models_registry.json format)."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._loaded_path = json_path

        # Domains
        for domain_name, cfg in data.get("domains", {}).items():
            self._domains[domain_name] = DomainConfig.from_dict(cfg)

        # Providers (summary from JSON)
        for prov_name, prov_cfg in data.get("providers", {}).items():
            self._providers[prov_name] = ProviderInfo(
                name=prov_name,
                models=[],
                status=prov_cfg.get("status", "unknown"),
                avg_latency_ms=prov_cfg.get("avg_latency_ms"),
            )

        # Local models
        for lm in data.get("local_models", {}).get("models", []):
            info = LocalModelInfo.from_dict(lm)
            self._local_models[info.name] = info

        # Index all models from domains
        for cfg in self._domains.values():
            for entry in cfg.primary:
                self._models[entry.name] = entry
                # Augment provider model list
                if entry.provider in self._providers:
                    if entry.name not in self._providers[entry.provider].models:
                        self._providers[entry.provider].models.append(entry.name)

        logger.info(
            "Loaded registry: %d domains, %d providers, %d models, %d local",
            len(self._domains), len(self._providers), len(self._models), len(self._local_models),
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize registry state to JSON."""
        data = {
            "domains": {k: v.to_dict() for k, v in self._domains.items()},
            "providers": {k: v.to_dict() for k, v in self._providers.items()},
            "local_models": [{"name": k, **{"size_gb": v.size_gb, "latency_ms": v.latency_ms, "specialty": v.specialty}} for k, v in self._local_models.items()],
            "model_count": len(self._models),
        }
        return json.dumps(data, indent=indent)

    # ── Registration ───────────────────────────────────────────────

    def register_provider(
        self,
        name: str,
        models: Optional[list[str]] = None,
        base_url: Optional[str] = None,
        api_key_env: Optional[str] = None,
        priority: int = 999,
        status: str = "unknown",
    ) -> ProviderInfo:
        """Register or update a provider."""
        if status not in VALID_PROVIDER_STATUSES:
            status = "unknown"
        existing = self._providers.get(name)
        if existing:
            existing.models = list(set(existing.models + (models or [])))
            if base_url:
                existing.base_url = base_url
            if api_key_env:
                existing.api_key_env = api_key_env
            existing.priority = min(existing.priority, priority)
            existing.status = status
            return existing
        info = ProviderInfo(
            name=name,
            models=models or [],
            base_url=base_url,
            api_key_env=api_key_env,
            priority=priority,
            status=status,
        )
        self._providers[name] = info
        logger.debug("Registered provider: %s (priority=%d)", name, priority)
        return info

    def register_model(
        self,
        name: str,
        provider: str,
        tier: int = 0,
        latency_ms: int = 0,
        cost_per_1m: float = 0.0,
        status: str = "unknown",
    ) -> ModelEntry:
        """Register a model. Ensures its provider exists."""
        if provider not in self._providers:
            self.register_provider(provider)
        entry = ModelEntry(
            name=name,
            provider=provider,
            tier=tier,
            latency_ms=latency_ms,
            cost_per_1m=cost_per_1m,
            status=status,
        )
        self._models[name] = entry
        if name not in self._providers[provider].models:
            self._providers[provider].models.append(name)
        logger.debug("Registered model: %s (provider=%s, tier=%d)", name, provider, tier)
        return entry

    def register_domain(
        self,
        name: str,
        description: str = "",
        models: Optional[list[ModelEntry]] = None,
        fallback_chain: Optional[list[str]] = None,
        recommended_for: Optional[list[str]] = None,
        requirement: Optional[Dict[str, Any]] = None,
    ) -> DomainConfig:
        """Register or update a domain configuration."""
        cfg = DomainConfig(
            description=description,
            primary=models or [],
            fallback_chain=fallback_chain or [],
            recommended_for=recommended_for or [],
            requirement=requirement,
        )
        self._domains[name] = cfg
        for entry in cfg.primary:
            self._models[entry.name] = entry
        logger.debug("Registered domain: %s (%d models)", name, len(cfg.primary))
        return cfg

    def register_local_model(self, name: str, size_gb: float, latency_ms: int, specialty: str = "general") -> LocalModelInfo:
        info = LocalModelInfo(name=name, size_gb=size_gb, latency_ms=latency_ms, specialty=specialty)
        self._local_models[name] = info
        return info

    # ── Query ──────────────────────────────────────────────────────

    def get_provider(self, name: str) -> Optional[ProviderInfo]:
        return self._providers.get(name)

    def get_model(self, name: str) -> Optional[ModelEntry]:
        return self._models.get(name)

    def get_domain(self, name: str) -> Optional[DomainConfig]:
        return self._domains.get(name)

    def get_fallback_chain(self, domain: str) -> list[str]:
        cfg = self._domains.get(domain)
        if cfg and cfg.fallback_chain:
            return cfg.fallback_chain
        return []

    def get_local_model(self, name: str) -> Optional[LocalModelInfo]:
        return self._local_models.get(name)

    # ── Selection ──────────────────────────────────────────────────

    def select_model(
        self,
        domain: str,
        prefer_local: bool = False,
        min_tier: int = 0,
        max_cost: float = float("inf"),
    ) -> Optional[ModelEntry]:
        """Select the best model for a domain given constraints."""
        cfg = self._domains.get(domain)
        if not cfg or not cfg.primary:
            return None

        candidates = cfg.primary

        if prefer_local:
            local_first = [m for m in candidates if m.status == "local"]
            if local_first:
                return min(local_first, key=lambda m: m.latency_ms)

        tier_filtered = [m for m in candidates if m.tier >= min_tier]
        if not tier_filtered:
            tier_filtered = candidates

        cost_filtered = [m for m in tier_filtered if m.cost_per_1m <= max_cost]
        if not cost_filtered:
            cost_filtered = tier_filtered

        # Best by tier (higher = better), then by latency (lower = better)
        cost_filtered.sort(key=lambda m: (-m.tier, m.latency_ms))
        return cost_filtered[0] if cost_filtered else None

    def search_models(
        self,
        query: str = "",
        provider: Optional[str] = None,
        min_tier: int = 0,
        max_cost: float = float("inf"),
        status: Optional[str] = None,
    ) -> list[ModelEntry]:
        """Search models by various criteria."""
        results = list(self._models.values())

        if query:
            q = query.lower()
            results = [m for m in results if q in m.name.lower()]

        if provider:
            results = [m for m in results if m.provider == provider]

        if min_tier > 0:
            results = [m for m in results if m.tier >= min_tier]

        if max_cost < float("inf"):
            results = [m for m in results if m.cost_per_1m <= max_cost]

        if status:
            results = [m for m in results if m.status == status]

        results.sort(key=lambda m: (-m.tier, m.latency_ms))
        return results

    def list_providers(self) -> list[ProviderInfo]:
        """List all registered providers, sorted by priority."""
        return sorted(self._providers.values(), key=lambda p: p.priority)

    def list_domains(self) -> list[str]:
        return list(self._domains.keys())

    def list_models(self) -> list[ModelEntry]:
        return list(self._models.values())

    def list_local_models(self) -> list[LocalModelInfo]:
        return list(self._local_models.values())

    # ── Health / Stats ─────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "domains": len(self._domains),
            "providers": len(self._providers),
            "models": len(self._models),
            "local_models": len(self._local_models),
            "loaded_from": self._loaded_path,
        }


_registry_instance: Optional[ModelRegistry] = None


def get_registry() -> ModelRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistry.load_default()
    return _registry_instance
