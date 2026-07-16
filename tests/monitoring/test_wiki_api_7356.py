"""Tests for the 7356 dashboard server's same-origin wiki API.

Spawns the real Node server on an ephemeral port and exercises
/wiki/api/index and /wiki/api/page/<slug> including traversal rejection.
"""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SERVER = REPO / "scripts" / "serve_dashboard_7356.js"

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node not available")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    port = _free_port()
    proc = subprocess.Popen(
        [node, str(SERVER)],
        env={"PORT": str(port), "HOST": "127.0.0.1", "PATH": str(Path(node).parent), "SystemRoot": "C:\\Windows"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=REPO,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{url}/wiki/", timeout=1)
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        else:
            proc.kill()
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            pytest.fail(f"7356 server did not start: {out[:500]}")
        yield url
    finally:
        proc.kill()


def _get_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


class TestWikiIndex:
    def test_index_shape_and_dossiers_present(self, server_url):
        data = _get_json(f"{server_url}/wiki/api/index")
        assert data["count"] == len(data["files"]) > 0
        assert "archivist/dossiers" in data["categories"]
        sample = data["files"][0]
        for key in ("slug", "title", "category", "updatedAt", "size", "headings", "excerpt", "frontmatter"):
            assert key in sample
        dossiers = [f for f in data["files"] if f["category"] == "archivist/dossiers"]
        assert len(dossiers) >= 8, "the 8 migrated dossiers must be indexed"

    def test_frontmatter_parsed(self, server_url):
        data = _get_json(f"{server_url}/wiki/api/index")
        trust = next(f for f in data["files"] if f["slug"].endswith("dossier_trust.md"))
        assert isinstance(trust["frontmatter"]["tags"], list)

    def test_dot_dirs_skipped(self, server_url):
        data = _get_json(f"{server_url}/wiki/api/index")
        assert not any("/.obsidian/" in f["slug"] or f["slug"].startswith(".") for f in data["files"])


class TestWikiPage:
    def test_dossier_fetch(self, server_url):
        with urllib.request.urlopen(
            f"{server_url}/wiki/api/page/archivist/dossiers/dossier_trust.md", timeout=10
        ) as resp:
            body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert len(body) > 100

    def test_unknown_slug_404(self, server_url):
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(f"{server_url}/wiki/api/page/archivist/nope.md", timeout=10)
        assert exc.value.code == 404

    def test_traversal_rejected(self, server_url):
        for evil in (
            "archivist/..%2F..%2Fsecrets.md",
            "docs/../../.modelrelay.json",
            "archivist/../../nexus_governance.db",
        ):
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(f"{server_url}/wiki/api/page/{evil}", timeout=10)
            assert exc.value.code == 404

    def test_non_docs_category_rejected(self, server_url):
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(f"{server_url}/wiki/api/page/docs/secrets/x.md", timeout=10)
        assert exc.value.code == 404


class TestBrowseAssets:
    def test_vendored_marked_served(self, server_url):
        with urllib.request.urlopen(f"{server_url}/wiki/vendor/marked.min.js", timeout=10) as resp:
            body = resp.read()
        assert resp.status == 200
        assert b"marked" in body[:200]

    def test_dashboard_references_live_api(self, server_url):
        with urllib.request.urlopen(f"{server_url}/wiki/", timeout=10) as resp:
            html = resp.read().decode("utf-8")
        assert "/wiki/api/index" in html
        assert "/wiki/vendor/marked.min.js" in html
        assert "ARCHIVE OFFLINE" in html  # offline fallback panel exists
        assert "wikilinkPass" in html     # [[wikilink]] click-through wired

    def test_dashboard_html_is_not_cached(self, server_url):
        with urllib.request.urlopen(f"{server_url}/", timeout=10) as resp:
            html = resp.read().decode("utf-8")
            cache_control = resp.headers.get("Cache-Control")
        assert "NEXUS Model Arena" in html
        assert cache_control == "no-store, max-age=0, must-revalidate"
