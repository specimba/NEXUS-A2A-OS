"""Tests for the 7350–7360 port plane."""

from nexus_os.bridge.port_plane import (
    PORT_PLANE,
    PortService,
    doctor_report,
    plane_summary,
    probe_service,
)
from nexus_os.bridge.port_registry import PortRegistry


def test_plane_covers_band_and_hard_rules():
    for port in range(7350, 7361):
        assert port in PORT_PLANE, f"missing plane entry for {port}"
    assert PORT_PLANE[7352].owner == "brain_api"
    assert "modelrelay" not in PORT_PLANE[7352].owner.lower()
    assert PORT_PLANE[7350].owner == "modelrelay_npm"
    assert "/health" not in PORT_PLANE[7350].health_paths
    assert PORT_PLANE[7350].health_paths[0] in {"/", "/v1/models"}


def test_plane_owners_align_with_registry_where_shared():
    for port, service in PORT_PLANE.items():
        if port in PortRegistry.CANONICAL_PORTS:
            assert (
                PortRegistry.CANONICAL_PORTS[port] == service.owner
            ), f"owner mismatch on {port}"


def test_probe_free_optional_port():
    # 7351 is reserved unused; almost certainly free in test env
    result = probe_service(PORT_PLANE[7351], timeout=0.3)
    assert result.port == 7351
    if not result.listening:
        assert result.classification == "free_optional"


def test_plane_summary_shapes():
    free = probe_service(PORT_PLANE[7351], timeout=0.2)
    summary = plane_summary([free])
    assert "status" in summary
    assert "routing_chain" in summary
    assert summary["stale_doc_warnings"]


def test_doctor_report_structure():
    report = doctor_report(timeout=0.3, band_only=True)
    assert report["command"] == "ports doctor"
    assert "services" in report
    assert len(report["services"]) == 11  # 7350..7360
    assert report["plane_version"]
