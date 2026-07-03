"""Compatibility contract for the optional native Sentinel UiPath client."""

from nexus_os.bridge.uipath_adapter import UiPathClient, UiPathConfig
from nexus_os.sentinel.uipath import UiPathClient as CanonicalUiPathClient
from nexus_os.sentinel.uipath import UiPathConfig as CanonicalUiPathConfig


def test_uipath_adapter_compatibility_exports_canonical_client():
    assert UiPathClient is CanonicalUiPathClient
    assert UiPathConfig is CanonicalUiPathConfig