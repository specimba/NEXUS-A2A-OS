import json
import tempfile
from pathlib import Path

from nexus_os.nexusclaw.reset_chrome_lane_window_placement import main as reset_main


def test_reset_window_placement(tmp_path, monkeypatch):
    prof = tmp_path / "ChromeProfile"
    default = prof / "Default"
    default.mkdir(parents=True)
    pref = default / "Preferences"
    pref.write_text('{"browser":{"window_placement":{"top":-32000,"left":-32000,"right":-31999,"bottom":-31999,"maximized":false}}}', encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "reset",
            "--profile-dir",
            str(prof),
            "--width",
            "1280",
            "--height",
            "900",
        ],
    )
    import sys

    assert reset_main() == 0
    data = json.loads(pref.read_text(encoding="utf-8"))
    wp = data["browser"]["window_placement"]
    assert wp["maximized"] is True
    assert wp["right"] - wp["left"] == 1280
    assert wp["bottom"] - wp["top"] == 900