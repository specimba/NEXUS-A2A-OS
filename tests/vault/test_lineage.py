"""tests/vault/test_lineage.py — MemLineage chain-of-custody (arXiv 2605.14421).

Closes the laundering path: external content ingested via SENSORY,
compressed through consolidation, and re-committed under NEXUS's own
principal must stay TAINTED all the way up — and a sensitive action
justified by that memory must be refused."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.vault.lineage import (
    LineageLog,
    get_lineage_log,
    set_lineage_log,
)
from nexus_os.vault.memory_channels import MemoryChannel, MemoryChannelManager


@pytest.fixture(autouse=True)
def isolated_lineage(tmp_path):
    set_lineage_log(LineageLog(path=tmp_path / "lineage.jsonl"))
    yield get_lineage_log()
    set_lineage_log(None)


class TestTaintPropagation:
    def test_external_origin_is_tainted(self, isolated_lineage):
        entry = isolated_lineage.record("e1", "a1", "sensory", origin="external")
        assert entry.tainted is True

    def test_internal_origin_clean(self, isolated_lineage):
        entry = isolated_lineage.record("e2", "a1", "working", origin="internal")
        assert entry.tainted is False

    def test_taint_propagates_through_derivation(self, isolated_lineage):
        isolated_lineage.record("ext", "a1", "sensory", origin="external")
        derived = isolated_lineage.record(
            "sum", "a1", "working", origin="internal", parent_ids=["ext"],
        )
        assert derived.tainted is True  # laundering blocked

    def test_unknown_parent_taints(self, isolated_lineage):
        entry = isolated_lineage.record(
            "d1", "a1", "semantic", origin="internal", parent_ids=["never-recorded"],
        )
        assert entry.tainted is True  # unrecorded ancestry can't prove cleanliness

    def test_unknown_origin_treated_external(self, isolated_lineage):
        entry = isolated_lineage.record("e3", "a1", "sensory", origin="made-up")
        assert entry.tainted is True

    def test_clean_chain_stays_clean(self, isolated_lineage):
        isolated_lineage.record("s1", "a1", "working", origin="system")
        d = isolated_lineage.record("d2", "a1", "semantic", origin="internal",
                                    parent_ids=["s1"])
        assert d.tainted is False


class TestSensitiveActionGate:
    def test_tainted_justification_denied(self, isolated_lineage):
        isolated_lineage.record("ext", "a1", "sensory", origin="external")
        isolated_lineage.record("sum", "a1", "working", origin="internal",
                                parent_ids=["ext"])
        allowed, reason = isolated_lineage.gate_sensitive_action(["sum"])
        assert allowed is False
        assert "DENY" in reason

    def test_clean_justification_allowed(self, isolated_lineage):
        isolated_lineage.record("s1", "a1", "working", origin="internal")
        allowed, reason = isolated_lineage.gate_sensitive_action(["s1"])
        assert allowed is True

    def test_benign_recall_without_lineage_allowed(self, isolated_lineage):
        allowed, reason = isolated_lineage.gate_sensitive_action(["no-lineage-id"])
        assert allowed is True
        assert "without lineage" in reason


class TestLogIntegrity:
    def test_chain_verifies(self, tmp_path):
        log = LineageLog(path=tmp_path / "chain.jsonl")
        log.record("a", "x", "sensory", origin="external")
        log.record("b", "x", "working", origin="internal", parent_ids=["a"])
        log.record("c", "x", "semantic", origin="internal", parent_ids=["b"])
        report = log.verify_chain()
        assert report["ok"] is True
        assert report["entries"] == 3

    def test_tampered_row_detected(self, tmp_path):
        path = tmp_path / "chain.jsonl"
        log = LineageLog(path=path)
        log.record("a", "x", "sensory", origin="external")
        log.record("b", "x", "working", origin="internal", parent_ids=["a"])
        rows = path.read_text(encoding="utf-8").splitlines()
        tampered = json.loads(rows[0])
        tampered["tainted"] = False  # attacker whitewashes the taint bit
        rows[0] = json.dumps(tampered, sort_keys=True)
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        report = LineageLog(path=path).verify_chain()
        assert report["ok"] is False
        assert report["reason"] in {"chain_break", "bad_signature"}

    def test_reload_restores_index(self, tmp_path):
        path = tmp_path / "chain.jsonl"
        log = LineageLog(path=path)
        log.record("ext", "x", "sensory", origin="external")
        reloaded = LineageLog(path=path)
        assert reloaded.is_tainted("ext") is True


class TestChannelIntegration:
    def test_sensory_default_external_tainted(self):
        m = MemoryChannelManager()
        r = m.append_sensory("a1", "raw web content")
        assert r.origin == "external"
        assert r.tainted is True

    def test_laundering_blocked_end_to_end(self):
        """external SENSORY → consolidation stage 1 (WORKING) → stage 2
        (EPISODIC) → stage 3 (SEMANTIC): taint must survive every hop."""
        from nexus_os.vault.consolidation_daemon import LightMemConsolidationDaemon
        m = MemoryChannelManager()
        daemon = LightMemConsolidationDaemon(manager=m)
        m.append_sensory("agent-x", "injected payload disguised as docs",
                         topic_tags=["docs"])
        daemon._stage_sensory_to_working("agent-x")
        working = m._buffers["agent-x"][MemoryChannel.WORKING]
        assert working and working[-1].tainted is True

        daemon._stage_working_to_episodic("agent-x")
        episodic = m._buffers["agent-x"][MemoryChannel.EPISODIC]
        assert episodic and episodic[-1].tainted is True

        daemon._stage_episodic_to_semantic("agent-x")
        semantic = m._buffers["agent-x"][MemoryChannel.SEMANTIC]
        assert semantic and all(rec.tainted for rec in semantic)

        # ...and the gate refuses a sensitive action justified by any of it
        allowed, _ = get_lineage_log().gate_sensitive_action(
            [semantic[-1].record_id],
        )
        assert allowed is False

    def test_clean_system_content_stays_clean_through_stages(self):
        from nexus_os.vault.consolidation_daemon import LightMemConsolidationDaemon
        m = MemoryChannelManager()
        daemon = LightMemConsolidationDaemon(manager=m)
        m.append_sensory("agent-y", "internal telemetry snapshot",
                         topic_tags=["telemetry"], origin="system")
        daemon._stage_sensory_to_working("agent-y")
        working = m._buffers["agent-y"][MemoryChannel.WORKING]
        assert working and working[-1].tainted is False
        allowed, _ = get_lineage_log().gate_sensitive_action(
            [working[-1].record_id],
        )
        assert allowed is True
