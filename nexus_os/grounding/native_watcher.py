"""Native filesystem watcher with debounce, tombstones, and reconciliation."""

from __future__ import annotations

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .service import GroundingService


def watch_grounding(
    service: GroundingService,
    *,
    debounce_seconds: int = 30,
    reconcile_seconds: int = 3600,
    fallback_poll_seconds: int = 30,
) -> None:
    service.reconcile(stability_delay_seconds=0.0)
    pending: dict[tuple[str, str], tuple[float, str]] = {}

    class Handler(FileSystemEventHandler):
        def __init__(self, source_id: str) -> None:
            self.source_id = source_id

        def queue(self, path: str, operation: str) -> None:
            pending[(self.source_id, str(path))] = (time.monotonic(), operation)

        def on_created(self, event: object) -> None:
            if not getattr(event, "is_directory", False):
                self.queue(getattr(event, "src_path"), "upsert")

        def on_modified(self, event: object) -> None:
            if not getattr(event, "is_directory", False):
                self.queue(getattr(event, "src_path"), "upsert")

        def on_deleted(self, event: object) -> None:
            if not getattr(event, "is_directory", False):
                self.queue(getattr(event, "src_path"), "delete")

        def on_moved(self, event: object) -> None:
            if not getattr(event, "is_directory", False):
                self.queue(getattr(event, "src_path"), "delete")
                self.queue(getattr(event, "dest_path"), "upsert")

    observer = Observer()
    scheduled = 0
    for source_id, root in service.roots.items():
        if root.exists():
            observer.schedule(Handler(source_id), str(root), recursive=True)
            scheduled += 1
    if not scheduled:
        _poll_fallback(service, fallback_poll_seconds)
        return

    observer.start()
    last_reconcile = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            ready = [
                key for key, (seen_at, _) in pending.items()
                if now - seen_at >= debounce_seconds
            ]
            for source_id, raw_path in ready:
                _, operation = pending.pop((source_id, raw_path))
                if operation == "delete":
                    service.ingest_delete(source_id, Path(raw_path))
                else:
                    service.ingest_path(
                        source_id,
                        Path(raw_path),
                        stability_delay_seconds=0.0,
                    )
            if now - last_reconcile >= reconcile_seconds:
                service.reconcile(stability_delay_seconds=0.0)
                last_reconcile = now
            time.sleep(1)
    finally:
        observer.stop()
        observer.join(timeout=10)


def _poll_fallback(service: GroundingService, poll_seconds: int) -> None:
    while True:
        service.reconcile(stability_delay_seconds=0.0)
        time.sleep(max(1, poll_seconds))
