#!/usr/bin/env python3
"""Allocate / write / append NEXUSbuildubuntuGROK45logs-NN.txt under the NEXUSlogs vault.

Hard rule: NEXUSLOGS-GB-001 (docs/policies/NEXUSLOGS_GROK45_LOGGING.md).

- Full conversation content only (never thin summaries).
- Soft max ~1500 / hard max ~3000 lines are ROTATION ceilings only.
- Prefer --append into the latest part until hard max; do not open a new NN every short note.
- Prefer Grok /export (often /home/speci/<name>) then --install-export into the vault.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_VAULT = Path(r"C:\Users\speci.000\Downloads\NEXUSlogs")
WSL_VAULT = Path("/mnt/c/Users/speci.000/Downloads/NEXUSlogs")
PREFIX = "NEXUSbuildubuntuGROK45logs-"
PATTERN = re.compile(r"^NEXUSbuildubuntuGROK45logs-(\d+)\.txt$")
SOFT_MAX = 1500
HARD_MAX = 3000


def vault_path() -> Path:
    if WSL_VAULT.is_dir():
        return WSL_VAULT
    return DEFAULT_VAULT


def part_path(vault: Path, index: int) -> Path:
    return vault / f"{PREFIX}{index:02d}.txt"


def list_parts(vault: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    for p in vault.glob(f"{PREFIX}*.txt"):
        m = PATTERN.match(p.name)
        if m:
            found.append((int(m.group(1)), p))
    found.sort(key=lambda t: t[0])
    return found


def next_index(vault: Path) -> int:
    parts = list_parts(vault)
    if not parts:
        return 1
    return parts[-1][0] + 1


def latest_part(vault: Path) -> tuple[int, Path] | None:
    parts = list_parts(vault)
    return parts[-1] if parts else None


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def file_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return count_lines(path.read_text(encoding="utf-8", errors="replace"))


def maybe_header(dest: Path, source: str | Path | None, body: str) -> str:
    if body.lstrip().startswith("====") or "NEXUS LOG" in body[:400]:
        return body if body.endswith("\n") else body + "\n"
    header = (
        f"{'=' * 80}\n"
        f"NEXUS LOG — {dest.name}\n"
        f"Installed_from: {source or 'stdin'}\n"
        f"Installed_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"Policy: NEXUSLOGS-GB-001 (full conversation content; rotation only at 1.5k–3k lines)\n"
        f"{'=' * 80}\n\n"
    )
    body = header + body
    return body if body.endswith("\n") else body + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", type=Path, default=None)
    ap.add_argument("--status", action="store_true", help="Print vault status and exit")
    ap.add_argument(
        "--write",
        type=Path,
        help="Write draft/export into a NEW next log part (full text, not a summary)",
    )
    ap.add_argument(
        "--install-export",
        type=Path,
        dest="write",
        help="Alias for --write; use for Grok /export files (often /home/speci/<name>)",
    )
    ap.add_argument(
        "--append",
        type=Path,
        help="Append full text into the latest part if under hard max; else new part",
    )
    ap.add_argument("--stdin", action="store_true", help="Read draft from stdin (with --write/--append semantics via flags)")
    ap.add_argument(
        "--force-index",
        type=int,
        default=None,
        help="Write specific index (must not exist unless --overwrite)",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replace of an existing part (use when reinstalling a full /export)",
    )
    args = ap.parse_args(argv)

    vault = args.vault or vault_path()
    vault.mkdir(parents=True, exist_ok=True)

    if args.status:
        parts = list_parts(vault)
        print(f"vault={vault}")
        print(f"soft_max_lines={SOFT_MAX}")
        print(f"hard_max_lines={HARD_MAX}")
        if not parts:
            print("parts=(none)")
            print(f"next_index=01")
            print(f"next_path={part_path(vault, 1)}")
            return 0
        for idx, p in parts:
            print(f"part={idx:02d} path={p} lines={file_line_count(p)}")
        last_idx, last_path = parts[-1]
        last_lines = file_line_count(last_path)
        print(f"latest_index={last_idx:02d}")
        print(f"latest_lines={last_lines}")
        if last_lines >= HARD_MAX:
            n = last_idx + 1
            print(f"recommend=new_part index={n:02d} reason=hard_max")
        elif last_lines >= SOFT_MAX:
            print(f"recommend=prefer_new_part_or_finish_section soft_max_reached")
        else:
            print(f"recommend=append_to_latest remaining_to_soft={SOFT_MAX - last_lines}")
        print(f"next_free_index={next_index(vault):02d}")
        return 0

    if args.append is not None or (args.stdin and args.append is None and args.write is None and False):
        pass  # handled below

    mode_append = args.append is not None
    mode_write = args.write is not None or (args.stdin and not mode_append)

    # Allow: --append - with --stdin, or --append PATH
    if args.stdin and args.append is None and args.write is None:
        # default stdin to append-if-possible
        mode_append = True

    if not mode_append and not mode_write and not args.stdin:
        ap.error("provide --status, --write PATH, --install-export PATH, --append PATH, or --stdin")

    if args.stdin:
        draft = sys.stdin.read()
        source: str | Path | None = "stdin"
    elif mode_append:
        draft = args.append.read_text(encoding="utf-8", errors="replace")
        source = args.append
    else:
        draft = args.write.read_text(encoding="utf-8", errors="replace")
        source = args.write

    draft_lines = count_lines(draft)

    if mode_append and args.force_index is None:
        latest = latest_part(vault)
        if latest is None:
            idx = 1
            dest = part_path(vault, idx)
            body = maybe_header(dest, source, draft)
            dest.write_text(body, encoding="utf-8")
            n = file_line_count(dest)
            print(f"wrote {dest} lines={n} mode=append_new")
            return 0

        idx, dest = latest
        existing_lines = file_line_count(dest)
        if existing_lines >= HARD_MAX:
            idx = idx + 1
            dest = part_path(vault, idx)
            body = maybe_header(dest, source, draft)
            dest.write_text(body, encoding="utf-8")
            n = file_line_count(dest)
            print(f"wrote {dest} lines={n} mode=append_rotated_hard_max")
            return 0

        if existing_lines + draft_lines > HARD_MAX and existing_lines > 0:
            # rotate rather than exceed hard max mid-append of a large chunk
            footer = (
                f"\n=== END PART {idx:02d} — CONTINUE IN PART {idx + 1:02d} "
                f"(hard max {HARD_MAX}) ===\n"
            )
            with dest.open("a", encoding="utf-8") as fh:
                fh.write(footer)
            idx = idx + 1
            dest = part_path(vault, idx)
            bridge = ""
            prev = part_path(vault, idx - 1)
            if prev.exists():
                prev_lines = prev.read_text(encoding="utf-8", errors="replace").splitlines()
                bridge_lines = prev_lines[-15:]
                bridge = (
                    f"=== CONTINUATION of NEXUSbuildubuntuGROK45logs-{idx - 1:02d} ===\n"
                    + "\n".join(bridge_lines)
                    + "\n\n"
                )
            body = maybe_header(dest, source, bridge + draft)
            dest.write_text(body, encoding="utf-8")
            n = file_line_count(dest)
            print(f"wrote {dest} lines={n} mode=append_rotated_chunk")
            return 0

        chunk = draft if draft.endswith("\n") else draft + "\n"
        if not chunk.startswith("\n"):
            # separate appended blocks slightly
            sep = (
                f"\n--- append {datetime.now(timezone.utc).isoformat()} "
                f"from {source} ---\n\n"
            )
        else:
            sep = f"\n--- append {datetime.now(timezone.utc).isoformat()} from {source} ---\n"
        with dest.open("a", encoding="utf-8") as fh:
            fh.write(sep)
            fh.write(chunk)
        n = file_line_count(dest)
        print(f"appended {dest} lines={n} mode=append_same_part")
        if n >= SOFT_MAX:
            print(
                f"NOTE: part has {n} lines (soft max {SOFT_MAX}). "
                "Finish section cleanly; next large dump may open a new part.",
                file=sys.stderr,
            )
        return 0

    # --write / --install-export path (new part or forced index)
    if draft_lines > HARD_MAX:
        print(
            f"ERROR: draft has {draft_lines} lines > hard max {HARD_MAX}. "
            "Split into multiple parts before writing, or raise policy with operator.",
            file=sys.stderr,
        )
        return 2
    if draft_lines > SOFT_MAX:
        print(
            f"WARNING: draft has {draft_lines} lines > soft max {SOFT_MAX}. "
            "Allowed (full /export). Prefer next part for further turns.",
            file=sys.stderr,
        )

    idx = args.force_index if args.force_index is not None else next_index(vault)
    dest = part_path(vault, idx)
    if dest.exists() and not args.overwrite:
        print(f"ERROR: refuses overwrite of existing {dest}", file=sys.stderr)
        return 3

    body = maybe_header(dest, source, draft)
    dest.write_text(body, encoding="utf-8")
    n = file_line_count(dest)
    print(f"wrote {dest} lines={n} mode=write")
    if n > SOFT_MAX:
        print(
            f"NOTE: part has {n} lines (soft max {SOFT_MAX}). "
            "Prefer appending further turns only until hard max, then next index.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
