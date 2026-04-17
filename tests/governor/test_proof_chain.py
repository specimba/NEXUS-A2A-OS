"""tests/governor/test_proof_chain.py — VAP 4-layer tests"""
import pytest
from nexus_os.governor.proof_chain import VAPProofChain

def test_vap_chain_creation():
    chain = VAPProofChain()
    assert hasattr(chain, "_entries")
    assert len(chain.entries) == 0

def test_vap_chain_record_and_verify():
    chain = VAPProofChain()
    r1 = chain.record("test-agent", "test-action", "resource-1", {"key": "value"}, "success")
    r2 = chain.record("test-agent", "test-action", "resource-2", {}, "success")
    assert len(chain.entries) == 2
    assert r1.signature is not None
    assert r1.chain_hash != "0" * 64
    assert chain.verify_chain() is True

def test_vap_chain_summary():
    chain = VAPProofChain()
    chain.record("agent1", "action1", "res1", {}, "ok")
    chain.record("agent2", "action2", "res2", {}, "ok")
    assert len(chain.entries) == 2
    assert chain.verify_chain() is True
