"""Opt-in, read-only OmniRoute catalogue intelligence.

This module deliberately does *not* import or run OmniRoute.  It reads a local
source snapshot, verifies an exact version/commit/content pin, and emits only
quarantined source-card candidates.  It has no network path, provider
credentials, inference calls, watchlist writes, or registry promotion path.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote


OFFICIAL_OMNIROUTE_REPOSITORY = "https://github.com/diegosouzapw/OmniRoute"
PROVIDER_SOURCE_SUBDIR = Path("src/shared/constants/providers")
DETACHED_MANIFEST_BASENAME = "nexus-omniroute-snapshot.json"

_MAX_SOURCE_FILES = 512
_MAX_SOURCE_FILE_BYTES = 4 * 1024 * 1024
_MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_ENTRY_START_RE = re.compile(
    r"(?m)^  (?P<key>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[A-Za-z0-9_$-]+)"
    r":\s*(?:Object\.freeze\s*\(\s*)?\{"
)
_ID_RE = re.compile(r"\bid\s*:\s*(?P<value>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')")


class OmniRouteCatalogError(ValueError):
    """Base class for fail-closed catalogue adapter errors."""


class AdapterDisabledError(OmniRouteCatalogError):
    """Raised unless an operator explicitly enables this inert adapter."""


class ProvenanceError(OmniRouteCatalogError):
    """Raised when an upstream source pin cannot be proved exactly."""


def _normalise_version(value: str) -> str:
    version = str(value).strip()
    if version.startswith("v"):
        version = version[1:]
    if not _VERSION_RE.fullmatch(version):
        raise ProvenanceError("expected version must be an exact semantic version")
    return version


def _normalise_commit(value: str) -> str:
    commit = str(value).strip().lower()
    if not _COMMIT_RE.fullmatch(commit):
        raise ProvenanceError("expected commit must be a full 40-character SHA-1")
    return commit


def _assert_bounded_source_file(path: Path, root: Path) -> bytes:
    if path.is_symlink():
        raise ProvenanceError(f"symlinked source file rejected: {path.name}")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ProvenanceError("source file escapes the pinned snapshot root")
    size = resolved.stat().st_size
    if size > _MAX_SOURCE_FILE_BYTES:
        raise ProvenanceError(f"source file exceeds size limit: {path.name}")
    return resolved.read_bytes()


def _snapshot_files(root: Path) -> list[Path]:
    package_json = root / "package.json"
    provider_root = root / PROVIDER_SOURCE_SUBDIR
    if not package_json.is_file():
        raise ProvenanceError("pinned snapshot is missing package.json")
    if not provider_root.is_dir() or provider_root.is_symlink():
        raise ProvenanceError("pinned snapshot is missing a real provider source directory")
    files = [package_json, *sorted(provider_root.rglob("*.ts"))]
    if len(files) > _MAX_SOURCE_FILES:
        raise ProvenanceError("pinned snapshot exceeds source-file count limit")
    return files


def _compute_snapshot_sha256(root: Path, files: Iterable[Path]) -> str:
    """Hash canonical relative paths, lengths, and bytes for archive stability."""
    digest = hashlib.sha256()
    total_bytes = 0
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        data = _assert_bounded_source_file(path, root)
        total_bytes += len(data)
        if total_bytes > _MAX_SNAPSHOT_BYTES:
            raise ProvenanceError("pinned snapshot exceeds total size limit")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(str(len(data)).encode("ascii"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def _read_git_head(root: Path) -> str | None:
    """Read a simple clone/worktree HEAD without invoking Git or upstream code."""
    dot_git = root / ".git"
    git_dir = dot_git
    if dot_git.is_file():
        marker = dot_git.read_text(encoding="utf-8", errors="strict").strip()
        if not marker.startswith("gitdir:"):
            return None
        git_dir = (root / marker.split(":", 1)[1].strip()).resolve()
    if not git_dir.is_dir():
        return None
    try:
        head = (git_dir / "HEAD").read_text(encoding="ascii").strip()
    except OSError:
        return None
    if _COMMIT_RE.fullmatch(head.lower()):
        return head.lower()
    if not head.startswith("ref:"):
        return None
    ref_name = head.split(":", 1)[1].strip()
    if ".." in Path(ref_name).parts or Path(ref_name).is_absolute():
        return None
    ref_path = git_dir / Path(ref_name)
    try:
        value = ref_path.read_text(encoding="ascii").strip().lower()
    except OSError:
        value = ""
    if _COMMIT_RE.fullmatch(value):
        return value
    packed_refs = git_dir / "packed-refs"
    try:
        lines = packed_refs.read_text(encoding="ascii").splitlines()
    except OSError:
        return None
    for line in lines:
        if line.startswith(("#", "^")):
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1] == ref_name and _COMMIT_RE.fullmatch(parts[0].lower()):
            return parts[0].lower()
    return None


def _load_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"invalid {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProvenanceError(f"invalid {description}: object required")
    return value


def _verify_provenance(
    root: Path,
    files: list[Path],
    expected_version: str,
    expected_commit: str,
    provenance_manifest: Path | None,
) -> tuple[str, str, str]:
    package = _load_json_object(root / "package.json", "package.json")
    observed_version = _normalise_version(str(package.get("version", "")))
    if observed_version != expected_version:
        raise ProvenanceError(
            f"version mismatch: expected {expected_version}, observed {observed_version}"
        )
    snapshot_sha256 = _compute_snapshot_sha256(root, files)
    git_commit = _read_git_head(root)

    manifest_commit: str | None = None
    if provenance_manifest is not None:
        manifest_path = provenance_manifest.resolve(strict=True)
        manifest = _load_json_object(manifest_path, "detached provenance manifest")
        if manifest.get("repository") != OFFICIAL_OMNIROUTE_REPOSITORY:
            raise ProvenanceError("detached manifest repository mismatch")
        manifest_version = _normalise_version(str(manifest.get("version", "")))
        if manifest_version != expected_version:
            raise ProvenanceError(
                f"version mismatch: expected {expected_version}, manifest has {manifest_version}"
            )
        manifest_commit = _normalise_commit(str(manifest.get("commit", "")))
        if manifest_commit != expected_commit:
            raise ProvenanceError(
                f"commit mismatch: expected {expected_commit}, manifest has {manifest_commit}"
            )
        manifest_hash = str(manifest.get("snapshot_sha256", "")).strip().lower()
        if manifest_hash != snapshot_sha256:
            raise ProvenanceError(
                f"snapshot hash mismatch: expected {manifest_hash}, observed {snapshot_sha256}"
            )

    if git_commit is not None and git_commit != expected_commit:
        raise ProvenanceError(
            f"commit mismatch: expected {expected_commit}, git HEAD is {git_commit}"
        )
    if git_commit is None and manifest_commit is None:
        raise ProvenanceError(
            "commit provenance unavailable: use a Git snapshot or detached manifest"
        )
    verification = (
        "git_head_and_detached_manifest"
        if git_commit is not None and manifest_commit is not None
        else "git_head"
        if git_commit is not None
        else "detached_manifest"
    )
    return snapshot_sha256, verification, observed_version


def _decode_ts_string(literal: str) -> str:
    quote_char = literal[0]
    body = literal[1:-1]
    if quote_char == '"':
        try:
            return str(json.loads(literal))
        except json.JSONDecodeError:
            pass
    escapes = {
        "\\": "\\",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        '"': '"',
        "'": "'",
        "`": "`",
    }
    return re.sub(r"\\(.)", lambda match: escapes.get(match.group(1), match.group(1)), body)


def _extract_string(block: str, field: str) -> str | None:
    pattern = re.compile(
        rf"\b{re.escape(field)}\s*:\s*"
        r"(?P<value>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)",
        re.DOTALL,
    )
    match = pattern.search(block)
    return _decode_ts_string(match.group("value")) if match else None


def _extract_bool(block: str, field: str) -> bool | None:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*(true|false)\b", block)
    if not match:
        return None
    return match.group(1) == "true"


def _extract_string_array(block: str, field: str) -> list[str] | None:
    match = re.search(rf"\b{re.escape(field)}\s*:\s*\[(?P<body>[^\]]*)\]", block, re.DOTALL)
    if not match:
        return None
    values = re.findall(r"\"((?:\\.|[^\"\\])*)\"|'((?:\\.|[^'\\])*)'", match.group("body"))
    decoded = []
    for double_value, single_value in values:
        literal = f'"{double_value}"' if double_value else f"'{single_value}'"
        decoded.append(_decode_ts_string(literal))
    return decoded


def _provider_entries(path: Path, root: Path) -> list[dict[str, Any]]:
    text = _assert_bounded_source_file(path, root).decode("utf-8", errors="strict")
    starts = list(_ENTRY_START_RE.finditer(text))
    records: list[dict[str, Any]] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[start.start() : end]
        id_match = _ID_RE.search(block)
        if not id_match:
            continue
        provider_id = _decode_ts_string(id_match.group("value")).strip()
        if not provider_id or any(ord(char) < 32 for char in provider_id) or "::" in provider_id:
            raise ProvenanceError(f"unsafe provider id in {path.relative_to(root).as_posix()}")
        records.append(
            {
                "provider_id": provider_id,
                "object_key": _decode_ts_string(start.group("key"))
                if start.group("key")[0] in "\"'"
                else start.group("key"),
                "source_file": path.relative_to(root).as_posix(),
                "source_fragment_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                "name": _extract_string(block, "name"),
                "alias": _extract_string(block, "alias"),
                "website": _extract_string(block, "website"),
                "free_note": _extract_string(block, "freeNote"),
                "has_free": _extract_bool(block, "hasFree"),
                "no_auth": _extract_bool(block, "noAuth"),
                "deprecated": _extract_bool(block, "deprecated"),
                "subscription_risk": _extract_bool(block, "subscriptionRisk"),
                "service_kinds": _extract_string_array(block, "serviceKinds"),
            }
        )
    return records


def _claim(value: Any) -> dict[str, Any]:
    return {"value": value, "verification": "unverified_upstream_claim"}


def _source_card(
    record: dict[str, Any], namespace: str, snapshot_sha256: str
) -> dict[str, Any]:
    provider_id = record["provider_id"]
    safe_provider_id = quote(provider_id, safe="@._-/")
    return {
        "admission_class": "source_card_candidate",
        "candidate_id": f"{namespace}::provider::{safe_provider_id}",
        "namespace": namespace,
        "provider_id": provider_id,
        "lifecycle": "quarantined",
        "promotion_allowed": False,
        "snapshot_sha256": snapshot_sha256,
        "observations": {
            "provider_id": {"value": provider_id, "verification": "source_observed"},
            "object_key": {"value": record["object_key"], "verification": "source_observed"},
            "source_file": record["source_file"],
            "source_fragment_sha256": record["source_fragment_sha256"],
        },
        "claims": {
            "name": _claim(record["name"]),
            "alias": _claim(record["alias"]),
            "website": _claim(record["website"]),
            "has_free": _claim(record["has_free"]),
            "free_note": _claim(record["free_note"]),
            "no_auth": _claim(record["no_auth"]),
            "deprecated": _claim(record["deprecated"]),
            "subscription_risk": _claim(record["subscription_risk"]),
            "service_kinds": _claim(record["service_kinds"]),
        },
    }


def build_source_card_bundle(
    source_root: Path,
    expected_version: str,
    expected_commit: str,
    provenance_manifest: Path | None = None,
    *,
    enabled: bool = False,
) -> dict[str, Any]:
    """Build a deterministic, candidate-only bundle from a local source pin."""
    if not enabled:
        raise AdapterDisabledError(
            "OmniRoute catalogue intelligence is disabled by default; explicit enable required"
        )
    version = _normalise_version(expected_version)
    commit = _normalise_commit(expected_commit)
    try:
        root = Path(source_root).resolve(strict=True)
    except OSError as exc:
        raise ProvenanceError(f"pinned snapshot root unavailable: {exc}") from exc
    if not root.is_dir():
        raise ProvenanceError("pinned snapshot root must be a directory")
    files = _snapshot_files(root)
    snapshot_sha256, commit_verification, observed_version = _verify_provenance(
        root, files, version, commit, provenance_manifest
    )

    records: list[dict[str, Any]] = []
    for path in files:
        if path.suffix == ".ts":
            records.extend(_provider_entries(path, root))
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        provider_id = record["provider_id"]
        if provider_id in seen:
            duplicates.add(provider_id)
        seen.add(provider_id)
    if duplicates:
        raise ProvenanceError(
            "duplicate provider ids in pinned snapshot: " + ", ".join(sorted(duplicates))
        )
    if not records:
        raise ProvenanceError("pinned snapshot yielded no provider candidates")

    namespace = f"omniroute/{version}/{commit[:12]}/{snapshot_sha256[:12]}"
    cards = [
        _source_card(record, namespace, snapshot_sha256)
        for record in sorted(records, key=lambda item: item["provider_id"])
    ]
    return {
        "schema_version": 1,
        "kind": "nexus.catalogue_intelligence.source_cards",
        "namespace": namespace,
        "source": {
            "repository": OFFICIAL_OMNIROUTE_REPOSITORY,
            "version": observed_version,
            "commit": commit,
            "commit_verification": commit_verification,
            "snapshot_sha256": snapshot_sha256,
            "source_file_count": len(files),
        },
        "policy": {
            "adapter_enabled_by_default": False,
            "candidate_only": True,
            "network_access": False,
            "provider_traffic": False,
            "registry_auto_promotion": False,
        },
        "summary": {
            "provider_candidate_count": len(cards),
            "upstream_has_free_true_claims": sum(
                1 for card in cards if card["claims"]["has_free"]["value"] is True
            ),
            "claim_verification": "unverified_upstream_claim",
        },
        "source_cards": cards,
    }

