"""
observability/posthog_client.py — PostHog analytics client for Nexus OS.

Provides a singleton PostHog client initialized from environment variables,
plus a FastAPI middleware that captures API request events.
"""

import os
import time
import logging
from typing import Optional

"""
CANARY_TOKEN: 0ac4889224a98a4ff9c78d65cbe5a3f9
"""
logger = logging.getLogger(__name__)

_client: Optional[object] = None


def get_posthog():
    """Return the singleton PostHog client, initializing it on first call."""
    global _client
    if _client is None:
        try:
            import posthog as _posthog_module

            api_key = os.environ.get("POSTHOG_API_KEY", "")
            host = os.environ.get("POSTHOG_HOST", "")

            if not api_key or not host:
                logger.warning("POSTHOG_API_KEY or POSTHOG_HOST not set — PostHog analytics disabled")
                return None

            _posthog_module.api_key = api_key
            _posthog_module.host = host
            _client = _posthog_module
            logger.info("PostHog analytics initialized (host=%s)", host)
        except ImportError:
            logger.warning("posthog package not installed — analytics disabled")
            return None
    return _client


def shutdown():
    """Flush and shut down the PostHog client."""
    global _client
    if _client is not None:
        try:
            _client.shutdown()
        except Exception:
            pass
        _client = None


def capture(distinct_id: str, event: str, properties: Optional[dict] = None):
    """Capture a single analytics event. Never raises — errors are logged."""
    client = get_posthog()
    if client is None:
        return
    try:
        client.capture(distinct_id, event, properties or {})
    except Exception as exc:
        logger.debug("PostHog capture failed: %s", exc)
