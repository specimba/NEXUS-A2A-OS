"""tests/sentinel/test_adoption_repairs.py — repairs applied during the
FABLE5 adoption review of the CODEX Sentinel cluster."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from nexus_os.governor.trust_kernel import TrustKernel, set_trust_kernel
from nexus_os.sentinel.models import CreateCaseRequest, PolicyVerdict
from nexus_os.sentinel.service import SentinelService


@pytest.fixture(autouse=True)
def isolated_kernel():
    set_trust_kernel(TrustKernel(vault_enabled=False))
    yield
    set_trust_kernel(None)


class TestWriterTrustFromKernel:
    def test_writer_trust_is_kernel_prior_not_100(self, sentinel_factory):
        service, _, _ = sentinel_factory()
        trust = service._writer_trust()
        assert trust == pytest.approx(90.0)  # bootstrap prior, not 100.0

    def test_writer_trust_fail_closed_without_kernel(self, sentinel_factory, monkeypatch):
        service, _, _ = sentinel_factory()
        import nexus_os.governor.trust_kernel as tk
        monkeypatch.setattr(tk, "get_trust_kernel",
                            lambda: (_ for _ in ()).throw(RuntimeError("down")))
        assert service._writer_trust() == 0.0

    def test_memory_mirror_uses_kernel_trust(self, sentinel_factory):
        service, _, _ = sentinel_factory()

        class _CapturingMemory:
            def __init__(self):
                self.calls = []
            def append_episodic(self, agent_id, content, **kw):
                self.calls.append(("episodic", kw.get("trust_score")))
            def append_task(self, agent_id, content, **kw):
                self.calls.append(("task", kw.get("trust_score")))
            def append_meta(self, agent_id, meta_type, meta_value, **kw):
                self.calls.append(("meta", kw.get("trust_score")))

        service.memory = _CapturingMemory()
        service.create_case(CreateCaseRequest(
            case_id="case-1", title="repair test",
            actor_id="tester", idempotency_key="create-case-1",
        ))
        assert service.memory.calls, "memory mirror not exercised"
        for _, trust in service.memory.calls:
            assert trust == pytest.approx(90.0)
            assert trust != 100.0


class TestGovernorVerdictFailClosed:
    def test_known_verdicts_map(self):
        for raw, expected in [("allow", PolicyVerdict.ALLOW),
                              ("hold", PolicyVerdict.HOLD),
                              ("deny", PolicyVerdict.DENY)]:
            result = SimpleNamespace(decision=SimpleNamespace(value=raw))
            assert SentinelService._governor_verdict(result) == expected

    def test_unknown_verdict_denies_instead_of_raising(self):
        for raw in ("escalate", "quarantine", "deny_hard", "garbage"):
            result = SimpleNamespace(decision=SimpleNamespace(value=raw))
            assert SentinelService._governor_verdict(result) == PolicyVerdict.DENY


class TestEscalationAlerts:
    def test_escalated_case_emits_a2a_alert(self, sentinel_factory, monkeypatch):
        published = []

        class _StubBus:
            def publish(self, channel_id, sender, message, topic, **kw):
                published.append({"channel_id": channel_id, "topic": topic,
                                  "message": json.loads(message)})

        import nexus_os.bridge.a2a_channels as a2a
        monkeypatch.setattr(a2a, "A2AChannelBus", _StubBus)

        service, _, _ = sentinel_factory()
        case = service.create_case(CreateCaseRequest(
            case_id="case-esc", title="escalation test",
            actor_id="tester", idempotency_key="create-case-esc",
        ))
        # Drive to ESCALATED via the internal transition helper
        from nexus_os.sentinel.models import CaseStage
        service._transition(
            case=service.repository.get_case("case-esc"),
            target=CaseStage.ESCALATED,
            actor_id="tester",
            event_type="case_escalated",
            details={"reason": "three strikes"},
        )
        alerts = [p for p in published if p["topic"] == "sentinel"]
        assert alerts, "no A2A alert for ESCALATED case"
        assert alerts[-1]["message"]["type"] == "sentinel-alert"
        assert alerts[-1]["message"]["stage"] == "ESCALATED"

    def test_normal_transition_no_alert(self, sentinel_factory, monkeypatch):
        published = []

        class _StubBus:
            def publish(self, *a, **kw):
                published.append(1)

        import nexus_os.bridge.a2a_channels as a2a
        monkeypatch.setattr(a2a, "A2AChannelBus", _StubBus)
        service, _, _ = sentinel_factory()
        service.create_case(CreateCaseRequest(
            case_id="case-ok", title="no alert test",
            actor_id="tester", idempotency_key="create-case-ok",
        ))
        assert published == []


class TestDbSecurityDefaults:
    def test_passphrase_defaults_to_vault_key(self, monkeypatch, tmp_path):
        from nexus_os.sentinel.api import _db_security_defaults
        import nexus_os.security.vault_encrypt as ve
        monkeypatch.delenv("NEXUS_SENTINEL_DB_PASSPHRASE", raising=False)
        monkeypatch.delenv("NEXUS_SENTINEL_DB_ENCRYPTED", raising=False)
        monkeypatch.delenv("NEXUS_SENTINEL_ALLOW_UNENCRYPTED", raising=False)
        monkeypatch.delenv("NEXUS_VAULT_KEY", raising=False)
        monkeypatch.setattr(ve, "KEY_FILE", tmp_path / "vault.key")
        passphrase, encrypted, allow_unencrypted = _db_security_defaults()
        assert passphrase, "passphrase should autogen from the vault key"
        # pysqlcipher3 is absent in this environment → plaintext fallback,
        # but explicitly allowed and loudly logged
        assert encrypted is False
        assert allow_unencrypted is True

    def test_env_overrides_win(self, monkeypatch):
        from nexus_os.sentinel.api import _db_security_defaults
        monkeypatch.setenv("NEXUS_SENTINEL_DB_PASSPHRASE", "aa" * 16)
        monkeypatch.setenv("NEXUS_SENTINEL_DB_ENCRYPTED", "1")
        monkeypatch.setenv("NEXUS_SENTINEL_ALLOW_UNENCRYPTED", "0")
        passphrase, encrypted, allow_unencrypted = _db_security_defaults()
        assert passphrase == "aa" * 16
        assert encrypted is True
        assert allow_unencrypted is False
