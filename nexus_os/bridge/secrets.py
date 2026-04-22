"""
bridge/secrets.py — Secret Management for Bridge Authentication

Replaces hardcoded AGENT_SECRETS dict with a proper secret store.
Supports:
  - Environment variable loading
  - JSON file-based secret store
  - Runtime secret rotation
  - Per-agent secret derivation from a master key
  - API key health checking with per-provider status logging

NO secrets are stored in source code.
"""

import os
import json
import hashlib
import hmac
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Provider Configuration ───────────────────────────────────────
# Maps provider names to their API endpoints and rate limit info.
# Used by check_health() to report per-provider status.

PROVIDER_CONFIG: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "rpm_limit": 20,
        "rpd_limit": 500,
        "description": "Primary multi-model provider. Routes to 200+ models.",
    },
    "jina": {
        "base_url": "https://api.jina.ai/v1",
        "rpm_limit": 20,
        "rpd_limit": 500,
        "description": "Search and reader API for web content extraction.",
    },
    "kilocode": {
        "base_url": "https://proxy.kilocode.ai/v1",
        "rpm_limit": 20,
        "rpd_limit": 500,
        "description": "Secondary multi-model provider. Backup for OpenRouter.",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "rpm_limit": 30,
        "rpd_limit": 1000,
        "description": "Ultra-fast inference provider for low-latency tasks.",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "rpm_limit": 10,
        "rpd_limit": 200,
        "description": "OpenAI direct API for GPT-4 and o-series models.",
    },
}


class SecretNotFoundError(Exception):
    """Raised when a requested agent secret is not found."""
    pass


class SecretStore:
    """
    Multi-source secret store for Bridge authentication.

    Lookup order:
    1. In-memory overrides (runtime-registered secrets)
    2. Secret file (JSON)
    3. Environment variables (NEXUS_SECRET_{AGENT_ID})
    4. Master key derivation (if master key is set)
    """

    def __init__(
        self,
        secret_file: Optional[str] = None,
        master_key: Optional[str] = None,
        env_prefix: str = "NEXUS_SECRET_",
    ):
        self._overrides: Dict[str, str] = {}
        self._env_prefix = env_prefix
        self._master_key = master_key
        self._file_secrets: Dict[str, str] = {}

        # API key pools per provider: provider_name -> [key1, key2, ...]
        self._api_key_pools: Dict[str, List[str]] = {}
        # Active key index per provider for rotation
        self._active_key_index: Dict[str, int] = {}
        # Last health check timestamp
        self._last_health_check: float = 0.0

        if secret_file:
            self._load_file(secret_file)

    def _load_file(self, path: str):
        p = Path(path)
        if p.exists():
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._file_secrets = data
                    logger.info("Loaded %d secrets from %s", len(data), path)
                else:
                    logger.warning("Secret file %s is not a JSON object", path)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load secret file %s: %s", path, e)
        else:
            logger.info("Secret file %s not found, skipping", path)

    def register(self, agent_id: str, secret: str):
        """Register a secret at runtime (highest priority)."""
        self._overrides[agent_id] = secret

    def get_secret(self, agent_id: str) -> str:
        """Retrieve the secret for an agent."""
        if agent_id in self._overrides:
            return self._overrides[agent_id]

        if agent_id in self._file_secrets:
            return self._file_secrets[agent_id]

        env_key = f"{self._env_prefix}{agent_id.upper()}"
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val

        if self._master_key:
            derived = self._derive_secret(agent_id)
            self._overrides[agent_id] = derived
            return derived

        raise SecretNotFoundError(
            f"No secret found for agent '{agent_id}'. "
            f"Set {env_key} env var, add to secrets file, or register at runtime."
        )

    def _derive_secret(self, agent_id: str) -> str:
        """Derive a per-agent secret from the master key using HMAC-SHA256."""
        return hmac.new(
            self._master_key.encode(),
            agent_id.encode(),
            hashlib.sha256,
        ).hexdigest()

    def has_secret(self, agent_id: str) -> bool:
        try:
            self.get_secret(agent_id)
            return True
        except SecretNotFoundError:
            return False

    # ── API Key Pool Management ──────────────────────────────────

    def add_api_key(self, provider: str, key: str) -> None:
        """Add an API key to a provider's pool."""
        provider = provider.lower()
        if provider not in self._api_key_pools:
            self._api_key_pools[provider] = []
            self._active_key_index[provider] = 0
        self._api_key_pools[provider].append(key)
        logger.info(
            "Secrets: added API key to %s pool (pool size: %d)",
            provider, len(self._api_key_pools[provider]),
        )

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get the current active API key for a provider."""
        provider = provider.lower()
        pool = self._api_key_pools.get(provider, [])
        if not pool:
            logger.warning("Secrets: no API keys available for %s", provider)
            return None
        idx = self._active_key_index.get(provider, 0) % len(pool)
        return pool[idx]

    def rotate_api_key(self, provider: str) -> Optional[str]:
        """Rotate to the next API key in a provider's pool."""
        provider = provider.lower()
        pool = self._api_key_pools.get(provider, [])
        if len(pool) <= 1:
            logger.debug("Secrets: cannot rotate %s — only %d key(s)", provider, len(pool))
            return self.get_api_key(provider)
        self._active_key_index[provider] = (self._active_key_index.get(provider, 0) + 1) % len(pool)
        logger.info("Secrets: rotated %s to key index %d", provider, self._active_key_index[provider])
        return self.get_api_key(provider)

    def is_provider_enabled(self, provider: str) -> bool:
        """Check if a provider has at least one API key configured."""
        return len(self._api_key_pools.get(provider.lower(), [])) > 0

    def get_enabled_providers(self) -> List[str]:
        """Get a list of all providers with API keys configured."""
        return [p for p, pool in self._api_key_pools.items() if len(pool) > 0]

    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Check the health status of all API key pools.

        Logs the status of each provider's key pool including:
        - Whether the provider has active keys
        - Pool size (number of available keys)
        - Whether the provider is enabled/registered
        - Rate limit configuration

        This method is designed for debugging and operational visibility.
        Call it periodically or on-demand to verify all API connections.

        Returns a dict of provider_name -> health_info.
        """
        self._last_health_check = time.time()
        all_healthy = True
        health_report: Dict[str, Dict[str, Any]] = {}

        logger.info("=== Secrets Health Check ===")

        # ── Check configured providers ───────────────────────
        for provider, config in PROVIDER_CONFIG.items():
            pool = self._api_key_pools.get(provider, [])
            pool_size = len(pool)
            is_active = pool_size > 0
            active_idx = self._active_key_index.get(provider, 0)

            if is_active:
                # Mask key for logging (show first 8 chars + ...)
                active_key = pool[active_idx % pool_size]
                masked_key = active_key[:8] + "..." if len(active_key) > 8 else "***"
                status_label = "Active"
            else:
                masked_key = "N/A"
                status_label = "No Keys"

            health_info: Dict[str, Any] = {
                "provider": provider,
                "status": status_label,
                "pool_size": pool_size,
                "active_key_index": active_idx if is_active else None,
                "active_key_masked": masked_key,
                "rpm_limit": config.get("rpm_limit", "unknown"),
                "rpd_limit": config.get("rpd_limit", "unknown"),
                "description": config.get("description", ""),
                "healthy": is_active,
            }
            health_report[provider] = health_info

            # ── Detailed per-provider logging ──
            if is_active:
                logger.info(
                    "  %s: %s (Pool Size: %d, RPM: %s, RPD: %s, Active Key: %s)",
                    provider.capitalize(), status_label, pool_size,
                    config.get("rpm_limit", "?"), config.get("rpd_limit", "?"),
                    masked_key,
                )
            else:
                logger.warning(
                    "  %s: %s (Pool Size: 0 — no API keys configured)",
                    provider.capitalize(), status_label,
                )
                all_healthy = False

        # ── Check for providers with keys but no config ──────
        for provider in self._api_key_pools:
            if provider not in PROVIDER_CONFIG:
                pool_size = len(self._api_key_pools[provider])
                health_info = {
                    "provider": provider,
                    "status": "Unconfigured",
                    "pool_size": pool_size,
                    "active_key_index": self._active_key_index.get(provider, 0),
                    "rpm_limit": "unknown",
                    "rpd_limit": "unknown",
                    "description": "Provider has keys but no configuration entry",
                    "healthy": True,
                }
                health_report[provider] = health_info
                logger.info(
                    "  %s: Unconfigured (Pool Size: %d, no rate limit config)",
                    provider.capitalize(), pool_size,
                )

        overall = "ALL HEALTHY" if all_healthy else "SOME PROVIDERS DEGRADED"
        logger.info(
            "=== Secrets Health Check Complete: %s (%d providers) ===",
            overall, len(health_report),
        )

        return health_report

    def remove(self, agent_id: str):
        self._overrides.pop(agent_id, None)

    def rotate(self, agent_id: str, new_secret: str):
        old = self._overrides.get(agent_id)
        self._overrides[agent_id] = new_secret
        logger.info("Rotated secret for agent %s (had previous: %s)", agent_id, old is not None)


def generate_signature(secret: str, trace_id: str, payload: str) -> str:
    """Generate HMAC-SHA256 signature for Bridge requests."""
    message = f"{secret}:{trace_id}:{payload}"
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(
    secret: str, trace_id: str, payload: str, provided_signature: str
) -> bool:
    """Verify a Bridge request signature using constant-time comparison."""
    expected = generate_signature(secret, trace_id, payload)
    return hmac.compare_digest(expected, provided_signature)
