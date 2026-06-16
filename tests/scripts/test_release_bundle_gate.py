from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_gate():
    path = ROOT / "scripts" / "release_bundle_gate.py"
    spec = importlib.util.spec_from_file_location("release_bundle_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def join(*parts: str) -> str:
    return "".join(parts)


def test_release_bundle_gate_allows_manifest_only_summary(tmp_path: Path) -> None:
    gate = load_gate()
    bundle = tmp_path / "safe_manifest.md"
    bundle.write_text(
        "\n".join(
            [
                "# Upload Manifest",
                "",
                "| Path | SHA-256 | Risk |",
                "|---|---|---|",
                "| evidence/raw-source.py | abc123 | redacted high-risk source |",
            ]
        ),
        encoding="utf-8",
    )

    report = gate.build_report(bundle)

    assert report["status"] == "PASS"
    assert report["counts"]["files_with_high_risk"] == 0


def test_release_bundle_gate_blocks_raw_socket_execution_chain(tmp_path: Path) -> None:
    gate = load_gate()
    bundle = tmp_path / "unsafe_bundle.md"
    bundle.write_text(
        "\n".join(
            [
                "# Raw Bundle",
                "```python",
                "import " + join("sock", "et"),
                "import " + join("sub", "process"),
                join("sub", "process") + ".Popen(['" + join("cmd", ".", "exe") + "'])",
                "```",
            ]
        ),
        encoding="utf-8",
    )

    report = gate.build_report(bundle)

    assert report["status"] == "BLOCK"
    assert report["counts"]["files_with_high_risk"] == 1
    assert report["high_risk_files"][0]["hits"][0]["indicator"] == "python_socket_exec_chain"


def test_release_bundle_gate_report_omits_payload_snippets(tmp_path: Path) -> None:
    gate = load_gate()
    source = tmp_path / "unsafe.py"
    source.write_text(
        "import "
        + join("sock", "et")
        + "\nimport "
        + join("sub", "process")
        + "\n"
        + join("sub", "process")
        + ".Popen(['"
        + join("cmd", ".", "exe")
        + "'])\n",
        encoding="utf-8",
    )
    markdown = tmp_path / "report.md"

    report = gate.build_report(source)
    gate.write_markdown(report, markdown)
    rendered = markdown.read_text(encoding="utf-8")

    assert report["status"] == "BLOCK"
    assert "subprocess.Popen" not in rendered
    assert "cmd.exe" not in rendered
    assert "python_socket_exec_chain" in rendered
