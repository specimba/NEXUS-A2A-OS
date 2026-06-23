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
from nexus_os.archivist.compile import ArchivistCompiler, CompiledRecord
from nexus_os.archivist.fit import ArchivistFitter, Dossier

__all__ = [
    # Stage 1: Import
    "ArchivistImporter",
    "ImportRecord",
    "FileType",
    "AdmissionClass",
    # Stage 2: Compile
    "ArchivistCompiler",
    "CompiledRecord",
    # Stage 3: Fit
    "ArchivistFitter",
    "Dossier",
]
