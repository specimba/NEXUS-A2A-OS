"""
NEXUS Wiki Pipeline Integration
Bridges Archivist daemon + DoppelGround to the unified control panel.
- Subscribes to UnifiedStateManager for real-time wiki state
- Provides wiki status, search, and dossier access via Brain API
- Periodic sync with archivist daemon
- GROSS exclusion enforcement (confidential project filter)
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nexus.wiki_pipeline")

WIKI_DIR = Path(__file__).resolve().parent.parent.parent / "nexus_os" / "archivist" / "wiki"
WIKI_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "nexus_os" / "archivist" / "wiki_state.json"
RAW_DIRS = {
    "archivist": Path(r"C:\Users\speci.000\Downloads\ARCHIVIST"),
    "papers": Path(r"C:\Users\speci.000\Downloads\PAPERS"),
    "nexuslogs": Path(r"C:\Users\speci.000\Downloads\NEXUSlogs"),
}
EXCLUDED_TOPICS = {"gross", "gross_mcp", "gross_bridge", "password", "secret", "api_key"}


class WikiPipeline:
    """Bridge between Archivist wiki and NEXUS control systems."""

    SYNC_INTERVAL = 300  # 5 minutes
    MAX_SNIPPET_LENGTH = 500

    def __init__(self, state_manager=None):
        self.sm = state_manager
        self.running = False
        self._wiki_index: Dict[str, Dict] = {}
        self._page_count = 0
        self._dossier_count = 0

    async def start(self):
        if self.running:
            return
        self.running = True
        self._build_index()
        asyncio.create_task(self._sync_loop())
        logger.info(f"Wiki Pipeline started ({self._page_count} pages, {self._dossier_count} dossiers)")

    async def stop(self):
        self.running = False

    def _build_index(self):
        """Build in-memory wiki index from wiki directory"""
        self._wiki_index = {}
        self._page_count = 0
        self._dossier_count = 0

        if not WIKI_DIR.exists():
            logger.warning(f"Wiki directory not found: {WIKI_DIR}")
            return

        for md_file in WIKI_DIR.rglob("*.md"):
            try:
                rel_path = md_file.relative_to(WIKI_DIR)
                slug = str(rel_path.with_suffix("")).replace("\\", "/")

                try:
                    full_text = md_file.read_text(encoding="utf-8", errors="replace")
                    word_count = len(full_text.split())
                    content = full_text[:self.MAX_SNIPPET_LENGTH]
                except Exception as e:
                    logger.debug(f"Failed to read {md_file}: {e}")
                    content = ""
                    word_count = 0

                title = self._extract_title(content) or slug

                # GROSS exclusion — exact segment match, not substring
                slug_parts = slug.lower().replace("/", " ").replace("-", " ").replace("_", " ").split()
                if any(t in slug_parts for t in EXCLUDED_TOPICS):
                    continue

                self._wiki_index[slug] = {
                    "slug": slug,
                    "title": title,
                    "path": str(md_file),
                    "word_count": word_count,
                    "last_modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(),
                    "snippet": content[:200].strip(),
                }
                self._page_count += 1
            except Exception as e:
                logger.debug(f"Failed to index {md_file}: {e}")

        # Load dossier count from wiki state
        if WIKI_STATE_FILE.exists():
            try:
                state = json.loads(WIKI_STATE_FILE.read_text(encoding="utf-8"))
                self._dossier_count = state.get("dossier_count", 0)
                if self._dossier_count == 0:
                    wiki_output_dir = WIKI_DIR.parent / "wiki_output"
                    if wiki_output_dir.exists():
                        self._dossier_count = len(list(wiki_output_dir.glob("dossier_*.md")))
            except json.JSONDecodeError as e:
                logger.warning("Wiki state file corrupted (%s), resetting dossier count", e)
            except Exception as e:
                logger.warning("Failed to read wiki state file: %s", e)

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from first H1 or H2 heading"""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
            if stripped.startswith("## "):
                return stripped[3:].strip()
        return None

    async def _sync_loop(self):
        """Periodic sync with state manager"""
        while self.running:
            try:
                await self._sync_to_state()
            except Exception as e:
                logger.error(f"Wiki sync error: {e}")
            await asyncio.sleep(self.SYNC_INTERVAL)

    async def _sync_to_state(self):
        """Push current wiki state to UnifiedStateManager"""
        if not self.sm:
            return

        await self.sm.publish(
            "wiki",
            {
                "pages": self._page_count,
                "dossiers": self._dossier_count,
                "last_update": datetime.now().isoformat(),
                "indexed_topics": list(self._wiki_index.keys())[:50],
            },
            source="wiki_pipeline"
        )

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search wiki pages by title/snippet"""
        query_lower = query.lower()
        results = []
        for slug, page in self._wiki_index.items():
            if query_lower in page["title"].lower() or query_lower in page["snippet"].lower():
                results.append(page)
                if len(results) >= limit:
                    break
        return results

    def get_page(self, slug: str) -> Optional[Dict]:
        """Get full wiki page data"""
        entry = self._wiki_index.get(slug)
        if not entry:
            return None
        result = {**entry}
        path = Path(entry["path"])
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                result["content"] = content
                result["word_count"] = len(content.split())
                current_mtime = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                if current_mtime != entry.get("last_modified"):
                    result["stale_index"] = True
            except Exception as e:
                logger.debug(f"Failed to read page content: {e}")
                result["content"] = None
        else:
            result["content"] = None
        return result

    def list_pages(self) -> List[Dict]:
        """List all indexed wiki pages. Note: may be stale if not refreshed."""
        return list(self._wiki_index.values())

    def list_sources(self) -> Dict[str, Dict]:
        """List raw source directories and their status"""
        result = {}
        for name, path in RAW_DIRS.items():
            if path.exists():
                file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                result[name] = {
                    "path": str(path),
                    "exists": True,
                    "file_count": file_count,
                }
            else:
                result[name] = {"path": str(path), "exists": False, "file_count": 0}
        return result

    def refresh(self, on_refresh=None) -> Dict:
        """Force rebuild of wiki index. Optionally notify state manager."""
        self._build_index()
        result = {
            "pages": self._page_count,
            "dossiers": self._dossier_count,
            "timestamp": datetime.now().isoformat(),
        }
        if on_refresh:
            on_refresh(result)
        return result

    async def async_refresh(self) -> Dict:
        """Force rebuild of wiki index and propagate to state manager."""
        result = self.refresh()
        if self.sm:
            await self.sm.publish("wiki", result, source="wiki_pipeline")
        return result

    def get_status(self) -> Dict:
        return {
            "running": self.running,
            "pages": self._page_count,
            "dossiers": self._dossier_count,
            "wiki_dir": str(WIKI_DIR),
            "indexed_topics": len(self._wiki_index),
        }


_wiki_pipeline: Optional[WikiPipeline] = None


def get_wiki_pipeline(state_manager=None) -> WikiPipeline:
    global _wiki_pipeline
    if _wiki_pipeline is None:
        _wiki_pipeline = WikiPipeline(state_manager=state_manager)
    elif state_manager and _wiki_pipeline.sm is None:
        _wiki_pipeline.sm = state_manager
    return _wiki_pipeline


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wiki Pipeline")
    parser.add_argument("--search", type=str, help="Search wiki")
    parser.add_argument("--list", action="store_true", help="List pages")
    parser.add_argument("--sources", action="store_true", help="List sources")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--refresh", action="store_true", help="Refresh index")
    args = parser.parse_args()

    pipeline = WikiPipeline()

    if args.search:
        results = pipeline.search(args.search)
        print(json.dumps(results, indent=2))
    elif args.list:
        pipeline._build_index()
        pages = pipeline.list_pages()
        for p in pages:
            print(f"  {p['slug']}: {p['title']} ({p['word_count']} words)")
    elif args.sources:
        sources = pipeline.list_sources()
        print(json.dumps(sources, indent=2))
    elif args.status:
        pipeline._build_index()
        print(json.dumps(pipeline.get_status(), indent=2))
    elif args.refresh:
        result = pipeline.refresh()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
