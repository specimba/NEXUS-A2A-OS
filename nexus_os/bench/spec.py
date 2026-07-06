"""NEXUS-BENCH probe schema.

Each probe is one prompt+expected_behavior as one (dimension, model) test.

A probe SET is a 200-item collection (technically: 12 dimensions x ~17
probes = 204, allowing a slight over-allocation per dimension).

For NEXUS-BENCH V1, the actual probe ITEMS live in a separate file
(`rubrics/probes_v1.py`) that is CLASSIFIED by default - real-session
content may carry operator fingerprints.

This module provides the FORMAT spec and loader scaffolding.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Expected:
    """What the ideal model output should look like for this probe."""
    pattern: str | None = None
    must_contain: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()
    format: str | None = None  # e.g., "json" | "code:python" | "plain"
    length_min: int = 0
    length_max: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProbeSet:
    """A collection of probe items for one dimension."""
    dimension_id: str
    title: str
    probes: list[dict[str, Any]] = field(default_factory=list)
    hard_constraint: bool = False

    def to_dict(self) -> dict:
        return {
            "dimension_id": self.dimension_id,
            "title": self.title,
            "probes": list(self.probes),
            "hard_constraint": self.hard_constraint,
        }


@dataclass
class Probe:
    """One evaluation prompt with expected behavior."""
    id: str
    prompt: str
    expected: Expected = field(default_factory=Expected)
    difficulty: str = "medium"  # easy | medium | expert
    domain: str = "general"
    anonymized: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "difficulty": self.difficulty,
            "domain": self.domain,
            "anonymized": self.anonymized,
            "prompt": self.prompt,
            "expected": self.expected.to_dict(),
        }


def probe_to_json(probe: Probe) -> str:
    return json.dumps(probe.to_dict(), ensure_ascii=False, indent=2)


def load_probesets_from_module(module_path: Path) -> list[ProbeSet]:
    """Import a Python module that defines NEXUS-BENCH probe sets.

    The module is expected to expose a top-level `PROBE_SETS` list of
    ProbeSet instances. Failing that, it should expose `probes()` returning
    the list.
    """
    import importlib.util
    if not module_path.exists():
        raise FileNotFoundError(module_path)
    spec = importlib.util.spec_from_file_location("probes_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module spec: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "PROBE_SETS"):
        return list(module.PROBE_SETS)
    if callable(getattr(module, "probes", None)):
        return list(module.probes())
    raise AttributeError(
        f"Module {module_path} lacks both PROBE_SETS and probes()"
    )


def save_probesets_jsonl(probesets: list[ProbeSet], target: Path) -> int:
    """Persist probes to JSONL."""
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with target.open("w", encoding="utf-8") as fh:
        for ps in probesets:
            fh.write(json.dumps(ps.to_dict(), ensure_ascii=False) + "\n")
            total += 1
    return total
