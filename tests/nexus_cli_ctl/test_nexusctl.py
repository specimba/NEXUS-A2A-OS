"""Tests for nexusctl CLI commands."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from nexus_os.cli.nexusctl import cmd_status, cmd_doctor, cmd_cycle_check, cmd_wiki, cmd_messaging, cmd_state, cmd_handoff, cmd_stress_lab


class TestCmdStatus:
    def test_status_runs(self, capsys):
        cmd_status(None)
        output = capsys.readouterr().out
        assert "Providers tracked" in output

    def test_status_shows_counts(self, capsys):
        from nexus_os.monitoring.provider_health import get_health_monitor
        monitor = get_health_monitor()
        monitor.record_request("test_provider", success=True, latency_ms=50)
        cmd_status(None)
        output = capsys.readouterr().out
        assert "1" in output


class TestCmdDoctor:
    def test_doctor_runs(self, capsys):
        result = cmd_doctor(None)
        output = capsys.readouterr().out
        assert "NEXUS Doctor Check" in output
        assert "Python" in output

    def test_doctor_shows_all_checks(self, capsys):
        cmd_doctor(None)
        output = capsys.readouterr().out
        assert "Provider Health" in output
        assert "Wiki Pipeline" in output
        assert "Messaging" in output


class TestCmdCycleCheck:
    def test_cycle_check_runs(self, capsys):
        result = cmd_cycle_check(None)
        output = capsys.readouterr().out
        assert "Cycle" in output or "OK" in output or "WARN" in output


class TestCmdWiki:
    def test_wiki_status(self, capsys):
        args = type("Args", (), {"wiki_search": None, "wiki_list": False, "wiki_status": True, "wiki_sources": False, "wiki_refresh": False})()
        cmd_wiki(args)
        output = capsys.readouterr().out
        assert "pages" in output

    def test_wiki_search_no_results(self, capsys):
        args = type("Args", (), {"wiki_search": "xyznonexistent", "wiki_list": False, "wiki_status": False, "wiki_sources": False, "wiki_refresh": False})()
        cmd_wiki(args)
        output = capsys.readouterr().out
        assert "No results" in output or "results" in output.lower()

    def test_wiki_default(self, capsys):
        args = type("Args", (), {"wiki_search": None, "wiki_list": False, "wiki_status": False, "wiki_sources": False, "wiki_refresh": False})()
        cmd_wiki(args)
        output = capsys.readouterr().out
        assert "Usage" in output or "nexusctl" in output


class TestCmdMessaging:
    def test_messaging_runs(self, capsys):
        cmd_messaging(None)
        output = capsys.readouterr().out
        assert "telegram" in output
        assert "slack" in output
        assert "discord" in output


class TestCmdState:
    def test_state_no_file(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        (tmp_path / ".nexus_pi" / "state").mkdir(parents=True, exist_ok=True)
        args = type("Args", (), {"section": None})()
        cmd_state(args)
        output = capsys.readouterr().out
        assert "No state file" in output or "state" in output.lower()


class TestCmdHandoff:
    def test_handoff_creates_package(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        (tmp_path / ".nexus_pi" / "state").mkdir(parents=True, exist_ok=True)
        cmd_handoff(None)
        output = capsys.readouterr().out
        assert "Handoff package" in output
        assert "Components" in output

    def test_handoff_includes_project_state(self, capsys, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        (tmp_path / ".nexus_pi" / "state").mkdir(parents=True, exist_ok=True)
        cmd_handoff(None)
        output = capsys.readouterr().out
        assert "project_state" in output or "provider_health" in output


class TestCmdStressLab:
    def test_stress_lab_runs(self, capsys):
        result = cmd_stress_lab(None)
        output = capsys.readouterr().out
        assert "NEXUS Stress Lab" in output
        assert "Results" in output

    def test_stress_lab_shows_each_test(self, capsys):
        cmd_stress_lab(None)
        output = capsys.readouterr().out
        assert "Rate limiter" in output
        assert "Misalignment" in output
