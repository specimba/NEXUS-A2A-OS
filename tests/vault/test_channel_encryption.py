"""tests/vault/test_channel_encryption.py — P2-5: channel buffers persist
AES-256-GCM encrypted at rest; no key → no plaintext on disk."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_os.vault.memory_channels import MemoryChannel, MemoryChannelManager

CANARY = "CANARY-sk-vault-secret-77aa88bb"
TEST_KEY_HEX = "aa" * 32


@pytest.fixture
def keyed_env(monkeypatch):
    monkeypatch.setenv("NEXUS_VAULT_KEY", TEST_KEY_HEX)


def _populated_manager():
    m = MemoryChannelManager()
    m.append_episodic(
        agent_id="agent-a", content=CANARY, outcome="success",
        duration_ms=12.0, token_count=42, failure_type=None, trace_id="t-1",
    )
    m.append_trust(
        agent_id="agent-a", lane="research", trust_score=0.8,
        evidence_count=3, content="trust note", writer_trust=100.0,
    )
    return m


class TestEncryptedRoundTrip:
    def test_save_and_load_round_trip(self, tmp_path, keyed_env):
        snap = tmp_path / "channels.enc"
        m1 = _populated_manager()
        assert m1.save_to_disk(snap) is True
        assert snap.exists()

        m2 = MemoryChannelManager()
        restored = m2.load_from_disk(snap)
        assert restored == 2
        episodic = m2._buffers["agent-a"][MemoryChannel.EPISODIC]
        assert len(episodic) == 1
        assert episodic[0].content == CANARY
        assert episodic[0].channel == MemoryChannel.EPISODIC
        trust = m2._buffers["agent-a"][MemoryChannel.TRUST]
        assert trust[0].trust_score == pytest.approx(0.8)

    def test_on_disk_artifact_has_no_plaintext(self, tmp_path, keyed_env):
        """Roadmap grep-canary gate."""
        snap = tmp_path / "channels.enc"
        _populated_manager().save_to_disk(snap)
        raw = snap.read_bytes()
        assert CANARY.encode() not in raw
        assert b"agent-a" not in raw
        assert b"episodic" not in raw

    def test_tampered_snapshot_loads_nothing(self, tmp_path, keyed_env):
        snap = tmp_path / "channels.enc"
        _populated_manager().save_to_disk(snap)
        blob = bytearray(snap.read_bytes())
        blob[-1] ^= 0xFF  # flip a ciphertext bit → GCM auth must fail
        snap.write_bytes(bytes(blob))
        m2 = MemoryChannelManager()
        assert m2.load_from_disk(snap) == 0
        assert not m2._buffers["agent-a"][MemoryChannel.EPISODIC]

    def test_wrong_key_loads_nothing(self, tmp_path, monkeypatch):
        snap = tmp_path / "channels.enc"
        monkeypatch.setenv("NEXUS_VAULT_KEY", TEST_KEY_HEX)
        _populated_manager().save_to_disk(snap)
        monkeypatch.setenv("NEXUS_VAULT_KEY", "bb" * 32)
        assert MemoryChannelManager().load_from_disk(snap) == 0


class TestFailClosed:
    def test_no_key_no_write(self, tmp_path, monkeypatch):
        import nexus_os.vault.memory_channels as mc
        monkeypatch.delenv("NEXUS_VAULT_KEY", raising=False)
        import nexus_os.security.vault_encrypt as ve
        monkeypatch.setattr(ve, "load_master_key", lambda generate=False: None)
        snap = tmp_path / "channels.enc"
        m = _populated_manager()
        assert m.save_to_disk(snap) is False
        assert not snap.exists()

    def test_missing_snapshot_returns_zero(self, tmp_path, keyed_env):
        assert MemoryChannelManager().load_from_disk(tmp_path / "nope.enc") == 0


class TestLibraryPrimitives:
    def test_encrypt_decrypt_bytes(self):
        from nexus_os.security.vault_encrypt import decrypt_bytes, encrypt_bytes
        key = bytes.fromhex(TEST_KEY_HEX)
        blob = encrypt_bytes(b"payload", key, b"aad")
        assert b"payload" not in blob
        assert decrypt_bytes(blob, key, b"aad") == b"payload"

    def test_aad_mismatch_fails(self):
        from nexus_os.security.vault_encrypt import decrypt_bytes, encrypt_bytes
        key = bytes.fromhex(TEST_KEY_HEX)
        blob = encrypt_bytes(b"payload", key, b"aad-one")
        with pytest.raises(Exception):
            decrypt_bytes(blob, key, b"aad-two")

    def test_env_key_resolution(self, monkeypatch):
        from nexus_os.security import vault_encrypt as ve
        monkeypatch.setenv("NEXUS_VAULT_KEY", TEST_KEY_HEX)
        assert ve.load_master_key() == bytes.fromhex(TEST_KEY_HEX)

    def test_keyfile_generation(self, tmp_path, monkeypatch):
        from nexus_os.security import vault_encrypt as ve
        monkeypatch.delenv("NEXUS_VAULT_KEY", raising=False)
        monkeypatch.setattr(ve, "KEY_FILE", tmp_path / "vault.key")
        assert ve.load_master_key(generate=False) is None
        key = ve.load_master_key(generate=True)
        assert isinstance(key, bytes) and len(key) == 32
        # Second resolution reads the same key back
        assert ve.load_master_key(generate=False) == key
