"""skill_auditor_seed — operator-approved experiment lane.

This directory is a fenced, non-canonical area per `docs/coordination/NEO_EVIDENCE_MATRIX_2026-06-20.md`.
Loading rules from here requires:

    python loader_stub.py --path attack_taxonomy_seed.yaml --load-papers09-seed

Until that gating token is supplied the loader does NOTHING.
"""

__all__ = [
    "GATING_TOKEN",
]

GATING_TOKEN = "--load-papers09-seed"
