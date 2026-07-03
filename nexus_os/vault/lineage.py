"""vault/lineage.py — Memory chain-of-custody (MemLineage, arXiv 2605.14421).

The 8-channel vault trust-gates WRITES but never tracked DERIVATION: a
payload ingested from an external source, summarized by the consolidation
daemon, and re-committed under NEXUS's own principal arrives at higher
channels laundered — its untrusted ancestry invisible. MemLineage closes
that class: every wired write gets a lineage edge, taint propagates
max-of-strong-edges (any tainted ancestor taints the derivation), and a
sensitive-action gate refuses dispatches whose justification descends
from an external/untrusted ancestor while leaving benign recall alone.

Log integrity: append-only JSONL, hash-chained (each row carries the
previous row's SHA-256) and HMAC-signed with the vault master key when
one is available — the same key file the P2-5 channel encryption uses.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

LINEAGE_LOG_PATH = Path(os.path.expanduser("~")) / ".nexus" / "memory_lineage.jsonl"

#: origin classes; "external" starts tainted, others inherit from parents
ORIGIN_EXTERNAL = "external"
ORIGIN_INTERNAL = "internal"
ORIGIN_SYSTEM = "system"
VALID_ORIGINS = {ORIGIN_EXTERNAL, ORIGIN_INTERNAL, ORIGIN_SYSTEM}


@dataclass
class LineageEntry:
    entry_id: str
    agent_id: str
    channel: str
    origin: str
    parent_ids: List[str] = field(default_factory=list)
    tainted: bool = False
    ts: float = field(default_factory=time.time)
    prev_hash: str = ""
    sig: Optional[str] = None

    def payload(self) -> str:
        """Canonical signable payload (excludes sig)."""
        return json.dumps({
            "entry_id": self.entry_id,
            "agent_id": self.agent_id,
            "channel": self.channel,
            "origin": self.origin,
            "parent_ids": self.parent_ids,
            "tainted": self.tainted,
            "ts": round(self.ts, 6),
            "prev_hash": self.prev_hash,
        }, sort_keys=True)

    def row_hash(self) -> str:
        return hashlib.sha256(self.payload().encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        data = json.loads(self.payload())
        data["sig"] = self.sig
        return json.dumps(data, sort_keys=True)


class LineageLog:
    """Append-only, hash-chained derivation log with an in-memory index."""

    def __init__(self, path: "Path | None" = None, persist: bool = True):
        self._path = Path(path) if path else LINEAGE_LOG_PATH
        self._persist = persist
        self._index: Dict[str, LineageEntry] = {}
        self._last_hash = ""
        self._lock = threading.RLock()
        self._key = self._load_key()
        if persist and self._path.exists():
            self._load()

    @staticmethod
    def _load_key() -> Optional[bytes]:
        try:
            from nexus_os.security.vault_encrypt import load_master_key
            return load_master_key(generate=True)
        except Exception:
            return None

    def _sign(self, payload: str) -> Optional[str]:
        if self._key is None:
            return None
        return hmac_mod.new(self._key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def _load(self) -> None:
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = LineageEntry(
                        entry_id=data["entry_id"],
                        agent_id=data.get("agent_id", ""),
                        channel=data.get("channel", ""),
                        origin=data.get("origin", ORIGIN_INTERNAL),
                        parent_ids=data.get("parent_ids", []),
                        tainted=bool(data.get("tainted", False)),
                        ts=float(data.get("ts", 0.0)),
                        prev_hash=data.get("prev_hash", ""),
                        sig=data.get("sig"),
                    )
                    self._index[entry.entry_id] = entry
                    self._last_hash = entry.row_hash()
                except (KeyError, ValueError, json.JSONDecodeError):
                    continue
        except OSError:
            logger.warning("Lineage log unreadable at %s", self._path, exc_info=True)

    # ── write path ────────────────────────────────────────────────

    def record(
        self,
        entry_id: str,
        agent_id: str,
        channel: str,
        origin: str = ORIGIN_INTERNAL,
        parent_ids: Optional[Iterable[str]] = None,
    ) -> LineageEntry:
        """Record a derivation edge; returns the entry with computed taint.

        Taint rule (max-of-strong-edges): tainted iff origin is external
        OR any parent is tainted. A parent with NO lineage record taints
        the derivation (fail-closed — unrecorded ancestry cannot prove
        cleanliness).
        """
        if origin not in VALID_ORIGINS:
            origin = ORIGIN_EXTERNAL  # unknown origin claims are untrusted
        parents = [p for p in (parent_ids or []) if p]
        tainted = origin == ORIGIN_EXTERNAL
        for pid in parents:
            parent = self._index.get(pid)
            if parent is None or parent.tainted:
                tainted = True
                break
        with self._lock:
            entry = LineageEntry(
                entry_id=entry_id,
                agent_id=agent_id,
                channel=channel,
                origin=origin,
                parent_ids=parents,
                tainted=tainted,
                prev_hash=self._last_hash,
            )
            entry.sig = self._sign(entry.payload())
            self._index[entry.entry_id] = entry
            self._last_hash = entry.row_hash()
            if self._persist:
                try:
                    self._path.parent.mkdir(parents=True, exist_ok=True)
                    with open(self._path, "a", encoding="utf-8") as f:
                        f.write(entry.to_json() + "\n")
                except OSError:
                    logger.warning("Lineage append failed", exc_info=True)
        return entry

    # ── read path ─────────────────────────────────────────────────

    def is_tainted(self, entry_id: str) -> Optional[bool]:
        """True/False for recorded entries; None when no lineage exists."""
        entry = self._index.get(entry_id)
        return entry.tainted if entry is not None else None

    def get(self, entry_id: str) -> Optional[LineageEntry]:
        return self._index.get(entry_id)

    def gate_sensitive_action(
        self, justification_ids: Iterable[str],
    ) -> Tuple[bool, str]:
        """Refuse a sensitive dispatch justified by tainted memory.

        Deny when ANY justification entry has tainted lineage. Entries
        without lineage records pass (compat with unwired channels) but
        are named in the reason so callers can tighten later.
        """
        tainted, unknown = [], []
        for jid in justification_ids:
            verdict = self.is_tainted(jid)
            if verdict is True:
                tainted.append(jid)
            elif verdict is None:
                unknown.append(jid)
        if tainted:
            return False, (
                f"lineage gate DENY: {len(tainted)} justification(s) descend "
                f"from untrusted ancestry: {tainted[:5]}"
            )
        reason = "lineage gate ALLOW"
        if unknown:
            reason += f" ({len(unknown)} justification(s) without lineage records)"
        return True, reason

    def verify_chain(self) -> Dict[str, object]:
        """Recompute the hash chain + signatures over the persisted log."""
        if not self._path.exists():
            return {"ok": True, "entries": 0, "reason": "no_log"}
        prev = ""
        checked = 0
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                return {"ok": False, "entries": checked, "reason": "unparseable_row"}
            entry = LineageEntry(
                entry_id=data["entry_id"],
                agent_id=data.get("agent_id", ""),
                channel=data.get("channel", ""),
                origin=data.get("origin", ORIGIN_INTERNAL),
                parent_ids=data.get("parent_ids", []),
                tainted=bool(data.get("tainted", False)),
                ts=float(data.get("ts", 0.0)),
                prev_hash=data.get("prev_hash", ""),
            )
            if entry.prev_hash != prev:
                return {"ok": False, "entries": checked, "reason": "chain_break",
                        "at": entry.entry_id}
            if self._key is not None and data.get("sig"):
                if not hmac_mod.compare_digest(
                    data["sig"], self._sign(entry.payload()) or ""
                ):
                    return {"ok": False, "entries": checked, "reason": "bad_signature",
                            "at": entry.entry_id}
            prev = entry.row_hash()
            checked += 1
        return {"ok": True, "entries": checked}


# ── Process-wide singleton ─────────────────────────────────────────────

_log_singleton: Optional[LineageLog] = None
_log_lock = threading.Lock()


def get_lineage_log() -> LineageLog:
    global _log_singleton
    if _log_singleton is None:
        with _log_lock:
            if _log_singleton is None:
                _log_singleton = LineageLog()
    return _log_singleton


def set_lineage_log(log: Optional[LineageLog]) -> None:
    """Replace the singleton (tests / explicit wiring). None resets to lazy."""
    global _log_singleton
    with _log_lock:
        _log_singleton = log
