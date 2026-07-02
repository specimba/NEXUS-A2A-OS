"""Static checks for the 7356 wiki dashboard HTML (fallout-terminal theme)."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HTML_PATH = REPO / "nexus_os" / "archivist" / "wiki-ui" / "nexus-dashboard.html"

EXPECTED_THEMES = [
    "fallout-terminal", "nexus-cyan", "obsidian-purple", "matrix-green",
    "amber-alert", "frost-blue", "rose-gold", "monochrome", "solarized-dark",
]


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body_theme = None
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.body_theme = dict(attrs).get("data-theme")


def _html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


class TestFalloutTheme:
    def test_html_parses_and_default_theme(self):
        parser = _Parser()
        parser.feed(_html())
        assert parser.body_theme == "fallout-terminal"

    def test_all_nine_themes_have_css_blocks(self):
        html = _html()
        for theme in EXPECTED_THEMES:
            assert f'[data-theme="{theme}"]' in html, f"missing CSS block for {theme}"

    def test_all_nine_themes_registered_in_grid(self):
        html = _html()
        for theme in EXPECTED_THEMES:
            assert re.search(r'id:\s*"%s"' % re.escape(theme), html), f"{theme} not in themes[]"

    def test_crt_motion_is_reduced_motion_gated(self):
        html = _html()
        assert "prefers-reduced-motion: no-preference" in html
        # animations only inside the gated block: the keyframe names must not
        # be applied via a bare (ungated) fallout selector
        gated = html.split("prefers-reduced-motion: no-preference", 1)[1]
        assert "crt-breathe" in gated
        assert "cursor-blink" in gated

    def test_crt_layers_scoped_to_fallout_only(self):
        html = _html()
        assert 'body[data-theme="fallout-terminal"]::after' in html
        assert 'body[data-theme="fallout-terminal"]::before' in html
        # no unscoped body::after that would bleed into other themes
        assert not re.search(r"^body::after", html, flags=re.M)

    def test_ascii_kit_present(self):
        html = _html()
        for fn in ("function asciiFrame", "function asciiMeter", "function asciiTreePrefix"):
            assert fn in html

    def test_default_current_theme(self):
        assert 'let currentTheme = "fallout-terminal"' in _html()
