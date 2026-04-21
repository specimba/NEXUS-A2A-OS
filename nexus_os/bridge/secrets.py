"""
NEXUS OS Bridge — Secrets Management

Manages API keys for all providers (OpenRouter, Jina, Kilocode, Cerebras,
OpenAI, etc.). Handles key health checking, rotation, and pool management.
Each provider has a pool of API keys that can be cycled through when
rate limits are hit.
"""

import logging
import time
from typing import Any

logger = logging.getLogger("nexus_os.bridge.secrets")

# ── Provider Configuration ───────────────────────────────────────

PROVIDER_CONFIG: dict[str, dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "rpm_limit": 20,
        "rpd_limit": 500,
        "description": "Primary multi-model provider. Routes to 200+ models including Claude, GPT-4, Llama.",
    },
    "jina": {
        "base_url": "https://api.jina.ai/v1",
        "rpm_limit": 20,
        "rpd_limit": 500,
        "description": "Search and reader API. Used for web search, page reading, and content extraction.",
    },
    "kilocode": {
        "base_url": "https://proxy.kilocode.ai/v1",
        "rpm_limit": 20,
        "rpd_limit": 500,
        "description": "Secondary multi-model provider. Backup for OpenRouter with different model access.",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "rpm_limit": 30,
        "rpd_limit": 1000,
        "description": "Ultra-fast inference provider. Best for low-latency tasks with Llama models.",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "rpm_limit": 10,
        "rpd_limit": 200,
        "description": "OpenAI direct API. Premium access to GPT-4 and o-series reasoning models.",
    },
}


class SecretsManager:
    """Manages API key pools for all providers with health checking."""

    def __init__(self):
        self._pools: dict[str, list[str]] = {}   # provider -> [api_key, ...]
        self._active: dict[str, int] = {}         # provider -> index of active key
        self._health: dict[str, dict[str, Any]] = {}  # provider -> health info
        self._last_check: float = 0.0

    def add_key(self, provider: str, key: str) -> None:
        """Add an API key to a provider's pool."""
        provider = provider.lower()
        if provider not in self._pools:
            self._pools[provider] = []
            self._active[provider] = 0
        self._pools[provider].append(key)
        logger.info("Secrets: added key to %s pool (pool size: %d)", provider, len(self._pools[provider]))

    def get_key(self, provider: str) -> str | None:
        """Get the current active API key for a provider."""
        provider = provider.lower()
        pool = self._pools.get(provider, [])
        if not pool:
            logger.warning("Secrets: no keys available for %s", provider)
            return None
        idx = self._active.get(provider, 0) % len(pool)
        return pool[idx]

    def rotate_key(self, provider: str) -> str | None:
        """Rotate to the next API key in a provider's pool."""
        provider = provider.lower()
        pool = self._pools.get(provider, [])
        if len(pool) <= 1:
            logger.debug("Secrets: cannot rotate %s — only %d key(s)", provider, len(pool))
            return self.get_key(provider)
        self._active[provider] = (self._active.get(provider, 0) + 1) % len(pool)
        new_key = self.get_key(provider)
        logger.info("Secrets: rotated %s to key index %d", provider, self._active[provider])
        return new_key

    def check_health(self) -> dict[str, dict[str, Any]]:
        """
        Check the health status of all API key pools.

        Logs the status of each provider's key pool including:
        - Whether the provider has active keys
        - Pool size (number of available keys)
        - Whether the provider is enabled/registered
        - Rate limit configuration

        Returns a dict of provider -> health info.
        """
        self._last_check = time.time()
        all_healthy = True

        # Check configured providers
        for provider, config in PROVIDER_CONFIG.items():
            pool = self._pools.get(provider, [])
            pool_size = len(pool)
            is_active = pool_size > 0
            active_idx = self._active.get(provider, 0)

            status = "Active" if is_active else "No Keys"
            health_info = {
                "provider": provider,
                "status": status,
                "pool_size": pool_size,
                "active_key_index": active_idx if is_active else None,
                "rpm_limit": config.get("rpm_limit", "unknown"),
                "rpd_limit": config.get("rpd_limit", "unknown"),
                "description": config.get("description", ""),
                "healthy": is_active,
            }
            self._health[provider] = health_info

            # ── Detailed logging for debugging ──
            if is_active:
                logger.info(
                    "Secrets health: %s — %s (Pool Size: %d, RPM: %s, RPD: %s, Active Key Index: %d)",
                    provider, status, pool_size,
                    config.get("rpm_limit", "?"), config.get("rpd_limit", "?"),
                    active_idx,
                )
            else:
                logger.warning(
                    "Secrets health: %s — %s (Pool Size: 0, no API keys configured)",
                    provider, status,
                )
                all_healthy = False

        # Check for providers with keys but no config
        for provider in self._pools:
            if provider not in PROVIDER_CONFIG:
                pool_size = len(self._pools[provider])
                health_info = {
                    "provider": provider,
                    "status": "Unconfigured",
                    "pool_size": pool_size,
                    "active_key_index": self._active.get(provider, 0),
                    "rpm_limit": "unknown",
                    "rpd_limit": "unknown",
                    "description": "Provider has keys but no configuration entry",
                    "healthy": True,  # Has keys, assume ok
                }
                self._health[provider] = health_info
                logger.info(
                    "Secrets health: %s — Unconfigured (Pool Size: %d, no rate limit config)",
                    provider, pool_size,
                )

        overall = "ALL HEALTHY" if all_healthy else "SOME PROVIDERS DEGRADED"
        logger.info("Secrets health check complete: %s (%d providers)", overall, len(self._health))
        return dict(self._health)

    def is_provider_enabled(self, provider: str) -> bool:
        """Check if a provider has at least one API key configured."""
        provider = provider.lower()
        return len(self._pools.get(provider, [])) > 0

    def get_all_providers(self) -> list[str]:
        """Get a list of all providers with keys configured."""
        return [p for p, pool in self._pools.items() if len(pool) > 0]

    @property
    def last_check_time(self) -> float:
        """Timestamp of the last health check."""
        return self._last_check


# Module-level singleton
_secrets: SecretsManager | None = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global SecretsManager singleton."""
    global _secrets
    if _secrets is None:
        _secrets = SecretsManager()
    return _secrets
