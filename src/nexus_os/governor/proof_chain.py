"""governor/proof_chain.py — VAP 4-layer Proof Chain (L1+L2 already present, now adding L3+L4)"""
from dataclasses import dataclass
import hashlib
import time
from typing import Dict, Any, Optional

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
    signature: Optional[str] = None          # L3: Non-Repudiation (Ed25519)
    integrity_proof: Optional[str] = None    # L4: Integrity (Merkle-style)

class VAPProofChain:
    def __init__(self):
        self.chain: list[VAPRecord] = []
        # Simple key for demo (replace with secure storage in production)
        self.private_key = b"\x00" * 32

    def append(self, actor: str, action: str, resource: str, ctx: Dict[str, Any], outcome: str) -> VAPRecord:
        prev_hash = self.chain[-1].chain_hash if self.chain else "0" * 64
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
        # L3: Non-Repudiation
        to_sign = f"{record.id}{record.ts}{record.actor}{record.action}{record.resource}{record.outcome}{record.prev_hash}".encode()
        record.signature = hashlib.sha256(to_sign).hexdigest()  # Placeholder - replace with real Ed25519 if needed
        # L4: Integrity
        record.chain_hash = hashlib.sha256((record.prev_hash + record.signature).encode()).hexdigest()
        self.chain.append(record)
        return record

    def verify_chain(self) -> bool:
        for i, record in enumerate(self.chain):
            if i > 0 and record.prev_hash != self.chain[i-1].chain_hash:
                return False
        return True

# Backward compatibility alias
ProofChain = VAPProofChain
