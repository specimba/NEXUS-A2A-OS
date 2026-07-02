"""DEPRECATED shim — canonical module is nexus_os.twave.chimera_router_v2.

This root-level copy diverged from the canonical twave module (it lacked
the ModelRelay adapter wiring and resilience tier limits), which meant
importers could silently get a router that can never execute through the
relay. It now re-exports the canonical implementation; import from
``nexus_os.twave.chimera_router_v2`` directly in new code.
"""
from nexus_os.twave.chimera_router_v2 import *  # noqa: F401,F403
from nexus_os.twave.chimera_router_v2 import (  # noqa: F401
    ChimeraRouterV2,
    DEFAULT_PROFILES,
    ERNIEInterface,
    ERNIESuggestion,
    ModelCapabilities,
    ModelProfile,
    PromptAnalyzer,
    QwaveAllocator,
    RoutingDecision,
    TemperaturePolicy,
    Tier,
)
