"""nexus_os/archivist/doppelground_bridge.py — DoppelGround → NEXUS Vault Bridge

One-way bridge from DoppelGround (DG) evidence preparation layer to NEXUS OS vault.
DG prepares evidence; NEXUS governs/routes/approves. This bridge never writes back.

Source kinds (12) → Vault channel mapping:
    rules, config           → TRUST (5)   — governance rules, policy configs
    mission, doc,
    deep_research, spec     → SEMANTIC (3) — knowledge, documentation, research
    code, test, skill       → PROCEDURAL (4) — verified execution paths, skills
    rejection_example       → EPISODIC (2) — failure patterns, anti-patterns
    role                    → TASK (6)     — role context, operator definitions
    golden_dataset          → META (7)     — metadata about evaluation datasets

Usage:
    from nexus_os.archivist.doppelground_bridge import DoppelGroundBridge
    
    bridge = DoppelGroundBridge()
    # Bridge a compiled record
    result = bridge.bridge_compiled(compiled_record)
    # Bridge an entire batch
    results = bridge.bridge_batch(compiled_records)
    # Bridge dossiers
    results = bridge.bridge_dossiers(dossiers)
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("nexus_os.archivist.doppelground_bridge")


class DGSourceKind(str, Enum):
    """DoppelGround source kind taxonomy (12 kinds)."""
    RULES = "rules"
    CONFIG = "config"
    MISSION = "mission"
    DOC = "doc"
    DEEP_RESEARCH = "deep_research"
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    SKILL = "skill"
    REJECTION_EXAMPLE = "rejection_example"
    ROLE = "role"
    GOLDEN_DATASET = "golden_dataset"


# Channel mapping: source_kind → NEXUS vault memory channel (integer channel numbers)
# 2=episodic, 3=semantic, 4=procedural, 5=trust, 6=task, 7=meta
SOURCE_KIND_TO_CHANNEL: Dict[str, int] = {
    # governance → TRUST (5)
    DGSourceKind.RULES.value: 5,
    DGSourceKind.CONFIG.value: 5,
    # knowledge → SEMANTIC (3)
    DGSourceKind.MISSION.value: 3,
    DGSourceKind.DOC.value: 3,
    DGSourceKind.DEEP_RESEARCH.value: 3,
    DGSourceKind.SPEC.value: 3,
    # verified paths → PROCEDURAL (4)
    DGSourceKind.CODE.value: 4,
    DGSourceKind.TEST.value: 4,
    DGSourceKind.SKILL.value: 4,
    # failure patterns → EPISODIC (2)
    DGSourceKind.REJECTION_EXAMPLE.value: 2,
    # role context → TASK (6)
    DGSourceKind.ROLE.value: 6,
    # evaluation metadata → META (7)
    DGSourceKind.GOLDEN_DATASET.value: 7,
}

# Integer reverse-lookup for stats/logging (channel name → number)
CHANNEL_NAME_TO_NUM: Dict[str, int] = {
    "sensory": 0, "working": 1, "episodic": 2, "semantic": 3,
    "procedural": 4, "trust": 5, "task": 6, "meta": 7,
}

# ----- Evidence-graded trust for DG-sourced records ----------------------
# Vault write gates (CHANNEL_WRITE_TRUST, NEXUS Trust Framework 4.2):
#   EPISODIC=30, TASK=40, SEMANTIC=65, META=70, PROCEDURAL=80, TRUST=90.
# DG is an *external* evidence-preparation layer; its records must earn
# their trust from evidence grade (continuity writer-fence vocabulary:
# E0 = unverified floor, E1 = verified with proof attached).
#: E0 / missing / unknown grade: below EVERY gated channel threshold, so
#: ungraded DG intel fails gated-channel writes (fail-closed).
TRUST_E0 = 25.0
#: E1 (verified) trust band: [65.0, 79.0] scaled by record quality_score.
#: Never reaches PROCEDURAL (80) or TRUST (90) gates automatically.
TRUST_E1_BASE = 65.0
TRUST_E1_SPAN = 14.0


@dataclass
class BridgeResult:
    """Result of bridging a single record to the vault."""
    source_kind: str
    target_channel: int
    target_channel_name: str
    record_id: Optional[str]
    accepted: bool
    reason: str = ""


class DoppelGroundBridge:
    """One-way bridge from DoppelGround to NEXUS Vault.
    
    DG is the evidence preparation layer; NEXUS is the governance layer.
    This bridge routes DG source cards into the appropriate vault channels
    per the source_kind → channel mapping above.
    
    IMPORTANT: This module must NEVER write back to DG. DG→NEXUS is one-way.
    """

    def __init__(self, trust_score_default: Optional[float] = None):
        """Initialize bridge.

        Args:
            trust_score_default: Operator override for vault write trust.
                Default None means trust is COMPUTED per record from its
                evidence grade and provenance (see :meth:`compute_trust`):
                E0/unverified/missing grade -> 25.0, which is below every
                gated channel threshold, so ungraded DG intel is rejected
                by the vault write gates (fail-closed); E1/verified -> the
                [65.0, 79.0] band. Trust >= 90 is NEVER assigned by
                default; it requires an explicit ``operator_grade`` field
                on the record itself.
                Passing an explicit float here is an operator override that
                applies that trust to every write (legacy behavior; use
                deliberately, it bypasses evidence-graded gating).
        """
        self._trust_default = trust_score_default
        self._stats = {
            "bridged": 0,
            "rejected": 0,
            "errors": 0,
        }
        # Lazy-load vault manager to avoid circular imports
        self._manager = None

    def _get_manager(self):
        """Lazy-load the vault MemoryChannelManager singleton."""
        if self._manager is None:
            from nexus_os.vault.memory_channels import get_manager, MemoryChannel
            self._manager = get_manager()
        return self._manager

    @staticmethod
    def _record_field(record, name: str):
        """Read ``name`` from the record, falling back to its import_record."""
        value = getattr(record, name, None)
        if value is None:
            import_record = getattr(record, "import_record", None)
            if import_record is not None:
                value = getattr(import_record, name, None)
        return value

    def compute_trust(self, record) -> float:
        """Compute writer trust for a DG-sourced record (fail-closed).

        Precedence:
        1. Constructor-level operator override (``trust_score_default`` float).
        2. ``operator_grade`` on the record (or its import_record) -- an
           explicit operator/governance grading, clamped to [0, 100]. This is
           the ONLY way a DG record can carry trust >= 90 (TRUST gate).
        3. ``evidence_grade``:
           - "E1" (verified) -> TRUST_E1_BASE + TRUST_E1_SPAN * quality_score,
             i.e. the [65, 79] band -- passes SEMANTIC (65), never PROCEDURAL
             (80) or TRUST (90).
           - "E0", missing, or unknown -> TRUST_E0 (below every gated
             channel threshold; the vault rejects the write).
        """
        if self._trust_default is not None:
            return float(self._trust_default)

        operator_grade = self._record_field(record, "operator_grade")
        if operator_grade is not None:
            try:
                return max(0.0, min(100.0, float(operator_grade)))
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid operator_grade %r on DG record; "
                    "falling back to evidence grade", operator_grade,
                )

        grade = self._record_field(record, "evidence_grade")
        grade_norm = str(grade).strip().upper() if grade is not None else ""
        if grade_norm == "E1":
            quality = getattr(record, "quality_score", None)
            try:
                q = max(0.0, min(1.0, float(quality)))
            except (TypeError, ValueError):
                q = 0.0
            return TRUST_E1_BASE + TRUST_E1_SPAN * q

        # E0, missing, or unrecognized grade: fail closed.
        return TRUST_E0

    def infer_source_kind(self, compiled_record) -> str:
        """Infer DG source kind from a CompiledRecord's topic tags and file type.
        
        Priority:
        1. Explicit topic tag match (e.g., 'rules' → RULES, 'code' → CODE)
        2. File type heuristic (e.g., FileType.CODE → CODE, FileType.CONFIG → CONFIG)
        3. Default: 'doc' (generic documentation)
        """
        # Check topic tags for explicit source kind match
        from nexus_os.archivist.taxonomy import (
            TOPIC_TO_SOURCE_KIND,
            FILE_TYPE_TO_TOPIC,
            source_kind_for_topic,
        )
        for tag in (compiled_record.topic_tags or []):
            if tag in TOPIC_TO_SOURCE_KIND:
                return TOPIC_TO_SOURCE_KIND[tag]

        # File type heuristic via shared taxonomy
        try:
            from nexus_os.archivist.import_stage import FileType
            ft = compiled_record.import_record.file_type
            ft_value = ft.value if hasattr(ft, "value") else str(ft)
            if ft_value in FILE_TYPE_TO_TOPIC:
                topic = FILE_TYPE_TO_TOPIC[ft_value]
                return source_kind_for_topic(topic)
        except Exception:
            pass

        return DGSourceKind.DOC.value  # default

    def bridge_compiled(self, compiled_record) -> BridgeResult:
        """Bridge a single CompiledRecord to the vault.
        
        Args:
            compiled_record: A CompiledRecord from the compile stage.
        
        Returns:
            BridgeResult with acceptance status and record ID.
        """
        source_kind = self.infer_source_kind(compiled_record)
        channel_num = SOURCE_KIND_TO_CHANNEL.get(source_kind, 3)  # default SEMANTIC=3
        channel_name = next(
            (name for name, num in CHANNEL_NAME_TO_NUM.items() if num == channel_num),
            "semantic",
        )
        
        from nexus_os.vault.memory_channels import MemoryChannel
        channel = MemoryChannel(channel_name)

        # Per-record trust from evidence grade / operator grade (fail-closed),
        # unless the constructor received an explicit operator override.
        trust = self.compute_trust(compiled_record)

        # Build content from the compiled record
        ir = compiled_record.import_record
        content_parts = [
            f"[DG→NEXUS] Source: {ir.file_path}",
            f"Title: {ir.title or 'untitled'}",
            f"Type: {getattr(ir.file_type, 'value', ir.file_type)}",
            f"Priority: {ir.priority}",
            f"Topics: {', '.join(compiled_record.topic_tags or [])}",
        ]
        if compiled_record.quality_score:
            content_parts.append(f"Quality: {compiled_record.quality_score:.2f}")
        if ir.arxiv_id:
            content_parts.append(f"arXiv: {ir.arxiv_id}")
        content = "\n".join(content_parts)

        # Route to appropriate vault write method
        try:
            manager = self._get_manager()
            record = None
            agent_id = "doppelground-bridge"

            if channel == MemoryChannel.SEMANTIC:
                record = manager.append_semantic(
                    agent_id=agent_id,
                    content=content,
                    topic_tags=compiled_record.topic_tags,
                    source_dossier_id=compiled_record.dossier_topic,
                    trust_score=trust,
                    trace_id=f"dg-{ir.blake3_hash[:16]}" if hasattr(ir, 'blake3_hash') else None,
                )
            elif channel == MemoryChannel.TRUST:
                # Rules/config go to TRUST as governance entries
                record = manager.append_trust(
                    agent_id=agent_id,
                    lane="governance",
                    trust_score=trust,
                    evidence_count=1,
                    content=content,
                    trace_id=f"dg-{ir.blake3_hash[:16]}" if hasattr(ir, 'blake3_hash') else None,
                    writer_trust=trust,
                )
            elif channel == MemoryChannel.PROCEDURAL:
                record = manager.append_procedural(
                    agent_id=agent_id,
                    content=content,
                    skill_tags=compiled_record.topic_tags or [],
                    confidence=compiled_record.quality_score or 0.5,
                    trust_score=trust,
                    trace_id=f"dg-{ir.blake3_hash[:16]}" if hasattr(ir, 'blake3_hash') else None,
                )
            elif channel == MemoryChannel.EPISODIC:
                record = manager.append_episodic(
                    agent_id=agent_id,
                    content=content,
                    outcome="failure",  # rejection examples are failures
                    failure_type="rejection_pattern",
                    trust_score=trust,
                    trace_id=f"dg-{ir.blake3_hash[:16]}" if hasattr(ir, 'blake3_hash') else None,
                )
            elif channel == MemoryChannel.TASK:
                record = manager.append_task(
                    agent_id=agent_id,
                    content=content,
                    task_id=f"role-{compiled_record.dossier_topic or 'unknown'}",
                    task_status="active",
                    trust_score=trust,
                    trace_id=f"dg-{ir.blake3_hash[:16]}" if hasattr(ir, 'blake3_hash') else None,
                )
            elif channel == MemoryChannel.META:
                record = manager.append_meta(
                    agent_id=agent_id,
                    meta_type="golden_dataset",
                    content=content,
                    trust_score=trust,
                    trace_id=f"dg-{ir.blake3_hash[:16]}" if hasattr(ir, 'blake3_hash') else None,
                )
            else:
                # Fallback: write to SEMANTIC
                record = manager.append_semantic(
                    agent_id=agent_id,
                    content=content,
                    topic_tags=compiled_record.topic_tags,
                    trust_score=trust,
                )

            if record is not None:
                record_id = record.record_id if hasattr(record, 'record_id') else None
                self._stats["bridged"] += 1
                return BridgeResult(
                    source_kind=source_kind,
                    target_channel=channel_num,
                    target_channel_name=channel_name,
                    record_id=record_id,
                    accepted=True,
                )
            else:
                self._stats["rejected"] += 1
                return BridgeResult(
                    source_kind=source_kind,
                    target_channel=channel_num,
                    target_channel_name=channel_name,
                    record_id=None,
                    accepted=False,
                    reason="vault_write_returned_none_trust_gate_blocked",
                )

        except Exception as e:
            self._stats["errors"] += 1
            logger.error("Bridge write failed for %s: %s", ir.file_path, e)
            return BridgeResult(
                source_kind=source_kind,
                target_channel=channel_num,
                target_channel_name=channel_name,
                record_id=None,
                accepted=False,
                reason=f"exception: {e}",
            )

    def bridge_batch(self, compiled_records: list) -> List[BridgeResult]:
        """Bridge a batch of CompiledRecords to the vault.
        
        Args:
            compiled_records: List of CompiledRecord objects from compile stage.
        
        Returns:
            List of BridgeResult objects.
        """
        results = []
        for record in compiled_records:
            result = self.bridge_compiled(record)
            results.append(result)
        logger.info(
            "Bridge batch: %d records, %d bridged, %d rejected, %d errors",
            len(compiled_records), 
            sum(1 for r in results if r.accepted),
            sum(1 for r in results if not r.accepted and "trust_gate" in r.reason),
            sum(1 for r in results if not r.accepted and "exception" in r.reason),
        )
        return results

    def bridge_dossiers(self, dossiers: list) -> List[BridgeResult]:
        """Bridge dossiers (from Fit stage) to the vault SEMANTIC channel.
        
        Dossiers always go to SEMANTIC (3) — they represent consolidated knowledge.
        
        Args:
            dossiers: List of Dossier objects from the Fit stage.
        
        Returns:
            List of BridgeResult objects.
        """
        results = []
        for dossier in dossiers:
            try:
                manager = self._get_manager()
                trust = self.compute_trust(dossier)
                content = f"[DG→NEXUS Dossier] {dossier.title}\n\n{dossier.content[:2000]}"
                record = manager.append_semantic(
                    agent_id="doppelground-bridge",
                    content=content,
                    topic_tags=dossier.tags if hasattr(dossier, 'tags') else [dossier.topic],
                    source_dossier_id=dossier.topic if hasattr(dossier, 'topic') else None,
                    trust_score=trust,
                )
                if record is not None:
                    record_id = record.record_id if hasattr(record, 'record_id') else None
                    self._stats["bridged"] += 1
                    results.append(BridgeResult(
                        source_kind="dossier",
                        target_channel=3,
                        target_channel_name="semantic",
                        record_id=record_id,
                        accepted=True,
                    ))
                else:
                    self._stats["rejected"] += 1
                    results.append(BridgeResult(
                        source_kind="dossier",
                        target_channel=3,
                        target_channel_name="semantic",
                        record_id=None,
                        accepted=False,
                        reason="vault_write_returned_none_trust_gate_blocked",
                    ))
            except Exception as e:
                self._stats["errors"] += 1
                logger.error("Dossier bridge failed for %s: %s", 
                           getattr(dossier, 'topic', 'unknown'), e)
                results.append(BridgeResult(
                    source_kind="dossier",
                    target_channel=3,
                    target_channel_name="semantic",
                    record_id=None,
                    accepted=False,
                    reason=f"exception: {e}",
                ))
        return results

    def get_stats(self) -> Dict[str, int]:
        """Return bridge statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset bridge statistics counters."""
        self._stats = {"bridged": 0, "rejected": 0, "errors": 0}


# Singleton
_bridge: Optional[DoppelGroundBridge] = None


def get_bridge() -> DoppelGroundBridge:
    """Get the singleton DoppelGroundBridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = DoppelGroundBridge()
    return _bridge
