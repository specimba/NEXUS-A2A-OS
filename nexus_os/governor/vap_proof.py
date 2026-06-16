"""VAP Proof Chain (light) — Hash-chain logging for model relay calls."""

from __future__ import annotations
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VAPEntry:
    level: int  # 1=identity, 2=context, 3=non-repudiation, 4=integrity
    agent_id: str
    model: str
    provider: str
    intent: str
    request_hash: str
    chain_hash: str
    timestamp: float = 0.0
    entry_id: str = ""


class VAPLight:
    def __init__(self):
        self._entries: list[VAPEntry] = []

    def append(self, agent_id: str, model: str, provider: str, intent: str, payload: str = "") -> VAPEntry:
        ts = time.time()
        prev_chain = self._entries[-1].chain_hash if self._entries else "0" * 64
        for level in range(1, 5):
            raw = f"{level}|{agent_id}|{model}|{provider}|{intent}|{payload}|{ts}|{prev_chain}"
            sig = hashlib.sha256(raw.encode()).hexdigest()
            chain = hashlib.sha256(f"{prev_chain}|{sig}".encode()).hexdigest()
            entry = VAPEntry(
                level=level, agent_id=agent_id, model=model, provider=provider,
                intent=intent, request_hash=sig, chain_hash=chain,
                timestamp=ts, entry_id=str(uuid.uuid4()),
            )
            self._entries.append(entry)
            prev_chain = chain
        return self._entries[-1]

    @property
    def entries(self) -> list[VAPEntry]:
        return list(self._entries)

    def verify(self) -> bool:
        prev = "0" * 64
        for entry in self._entries:
            raw = f"{entry.level}|{entry.agent_id}|{entry.model}|{entry.provider}|{entry.intent}|{entry.request_hash}|{entry.timestamp}|{prev}"
            expected_sig = hashlib.sha256(raw.encode()).hexdigest()
            expected_chain = hashlib.sha256(f"{prev}|{expected_sig}".encode()).hexdigest()
            if entry.chain_hash != expected_chain:
                return False
            prev = entry.chain_hash
        return True

    def summary(self) -> dict:
        return {
            "total_entries": len(self._entries),
            "verified": self.verify(),
            "last_entry": {
                "agent_id": self._entries[-1].agent_id,
                "model": self._entries[-1].model,
                "timestamp": self._entries[-1].timestamp,
            } if self._entries else None,
        }
