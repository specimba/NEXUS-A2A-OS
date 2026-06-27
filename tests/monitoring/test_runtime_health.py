from nexus_os.monitoring.runtime_health import assess_runtime_health


def _snapshot(**overrides):
    snapshot = {
        "chrome": {"private_gb": 4.0, "top_private_mb": 800},
        "memory": {"available_mb": 8192, "commit_pct": 50},
        "disk": {"max_mbps": 20},
        "session_recovery": {"ready": True},
    }
    snapshot.update(overrides)
    return snapshot


def test_runtime_health_is_report_only_when_healthy():
    result = assess_runtime_health(_snapshot())
    assert result["status"] == "ok"
    assert result["restart_recommended"] is False
    assert result["automatic_restart_performed"] is False


def test_runtime_health_recommends_restart_only_with_recovery():
    result = assess_runtime_health(
        _snapshot(
            chrome={"private_gb": 18.0, "top_private_mb": 4096},
            memory={"available_mb": 1500, "commit_pct": 94},
        )
    )
    assert result["status"] == "critical"
    assert result["restart_recommended"] is True
    assert {item["code"] for item in result["findings"]} == {
        "browser_memory_pressure",
    }


def test_runtime_health_blocks_restart_without_session_recovery():
    result = assess_runtime_health(
        _snapshot(
            chrome={"private_gb": 11.0, "top_private_mb": 3500},
            session_recovery={"ready": False},
        )
    )
    assert result["status"] == "critical"
    assert result["restart_recommended"] is False
    assert {item["code"] for item in result["findings"]} == {
        "browser_memory_growth",
        "restart_without_recovery",
    }


def test_runtime_health_reports_disk_spike_without_browser_restart():
    result = assess_runtime_health(_snapshot(disk={"max_mbps": 400}))
    assert result["status"] == "warning"
    assert result["restart_recommended"] is False
    assert result["findings"][0]["code"] == "disk_spike_observed"
