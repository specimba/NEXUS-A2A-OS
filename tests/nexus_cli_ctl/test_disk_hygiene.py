import argparse
import json

from nexus_os.cli.nexusctl import cmd_hygiene
from nexus_os.monitoring.disk_hygiene import (
    GIB,
    DriveAccounting,
    PathSummary,
    analyze_drive_accounting,
    build_cleanup_readiness,
    build_hygiene_report,
    classify_path,
)


def test_classify_system_and_cache_paths():
    assert classify_path(r"C:\pagefile.sys")[1] == "admin_only"
    assert classify_path(r"C:\Users\speci.000\AppData\Local\npm-cache\_cacache")[0] == "package_cache"
    assert classify_path(r"C:\Users\speci.000\Documents\NEXUS\models\guard\model.safetensors")[1] == "high"


def test_build_hygiene_report_is_read_only(tmp_path):
    cache_dir = tmp_path / "npm-cache" / "_cacache"
    cache_dir.mkdir(parents=True)
    large_file = cache_dir / "blob.bin"
    large_file.write_bytes(b"x" * 2048)

    report = build_hygiene_report(
        paths=[tmp_path],
        min_file_mib=0,
        top_file_limit=5,
        include_system_files=False,
    )

    assert report["mode"] == "read_only"
    assert report["safety"]["deletes"] is False
    assert report["safety"]["moves"] is False
    assert any(row["path"].endswith("blob.bin") for row in report["top_files"])
    assert report["cleanup_operator_protocol"]["mode"] == "diagnose_first_then_confirm"
    assert large_file.exists()


def test_hidden_space_gap_finding_requires_diagnose_first():
    row = DriveAccounting(
        drive="C:",
        total_bytes=900 * GIB,
        used_bytes=600 * GIB,
        free_bytes=300 * GIB,
        visible_bytes=500 * GIB,
    )

    findings = analyze_drive_accounting([row], hidden_gap_threshold_gib=25)

    assert findings[0]["type"] == "hidden_space_unexplained"
    assert findings[0]["severity"] == "warning"
    assert "admin/VSS/USN diagnostics" in findings[0]["message"]


def test_material_free_space_delta_from_baseline_is_reported():
    previous = {
        "drive_accounting": [
            {
                "drive": "D:",
                "free_bytes": 30 * GIB,
            }
        ]
    }
    row = DriveAccounting(
        drive="D:",
        total_bytes=900 * GIB,
        used_bytes=300 * GIB,
        free_bytes=600 * GIB,
    )

    findings = analyze_drive_accounting([row], previous_report=previous, free_delta_threshold_gib=50)

    assert findings[0]["type"] == "material_free_space_delta"
    assert findings[0]["direction"] == "increased"
    assert findings[0]["delta_gib"] == 570.0


def test_cleanup_readiness_protects_evidence_and_models():
    readiness = build_cleanup_readiness(
        [
            PathSummary(
                path=r"C:\Users\speci.000\Downloads\ARCHIVIST",
                size_bytes=4 * GIB,
                files=1,
                dirs=0,
                errors=0,
                latest_write=None,
                category="nexus_evidence",
                risk="high",
                recommendation="preserve",
            ),
            PathSummary(
                path=r"C:\Users\speci.000\AppData\Local\npm-cache\_cacache",
                size_bytes=2 * GIB,
                files=1,
                dirs=0,
                errors=0,
                latest_write=None,
                category="package_cache",
                risk="low",
                recommendation="tool cleanup",
            ),
        ]
    )

    rows = {row["path"]: row for row in readiness["rows"]}
    assert rows[r"C:\Users\speci.000\Downloads\ARCHIVIST"]["protected"] is True
    assert rows[r"C:\Users\speci.000\AppData\Local\npm-cache\_cacache"]["cleanup_class"] == "ready_with_confirmation"
    assert readiness["estimated_confirmation_reclaim_gib"] == 2.0


def test_build_hygiene_report_allows_drive_only_scope():
    report = build_hygiene_report(
        paths=[],
        top_file_limit=0,
        include_system_files=False,
        include_drive_accounting=False,
    )

    assert report["summaries"] == []
    assert report["top_files"] == []
    assert report["scan_stats"]["skipped"] == "limit_zero"


def test_cmd_hygiene_json_output(capsys, tmp_path):
    target = tmp_path / "Downloads"
    target.mkdir()
    (target / "artifact.zip").write_bytes(b"x" * 1024)
    args = argparse.Namespace(
        path=[str(target)],
        json=True,
        top_files=10,
        summary_limit=10,
        min_file_mib=0,
        no_system_files=True,
        baseline=None,
        drive=[],
        no_drive_accounting=True,
        visible_root_scan=False,
        hidden_gap_threshold_gib=25.0,
        free_delta_threshold_gib=50.0,
    )

    assert cmd_hygiene(args) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "ok"
    assert payload["mode"] == "read_only"
    assert payload["summaries"][0]["path"] == str(target)
    assert payload["top_files"][0]["path"].endswith("artifact.zip")
    assert payload["drive_accounting"] == []
