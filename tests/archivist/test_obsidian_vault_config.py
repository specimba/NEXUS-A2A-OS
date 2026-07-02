"""Obsidian vault config validity for nexus_os/archivist/wiki/.obsidian."""
from __future__ import annotations

import json
from pathlib import Path

OBSIDIAN = Path(__file__).resolve().parents[2] / "nexus_os" / "archivist" / "wiki" / ".obsidian"


class TestVaultConfig:
    def test_config_jsons_valid(self):
        for name in ("app.json", "graph.json", "core-plugins.json", "community-plugins.json"):
            data = json.loads((OBSIDIAN / name).read_text(encoding="utf-8"))
            assert data is not None

    def test_no_community_plugins(self):
        assert json.loads((OBSIDIAN / "community-plugins.json").read_text(encoding="utf-8")) == []

    def test_graph_color_groups_cover_sections(self):
        graph = json.loads((OBSIDIAN / "graph.json").read_text(encoding="utf-8"))
        queries = {g["query"] for g in graph["colorGroups"]}
        assert queries == {"path:dossiers", "path:sources", "path:entities", "path:concepts"}

    def test_workspace_state_gitignored(self):
        gitignore = (OBSIDIAN / ".gitignore").read_text(encoding="utf-8")
        assert "workspace.json" in gitignore
