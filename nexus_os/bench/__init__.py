"""NEXUS-BENCH operator-realistic frontier benchmarking.

This package complements `nexus_os.benchmark` (which tracks governance /
security / ops / R&D / integration tracks).

NEXUS-BENCH adds a frontier-model evaluation tier driven by 12 dimensions
of operator-realistic quality, sourced from real NEXUS session prompts.
The 12-dimension schema is operator-derived: it was formalized from the
operator's personal curation hierarchy (which models are trusted for what
task) by reverse-engineering what those rankings *imply* about the
dimensions a serious practitioner cares about.

PUBLIC surface (open-source):
- schemas (12 dimensions)
- probe specification format
- run reports in JSON
- rubric scoring algorithm

OPERATOR surface (private):
- the actual probe items (real-session-derived; potentially sensitive)
- per-model reasoning traces from frontier probes
- any DPO/SFT-ready training corpora
"""
__version__ = "0.1.0"
