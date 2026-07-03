"""Vault test isolation: never let tests touch the real encrypted channel
snapshot (~/.nexus/memory_channels.enc) or vault key file."""
import pytest


@pytest.fixture(autouse=True)
def isolate_channel_snapshot(tmp_path, monkeypatch):
    import nexus_os.vault.memory_channels as mc
    import nexus_os.security.vault_encrypt as ve
    import nexus_os.vault.lineage as lineage
    monkeypatch.setattr(mc, "CHANNELS_ENC_PATH", tmp_path / "memory_channels.enc")
    monkeypatch.setattr(ve, "KEY_FILE", tmp_path / "vault.key")
    monkeypatch.setattr(lineage, "LINEAGE_LOG_PATH", tmp_path / "memory_lineage.jsonl")
    lineage.set_lineage_log(None)  # fresh singleton per test, tmp-backed
    yield
    lineage.set_lineage_log(None)
