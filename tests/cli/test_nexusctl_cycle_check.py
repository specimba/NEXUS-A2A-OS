import json
import os
import subprocess
import sys
from pathlib import Path


def test_cycle_check_reports_unavailable_when_no_state(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m", "nexusctl", "cycle-check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["status"] == "unavailable"


def test_doctor_report_only_has_intentional_failure_mode(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m", "nexusctl", "doctor", "--report-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["command"] == "doctor"
    assert payload["report_only"] is True
    assert payload["no_fake_counts"] is True


def test_doctor_memory_report_only_checks_restored_modules(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(repo_root), str(repo_root / "src")])
    proc = subprocess.run(
        [sys.executable, "-m", "nexusctl", "doctor", "memory", "--report-only"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["command"] == "doctor memory"
    assert payload["report_only"] is True
    assert payload["checks"]["nexus_os.governor.trust_kernel"] is True
    assert payload["checks"]["src.nexus_os.monitoring.token_guard"] is True


def test_doctor_version_report_only_checks_repo_without_fetch(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m", "nexusctl", "doctor", "version", "--report-only"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["command"] == "doctor version"
    assert payload["report_only"] is True
    assert payload["refresh_performed"] is False
    assert payload["required_files"]["missing"] == []
    assert "pending" in payload["queue"]


def test_status_has_intentional_failure_mode(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m", "nexusctl", "status"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["command"] == "status"


def test_handoff_has_intentional_failure_mode(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m", "nexusctl", "handoff", "--output", "handoff.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["command"] == "handoff"
    assert payload["suggested_output"] == "handoff.json"
