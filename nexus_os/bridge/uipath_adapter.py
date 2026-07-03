"""Compatibility exports for the optional UiPath Sentinel adapter.

The historical AgentHack service is intentionally not imported into NEXUS.
Native Sentinel owns case policy and lifecycle; this module exposes only the
disabled-by-default outbound UiPath client.
"""

from nexus_os.sentinel.uipath import UiPathClient, UiPathConfig

__all__ = ["UiPathClient", "UiPathConfig"]