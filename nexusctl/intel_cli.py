"""nexusctl intel commands — LLMWiki dossier pipeline CLI surface.

Wraps nexus_os.nexusclaw.wiki_intel_pipeline.WikiIntelPipeline to expose
DoppelGround→LLMWiki document ingestion, dossier writing, and linting
as nexusctl subcommands. Each subcommand returns (code, payload_dict).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json_file(file_path: str) -> Any:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return json.loads(p.read_text(encoding="utf-8"))


def run_intel(args: Any) -> tuple[int, dict[str, Any]]:
    command = args.intel_command

    try:
        from nexus_os.nexusclaw.wiki_intel_pipeline import WikiIntelPipeline
    except ImportError as exc:
        return 2, {"status": "blocked", "error": f"WikiIntelPipeline import failed: {exc}"}

    wiki_output_dir = getattr(args, "wiki_output_dir", None)
    if wiki_output_dir:
        wiki_path = Path(wiki_output_dir)
        memory_path = wiki_path.parent / "memory"
        pipeline = WikiIntelPipeline(wiki_output_dir=wiki_path, memory_dir=memory_path)
    else:
        pipeline = WikiIntelPipeline()

    if command == "stats":
        known = pipeline.known_dossier_count()
        lint = pipeline.lint()
        return 0, {
            "status": "ok",
            "command": "intel stats",
            "wiki_output_dir": str(pipeline.wiki_output_dir),
            "known_dossiers": known,
            "lint": lint,
        }

    if command == "lint":
        counts = pipeline.lint()
        status = "ok" if counts["dossiers"] > 0 else "degraded"
        if counts["missing_vap"] > 0 or counts["missing_provenance"] > 0:
            status = "degraded"
        code = 0 if status == "ok" else 2
        return code, {
            "status": status,
            "command": "intel lint",
            "wiki_output_dir": str(pipeline.wiki_output_dir),
            "dossiers": counts["dossiers"],
            "missing_vap": counts["missing_vap"],
            "missing_canonical_ref": counts["missing_canonical_ref"],
            "missing_provenance": counts["missing_provenance"],
        }

    if command == "ingest-claims":
        try:
            claims_data = _load_json_file(args.input_file)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            return 2, {"status": "blocked", "error": f"input parse failed: {exc}"}
        if not isinstance(claims_data, list):
            return 2, {"status": "blocked", "error": "input JSON must be an array of claim objects"}
        dossiers = pipeline.ingest_evidence_claims(claims_data)
        written = pipeline.write_dossiers(dossiers, overwrite=args.overwrite)
        return 0, {
            "status": "ok",
            "command": "intel ingest-claims",
            "claims_ingested": len(claims_data),
            "dossiers_generated": len(dossiers),
            "dossiers_written": len(written),
            "written_paths": [str(p) for p in written],
        }

    if command == "ingest-synthesis":
        try:
            synthesis_data = _load_json_file(args.input_file)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            return 2, {"status": "blocked", "error": f"input parse failed: {exc}"}
        if not isinstance(synthesis_data, dict):
            return 2, {"status": "blocked", "error": "input JSON must be a synthesis object with 'findings'"}
        dossiers = pipeline.ingest_research_synthesis(synthesis_data)
        if not dossiers:
            return 2, {"status": "degraded", "error": "no findings in synthesis payload"}
        written = pipeline.write_dossiers(dossiers, overwrite=args.overwrite)
        return 0, {
            "status": "ok",
            "command": "intel ingest-synthesis",
            "findings_count": len(synthesis_data.get("findings", [])),
            "dossiers_generated": len(dossiers),
            "dossiers_written": len(written),
            "written_paths": [str(p) for p in written],
        }

    return 2, {"status": "blocked", "error": f"unknown intel command: {command}"}
