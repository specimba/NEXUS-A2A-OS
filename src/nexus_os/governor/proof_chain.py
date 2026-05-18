"""governor/proof_chain.py — VAP 4-layer Proof Chain (L1+L2+L3+L4)"""
from dataclasses import dataclass
import hashlib
import json
import time
from typing import Dict, Any, Optional, List

@dataclass
class VAPRecord:
    id: str
    ts: float
    actor: str
    action: str
    resource: str
    ctx: Dict[str, Any]
    outcome: str
    prev_hash: str
    chain_hash: str
    signature: Optional[str] = None          # L3: Non-Repudiation
    integrity_proof: Optional[str] = None    # L4: Integrity

class VAPProofChain:
    def __init__(self):
        self._entries: List[VAPRecord] = []   # test expects _entries
        self._latest_hash = "0" * 64

    def record(self, actor: str = None, action: str = None, resource: str = "", ctx: Dict[str, Any] = None, outcome: str = "", agent_id: str = None, details: Dict[str, Any] = None, level: str = "INFO") -> VAPRecord:
        """Primary method expected by tests.
        
        Supports both positional and keyword arguments for compatibility.
        """
        # Handle keyword arguments from compliance.py
        if agent_id is not None:
            actor = actor or agent_id
        if details is not None:
            ctx = ctx or details
        ctx = ctx or {}
        return self.append(actor or "unknown", action or "unknown", resource, ctx, outcome or level)

    def append(self, actor: str, action: str, resource: str, ctx: Dict[str, Any], outcome: str) -> VAPRecord:
        prev_hash = self._entries[-1].chain_hash if self._entries else "0" * 64
        record = VAPRecord(
            id=hashlib.sha256(f"{time.time_ns()}".encode()).hexdigest(),
            ts=time.time(),
            actor=actor,
            action=action,
            resource=resource,
            ctx=ctx,
            outcome=outcome,
            prev_hash=prev_hash,
            chain_hash="",
            signature=None,
            integrity_proof=None
        )
        # L3: Non-Repudiation placeholder. This is deterministic integrity,
        # not a keyed signature.
        record.signature = self._record_signature(record)
        # L4: Integrity
        record.chain_hash = self._record_chain_hash(record.prev_hash, record.signature)
        self._entries.append(record)
        self._latest_hash = record.chain_hash
        return record

    def verify_chain(self) -> bool:
        previous_hash = "0" * 64
        for record in self._entries:
            if record.prev_hash != previous_hash:
                return False
            expected_signature = self._record_signature(record)
            if record.signature != expected_signature:
                return False
            expected_chain_hash = self._record_chain_hash(record.prev_hash, record.signature or "")
            if record.chain_hash != expected_chain_hash:
                return False
            previous_hash = record.chain_hash
        return True

    def _record_signature(self, record: VAPRecord) -> str:
        payload = {
            "id": record.id,
            "ts": record.ts,
            "actor": record.actor,
            "action": record.action,
            "resource": record.resource,
            "ctx": record.ctx,
            "outcome": record.outcome,
            "prev_hash": record.prev_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _record_chain_hash(self, prev_hash: str, signature: str) -> str:
        return hashlib.sha256((prev_hash + signature).encode()).hexdigest()

    @property
    def entries(self):
        """Alias for test compatibility."""
        return self._entries


# Alias for backward compatibility
ProofChain = VAPProofChain
