"""Read-only Kilo snapshot forensic inventory and live NEXUS comparison.

The tool treats the Kilo snapshot as evidence. It does not restore files, delete
files, mutate Git state, or print file contents. Sensitive-looking path names
are redacted by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SNAPSHOT_ROOT = Path(
    r"D:\NEXUS_COLD\level6_quarantine_20260608\Users_speci.000_.local_share_kilo_snapshot"
)
DEFAULT_REPO_ROOT = Path(r"C:\Users\speci.000\Documents\NEXUS")
DEFAULT_MAX_COMPARE_BYTES = 50 * 1024 * 1024
DEFAULT_FOCUS_PREFIXES = (
    "benchmarks",
    "datasets",
    "models",
    "src",
    "nexus_os",
    "research",
    "docs",
    ".agents",
    "tests",
    "tasks",
    "evidence",
    "logs",
    "upload",
)
SENSITIVE_PATH_RE = re.compile(
    r"(^|[/\\._-])("
    r"env|secret|secrets|token|tokens|jwt|credential|credentials|key|keys|"
    r"auth|oauth|pem|pgp|vault|session|cookie|cookies|grok|devin|gemini"
    r")($|[/\\._-])",
    re.IGNORECASE,
)
GENERATED_PATH_RE = re.compile(
    r"(^|/)(node_modules|\.next|dist|build|__pycache__|\.pytest_cache|"
    r"unsloth_compiled_cache|hf_cache|bouncer_checkpoints|bouncer_checkpoints_v3|"
    r"rp_benchmark_results|thermo_sweep_results|v7_lab_output)($|/)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class IndexEntry:
    mode: str
    blob: str
    stage: str
    path: str
    blob_size: int | None = None


def bytes_to_gib(value: int) -> float:
    return round(value / (1024**3), 3)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_rel_path(path: str, redact_sensitive: bool = True) -> str:
    normalized = path.replace("\\", "/")
    if redact_sensitive and SENSITIVE_PATH_RE.search(normalized):
        return f"<redacted-sensitive-path:{Path(normalized).suffix or 'no-ext'}>"
    return normalized


def is_safe_repo_relative(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        return False
    return ".." not in Path(normalized).parts


def run_git(args: list[str], cwd: Path | None = None, input_text: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=120,
    )


def run_git_bytes(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        check=False,
        env=env,
        timeout=120,
    )


def find_git_dirs(snapshot_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for config in snapshot_root.rglob("config"):
        git_dir = config.parent
        if (git_dir / "objects").exists() and (git_dir / "index").exists():
            candidates.append(git_dir)
    return sorted(candidates, key=lambda p: len(str(p)))


def git_config(git_dir: Path) -> dict[str, str]:
    proc = run_git(["--git-dir", str(git_dir), "config", "--list"])
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()}
    config: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key.startswith("credential.") or "email" in key.lower():
                config[key] = "<redacted>"
            else:
                config[key] = value
    return config


def parse_ls_files(git_dir: Path) -> list[IndexEntry]:
    proc = run_git_bytes(["--git-dir", str(git_dir), "ls-files", "-s", "-z"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace").strip())
    entries: list[IndexEntry] = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        meta, path = raw.split(b"\t", 1)
        mode, blob, stage = meta.decode("ascii").split(" ")
        entries.append(IndexEntry(mode=mode, blob=blob, stage=stage, path=path.decode("utf-8", errors="replace")))
    return entries


def batch_blob_sizes(git_dir: Path, blobs: Iterable[str]) -> dict[str, int]:
    unique = sorted(set(blobs))
    if not unique:
        return {}
    proc = run_git(
        ["--git-dir", str(git_dir), "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
        input_text="\n".join(unique) + "\n",
    )
    if proc.returncode != 0:
        return {}
    sizes: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        parts = line.split(" ")
        if len(parts) == 3 and parts[1] == "blob":
            sizes[parts[0]] = int(parts[2])
    return sizes


def snapshot_file_inventory(snapshot_root: Path, top_limit: int = 25) -> dict[str, Any]:
    totals = {"files": 0, "bytes": 0}
    categories: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    top_files: list[dict[str, Any]] = []

    for item in snapshot_root.rglob("*"):
        if not item.is_file():
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        rel = item.relative_to(snapshot_root).as_posix()
        category = classify_snapshot_file(rel)
        totals["files"] += 1
        totals["bytes"] += stat.st_size
        categories[category]["files"] += 1
        categories[category]["bytes"] += stat.st_size
        top_files.append(
            {
                "path": safe_rel_path(rel),
                "bytes": stat.st_size,
                "gib": bytes_to_gib(stat.st_size),
                "last_write": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "category": category,
            }
        )

    top_files.sort(key=lambda row: row["bytes"], reverse=True)
    return {
        "totals": {"files": totals["files"], "bytes": totals["bytes"], "gib": bytes_to_gib(totals["bytes"])},
        "categories": {
            key: {"files": value["files"], "bytes": value["bytes"], "gib": bytes_to_gib(value["bytes"])}
            for key, value in sorted(categories.items())
        },
        "top_files": top_files[:top_limit],
    }


def classify_snapshot_file(rel_path: str) -> str:
    name = Path(rel_path).name
    normalized = rel_path.replace("\\", "/")
    if "/objects/pack/tmp_pack_" in normalized or name.startswith("tmp_pack_"):
        return "git_tmp_pack_garbage"
    if normalized.endswith(".pack") and "/objects/pack/" in normalized:
        return "git_pack"
    if normalized.endswith(".idx") and "/objects/pack/" in normalized:
        return "git_pack_index"
    if "/lfs/objects/" in normalized:
        return "git_lfs_object"
    if re.search(r"/objects/[0-9a-f]{2}/[0-9a-f]{38}$", normalized, re.IGNORECASE):
        return "git_loose_object"
    if any(part in normalized for part in ["/hooks/", "/info/", "/refs/"]):
        return "git_metadata"
    return "other_snapshot_file"


def classify_project_path(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    prefix = normalized.split("/", 1)[0]
    suffix = Path(normalized).suffix.lower()

    if SENSITIVE_PATH_RE.search(normalized):
        return "sensitive_path"
    if GENERATED_PATH_RE.search(normalized):
        return "generated_or_cache"
    if prefix in {"nexus_os", "src", "upload"} or suffix in {".py", ".ts", ".tsx", ".js", ".mjs", ".ps1", ".sh"}:
        return "source_or_script"
    if prefix in {"docs", "research"} or suffix in {".md", ".txt", ".rst"}:
        return "docs_or_research"
    if prefix in {"datasets", "benchmarks"} or suffix in {".json", ".jsonl", ".csv", ".yaml", ".yml"}:
        return "data_or_benchmark"
    if prefix == "models" or suffix in {".gguf", ".safetensors", ".bin", ".pt", ".pth"}:
        return "model_or_weight"
    if prefix in {"logs", "evidence"} or suffix in {".log"}:
        return "logs_or_evidence"
    if prefix in {"backups", "nexus_os_backup_untracked", "nexus_os_shadow_backup", "nexus_os_untracked_backup"}:
        return "backup_or_shadow"
    if prefix in {".agents", ".devin", ".gemini", ".grok", ".pi", ".session", ".vscode", ".playwright-mcp"}:
        return "agent_or_local_state"
    return "other"


def recovery_priority(kind: str, relation: str, rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    if kind == "sensitive_path":
        return "P0_sensitive_hold"
    if relation == "missing_live":
        if kind == "source_or_script":
            return "P0_missing_code_review"
        if kind == "docs_or_research":
            return "P1_missing_docs_review"
        if kind == "data_or_benchmark":
            return "P1_missing_data_review"
        return "P2_missing_low_signal"
    if relation == "different_index":
        if normalized.startswith(("nexus_os/", "src/", "scripts/", "tests/")):
            return "P1_diff_code_review"
        if kind in {"docs_or_research", "data_or_benchmark"}:
            return "P2_diff_evidence_review"
        return "P3_diff_low_signal"
    if relation == "not_tracked_current_index":
        if kind in {"docs_or_research", "source_or_script", "data_or_benchmark"}:
            return "P2_untracked_intake_review"
        if kind in {"model_or_weight", "backup_or_shadow", "logs_or_evidence"}:
            return "P3_untracked_preserve_or_ignore"
        return "P4_untracked_low_signal"
    return "P4_low_signal"


def classify_entries(
    entries: list[IndexEntry],
    repo_root: Path,
    redact_sensitive: bool = True,
    list_limit: int = 200,
) -> dict[str, Any]:
    live_index = repo_index_entries(repo_root)
    summary: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    by_priority: Counter[str] = Counter()
    by_relation_kind: Counter[str] = Counter()
    high_value: list[dict[str, Any]] = []

    for entry in entries:
        rel_path = entry.path.replace("\\", "/")
        sensitive = bool(SENSITIVE_PATH_RE.search(rel_path))
        kind = classify_project_path(rel_path)
        live_path = repo_root / rel_path
        if not is_safe_repo_relative(rel_path):
            relation = "unsafe_path"
        elif not live_path.exists():
            relation = "missing_live"
        elif not live_path.is_file():
            relation = "live_not_file"
        elif rel_path not in live_index:
            relation = "not_tracked_current_index"
        elif live_index[rel_path].blob != entry.blob:
            relation = "different_index"
        else:
            relation = "same_index"

        priority = recovery_priority(kind, relation, rel_path)
        summary[relation] += 1
        by_kind[kind] += 1
        by_priority[priority] += 1
        by_relation_kind[f"{relation}:{kind}"] += 1

        if priority.startswith(("P0", "P1", "P2")) and len(high_value) < list_limit:
            high_value.append(
                {
                    "path": safe_rel_path(rel_path, redact_sensitive=redact_sensitive),
                    "prefix": rel_path.split("/", 1)[0],
                    "kind": kind,
                    "relation": relation,
                    "priority": priority,
                    "blob_size": entry.blob_size,
                    "snapshot_blob": entry.blob,
                    "sensitive_path_redacted": sensitive and redact_sensitive,
                }
            )

    return {
        "summary": dict(summary),
        "by_kind": dict(by_kind),
        "by_priority": dict(by_priority),
        "by_relation_kind": dict(by_relation_kind),
        "high_value_candidates": high_value,
        "limits": {"list_limit": list_limit, "redact_sensitive": redact_sensitive},
    }


def index_path_summary(entries: list[IndexEntry], redact_sensitive: bool = True) -> dict[str, Any]:
    top_prefixes: Counter[str] = Counter()
    top_extensions: Counter[str] = Counter()
    sensitive_counts: Counter[str] = Counter()
    examples: list[str] = []

    for entry in entries:
        normalized = entry.path.replace("\\", "/")
        prefix = normalized.split("/", 1)[0]
        top_prefixes[prefix] += 1
        suffix = Path(normalized).suffix.lower() or "<no-ext>"
        top_extensions[suffix] += 1
        if SENSITIVE_PATH_RE.search(normalized):
            sensitive_counts[prefix] += 1
        elif len(examples) < 25:
            examples.append(safe_rel_path(normalized, redact_sensitive=redact_sensitive))

    return {
        "tracked_file_count": len(entries),
        "top_prefixes": dict(top_prefixes.most_common(25)),
        "top_extensions": dict(top_extensions.most_common(25)),
        "sensitive_path_count": sum(sensitive_counts.values()),
        "sensitive_prefix_counts": dict(sensitive_counts.most_common(25)),
        "safe_examples": examples,
    }


def hash_live_file(repo_root: Path, rel_path: str) -> str | None:
    proc = run_git(["hash-object", "--path", rel_path, "--", rel_path], cwd=repo_root)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def hash_live_file_raw(repo_root: Path, rel_path: str) -> str | None:
    proc = run_git(["hash-object", "--no-filters", "--", rel_path], cwd=repo_root)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def cat_blob(git_dir: Path, blob: str) -> bytes:
    proc = run_git_bytes(["--git-dir", str(git_dir), "cat-file", "blob", blob])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode(errors="replace").strip())
    return proc.stdout


def repo_index_entries(repo_root: Path) -> dict[str, IndexEntry]:
    proc = run_git_bytes(["ls-files", "-s", "-z"], cwd=repo_root)
    if proc.returncode != 0:
        return {}
    entries: dict[str, IndexEntry] = {}
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        meta, path = raw.split(b"\t", 1)
        mode, blob, stage = meta.decode("ascii").split(" ")
        rel_path = path.decode("utf-8", errors="replace").replace("\\", "/")
        entries[rel_path] = IndexEntry(mode=mode, blob=blob, stage=stage, path=rel_path)
    return entries


def compare_snapshot_to_repo_index(
    entries: list[IndexEntry],
    repo_root: Path,
    redact_sensitive: bool = True,
    list_limit: int = 200,
) -> dict[str, Any]:
    live_index = repo_index_entries(repo_root)
    counters: Counter[str] = Counter()
    different: list[dict[str, Any]] = []
    not_tracked: list[dict[str, Any]] = []

    for entry in entries:
        rel_path = entry.path.replace("\\", "/")
        display_path = safe_rel_path(rel_path, redact_sensitive=redact_sensitive)
        sensitive = bool(SENSITIVE_PATH_RE.search(rel_path))
        live_entry = live_index.get(rel_path)
        row = {
            "path": display_path,
            "sensitive_path_redacted": sensitive and redact_sensitive,
            "snapshot_blob": entry.blob,
            "snapshot_blob_size": entry.blob_size,
        }
        if live_entry is None:
            counters["not_tracked_in_current_index"] += 1
            if len(not_tracked) < list_limit:
                not_tracked.append(row)
            continue
        if live_entry.blob == entry.blob:
            counters["same_as_current_index"] += 1
        else:
            counters["different_from_current_index"] += 1
            if len(different) < list_limit:
                different.append({**row, "current_index_blob": live_entry.blob})

    return {
        "summary": dict(counters),
        "different_candidates": different,
        "not_tracked_candidates": not_tracked,
        "limits": {"list_limit": list_limit, "redact_sensitive": redact_sensitive},
    }


def compare_snapshot_to_repo(
    entries: list[IndexEntry],
    repo_root: Path,
    max_compare_bytes: int,
    redact_sensitive: bool = True,
    list_limit: int = 200,
    hash_working_tree: bool = False,
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    missing: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    metadata_only: list[dict[str, Any]] = []
    unsafe_paths: list[dict[str, Any]] = []

    for entry in entries:
        rel_path = entry.path.replace("\\", "/")
        display_path = safe_rel_path(rel_path, redact_sensitive=redact_sensitive)
        sensitive = bool(SENSITIVE_PATH_RE.search(rel_path))

        if not is_safe_repo_relative(rel_path):
            counters["unsafe_relative_path"] += 1
            if len(unsafe_paths) < list_limit:
                unsafe_paths.append({"path": display_path, "blob": entry.blob, "reason": "unsafe_relative_path"})
            continue

        live_path = repo_root / rel_path
        row = {
            "path": display_path,
            "sensitive_path_redacted": sensitive and redact_sensitive,
            "snapshot_blob": entry.blob,
            "snapshot_blob_size": entry.blob_size,
        }

        if not live_path.exists():
            counters["missing_in_live_repo"] += 1
            if len(missing) < list_limit:
                missing.append({**row, "recovery": "candidate_individual_git_show_restore"})
            continue

        if not live_path.is_file():
            counters["live_path_not_file"] += 1
            continue

        try:
            live_size = live_path.stat().st_size
        except OSError:
            counters["live_stat_error"] += 1
            continue

        row["live_size"] = live_size
        if not hash_working_tree:
            counters["live_file_present_unhashed"] += 1
            continue

        blob_size = entry.blob_size if entry.blob_size is not None else max_compare_bytes + 1
        if blob_size > max_compare_bytes or live_size > max_compare_bytes:
            counters["metadata_only_large_file"] += 1
            if len(metadata_only) < list_limit:
                metadata_only.append(row)
            continue

        live_blob = hash_live_file(repo_root, rel_path)
        if live_blob is None:
            counters["live_hash_error"] += 1
            continue
        if live_blob == entry.blob:
            counters["same_blob"] += 1
        else:
            counters["different_blob"] += 1
            if len(changed) < list_limit:
                changed.append({**row, "live_blob": live_blob, "recovery": "candidate_diff_review"})

    return {
        "summary": dict(counters),
        "missing_candidates": missing,
        "changed_candidates": changed,
        "metadata_only_large_files": metadata_only,
        "unsafe_paths": unsafe_paths,
        "limits": {
            "list_limit": list_limit,
            "max_compare_bytes": max_compare_bytes,
            "redact_sensitive": redact_sensitive,
            "hash_working_tree": hash_working_tree,
        },
    }


def byte_compare_focus(
    entries: list[IndexEntry],
    repo_root: Path,
    prefixes: Iterable[str],
    redact_sensitive: bool = True,
    list_limit: int = 5000,
) -> dict[str, Any]:
    focus_prefixes = tuple(prefixes)
    live_index = repo_index_entries(repo_root)
    rows: list[dict[str, Any]] = []
    summary: Counter[str] = Counter()
    by_prefix: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    by_priority: Counter[str] = Counter()
    by_relation_kind: Counter[str] = Counter()

    for entry in entries:
        rel_path = entry.path.replace("\\", "/")
        prefix = rel_path.split("/", 1)[0]
        if prefix not in focus_prefixes:
            continue

        kind = classify_project_path(rel_path)
        live_path = repo_root / rel_path
        sensitive = bool(SENSITIVE_PATH_RE.search(rel_path))
        current_index = live_index.get(rel_path)
        current_index_blob = current_index.blob if current_index else None
        live_blob = None
        live_bytes = None
        byte_relation = "unknown"
        tracked_relation = "not_tracked_current_index" if current_index is None else (
            "same_as_current_index" if current_index.blob == entry.blob else "different_from_current_index"
        )

        if not is_safe_repo_relative(rel_path):
            byte_relation = "unsafe_path"
        elif not live_path.exists():
            byte_relation = "missing_live"
        elif not live_path.is_file():
            byte_relation = "live_not_file"
        else:
            try:
                live_bytes = live_path.stat().st_size
            except OSError:
                live_bytes = None
            live_blob = hash_live_file(repo_root, rel_path)
            if live_blob is None:
                byte_relation = "live_hash_error"
            elif live_blob == entry.blob:
                byte_relation = "byte_identical_to_snapshot"
            elif current_index_blob and live_blob == current_index_blob:
                byte_relation = "live_matches_current_index_not_snapshot"
            elif current_index_blob:
                byte_relation = "live_differs_from_snapshot_and_index"
            else:
                byte_relation = "live_differs_from_snapshot_untracked"

        priority_relation = tracked_relation
        if byte_relation == "missing_live":
            priority_relation = "missing_live"
        elif byte_relation == "live_differs_from_snapshot_and_index":
            priority_relation = "different_index"
        priority = recovery_priority(kind, priority_relation, rel_path)
        summary[byte_relation] += 1
        by_prefix[prefix] += 1
        by_kind[kind] += 1
        by_priority[priority] += 1
        by_relation_kind[f"{byte_relation}:{kind}"] += 1

        if len(rows) < list_limit:
            rows.append(
                {
                    "path": safe_rel_path(rel_path, redact_sensitive=redact_sensitive),
                    "prefix": prefix,
                    "kind": kind,
                    "priority": priority,
                    "byte_relation": byte_relation,
                    "tracked_relation": tracked_relation,
                    "snapshot_blob": entry.blob,
                    "snapshot_blob_size": entry.blob_size,
                    "live_blob": live_blob,
                    "live_bytes": live_bytes,
                    "current_index_blob": current_index_blob,
                    "sensitive_path_redacted": sensitive and redact_sensitive,
                }
            )

    return {
        "focus_prefixes": list(focus_prefixes),
        "summary": dict(summary),
        "by_prefix": dict(by_prefix),
        "by_kind": dict(by_kind),
        "by_priority": dict(by_priority),
        "by_relation_kind": dict(by_relation_kind),
        "rows": rows,
        "limits": {"list_limit": list_limit, "redact_sensitive": redact_sensitive},
    }


def extract_missing_review_blobs(
    entries: list[IndexEntry],
    git_dir: Path,
    repo_root: Path,
    review_dir: Path,
    prefixes: Iterable[str],
    redact_sensitive: bool = True,
) -> dict[str, Any]:
    review_dir = review_dir.resolve()
    repo_root = repo_root.resolve()
    try:
        review_dir.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"Review extraction dir must stay inside repo root: {review_dir}") from exc

    focus_prefixes = tuple(prefixes)
    file_root = review_dir / "files"
    file_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for entry in entries:
        rel_path = entry.path.replace("\\", "/")
        prefix = rel_path.split("/", 1)[0]
        if prefix not in focus_prefixes:
            continue
        if not is_safe_repo_relative(rel_path):
            skipped.append({"path": safe_rel_path(rel_path, redact_sensitive=redact_sensitive), "reason": "unsafe_path"})
            continue
        if (repo_root / rel_path).exists():
            continue

        blob_bytes = cat_blob(git_dir, entry.blob)
        out_path = file_root / rel_path
        resolved_out = out_path.resolve()
        try:
            resolved_out.relative_to(file_root.resolve())
        except ValueError as exc:
            raise ValueError(f"Refusing extraction outside review file root: {resolved_out}") from exc
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(blob_bytes)
        rows.append(
            {
                "snapshot_path": rel_path,
                "display_path": safe_rel_path(rel_path, redact_sensitive=redact_sensitive),
                "extracted_path": out_path.relative_to(repo_root).as_posix(),
                "prefix": prefix,
                "kind": classify_project_path(rel_path),
                "priority": recovery_priority(classify_project_path(rel_path), "missing_live", rel_path),
                "snapshot_blob": entry.blob,
                "snapshot_blob_size": entry.blob_size,
                "extracted_bytes": len(blob_bytes),
                "content_sha256": hashlib.sha256(blob_bytes).hexdigest(),
                "sensitive_path_redacted": bool(SENSITIVE_PATH_RE.search(rel_path)) and redact_sensitive,
            }
        )

    manifest = {
        "generated_at": now_utc_iso(),
        "mode": "review_extract_no_live_restore",
        "review_dir": str(review_dir),
        "file_root": str(file_root),
        "focus_prefixes": list(focus_prefixes),
        "files_extracted": len(rows),
        "rows": rows,
        "skipped": skipped,
        "safety": {
            "live_paths_modified": False,
            "restored_into_repo_paths": False,
            "contents_printed": False,
        },
    }
    (review_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (review_dir / "README.md").write_text(
        "# Kilo Missing Blob Review\n\n"
        "This folder contains review-only extracted blobs from the Kilo snapshot. "
        "They were not restored into live source paths. Review and port manually.\n",
        encoding="utf-8",
    )
    return {key: value for key, value in manifest.items() if key != "rows"} | {"rows": rows}


def analyze(
    snapshot_root: Path,
    repo_root: Path,
    max_compare_bytes: int = DEFAULT_MAX_COMPARE_BYTES,
    redact_sensitive: bool = True,
    hash_working_tree: bool = False,
    candidate_limit: int = 200,
    byte_compare_prefixes: Iterable[str] | None = None,
    extract_missing_review_dir: Path | None = None,
) -> dict[str, Any]:
    snapshot_root = snapshot_root.resolve()
    repo_root = repo_root.resolve()
    if not snapshot_root.exists():
        raise FileNotFoundError(f"Snapshot root not found: {snapshot_root}")
    if not repo_root.exists():
        raise FileNotFoundError(f"Repo root not found: {repo_root}")

    git_dirs = find_git_dirs(snapshot_root)
    selected_git_dir: Path | None = None
    entries: list[IndexEntry] = []
    git_dir_summaries: list[dict[str, Any]] = []
    for git_dir in git_dirs:
        try:
            candidate_entries = parse_ls_files(git_dir)
        except RuntimeError as exc:
            git_dir_summaries.append({"git_dir": str(git_dir), "error": str(exc), "tracked_file_count": 0})
            continue
        git_dir_summaries.append({"git_dir": str(git_dir), "tracked_file_count": len(candidate_entries)})
        if len(candidate_entries) > len(entries):
            selected_git_dir = git_dir
            entries = candidate_entries

    if selected_git_dir and entries:
        sizes = batch_blob_sizes(selected_git_dir, [entry.blob for entry in entries])
        entries = [
            IndexEntry(
                mode=entry.mode,
                blob=entry.blob,
                stage=entry.stage,
                path=entry.path,
                blob_size=sizes.get(entry.blob),
            )
            for entry in entries
        ]

    report = {
        "generated_at": now_utc_iso(),
        "mode": "review_extract_no_live_restore" if extract_missing_review_dir else "read_only_metadata_no_content_restore",
        "snapshot_root": str(snapshot_root),
        "repo_root": str(repo_root),
        "git_dirs": [str(path) for path in git_dirs],
        "git_dir_summaries": git_dir_summaries,
        "selected_git_dir": str(selected_git_dir) if selected_git_dir else None,
        "selected_git_config": git_config(selected_git_dir) if selected_git_dir else {},
        "file_inventory": snapshot_file_inventory(snapshot_root),
        "index_summary": index_path_summary(entries, redact_sensitive=redact_sensitive) if entries else {},
        "repo_compare": compare_snapshot_to_repo(
            entries,
            repo_root,
            max_compare_bytes=max_compare_bytes,
            redact_sensitive=redact_sensitive,
            list_limit=candidate_limit,
            hash_working_tree=hash_working_tree,
        )
        if entries
        else {},
        "repo_index_compare": compare_snapshot_to_repo_index(
            entries,
            repo_root,
            redact_sensitive=redact_sensitive,
            list_limit=candidate_limit,
        )
        if entries
        else {},
        "recovery_classification": classify_entries(
            entries,
            repo_root,
            redact_sensitive=redact_sensitive,
            list_limit=candidate_limit,
        )
        if entries
        else {},
        "byte_comparison": byte_compare_focus(
            entries,
            repo_root,
            prefixes=byte_compare_prefixes,
            redact_sensitive=redact_sensitive,
            list_limit=candidate_limit,
        )
        if entries and byte_compare_prefixes
        else {},
    }
    if entries and selected_git_dir and byte_compare_prefixes and extract_missing_review_dir:
        report["missing_review_extract"] = extract_missing_review_blobs(
            entries,
            selected_git_dir,
            repo_root,
            extract_missing_review_dir,
            prefixes=byte_compare_prefixes,
            redact_sensitive=redact_sensitive,
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Kilo snapshot forensic inventory")
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--max-compare-mib", type=int, default=50)
    parser.add_argument("--include-sensitive-paths", action="store_true")
    parser.add_argument("--include-working-tree-hash", action="store_true")
    parser.add_argument("--candidate-limit", type=int, default=200)
    parser.add_argument(
        "--byte-compare-high-value",
        action="store_true",
        help="Run Git blob-byte comparison for high-value NEXUS prefixes",
    )
    parser.add_argument("--byte-compare-prefix", action="append", default=[])
    parser.add_argument("--extract-missing-review-dir", type=Path)
    args = parser.parse_args(argv)

    report = analyze(
        snapshot_root=args.snapshot_root,
        repo_root=args.repo_root,
        max_compare_bytes=args.max_compare_mib * 1024 * 1024,
        redact_sensitive=not args.include_sensitive_paths,
        hash_working_tree=args.include_working_tree_hash,
        candidate_limit=args.candidate_limit,
        byte_compare_prefixes=(
            args.byte_compare_prefix
            or (DEFAULT_FOCUS_PREFIXES if args.byte_compare_high_value else None)
        ),
        extract_missing_review_dir=args.extract_missing_review_dir,
    )
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
