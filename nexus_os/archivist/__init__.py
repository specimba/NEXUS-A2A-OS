"""nexus_os/archivist/__init__.py — ARCHIVIST Pipeline Package

3-stage pipeline:
1. Import: file discovery, classification, deduplication, priority scoring
2. Compile: 7 admission classes, semantic tagging, wiki admission gate
3. Fit: dossier synthesis, project-fit scoring, wiki markdown generation

References:
- DoppelGround 3-stage pipeline (Import → Compile → Fit/Mission)
- NEXUS Trust Framework §4.2: Trust-gated SEMANTIC channel writes
- Du (2026) — Memory for Autonomous LLM Agents: 4 memory types
"""

from nexus_os.archivist.import_stage import ArchivistImporter, ImportRecord, FileType, AdmissionClass

__all__ = [
    "ArchivistImporter",
    "ImportRecord",
    "FileType",
    "AdmissionClass",
]
