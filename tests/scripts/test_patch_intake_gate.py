import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "patch_intake_gate.py"


def run_gate(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_patch_intake_gate_accepts_matching_hash_and_byte_count(tmp_path):
    patch = tmp_path / "empty.patch"
    patch.write_text("", encoding="utf-8")
    digest = hashlib.sha256(b"").hexdigest()
    sidecar = tmp_path / "empty.patch.sha256"
    sidecar.write_text(f"{digest}  empty.patch\n", encoding="utf-8")

    result = run_gate(
        str(patch),
        "--sha256-file",
        str(sidecar),
        "--expected-sha256",
        digest,
        "--expected-bytes",
        "0",
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_patch_intake_gate_rejects_mismatched_hash(tmp_path):
    patch = tmp_path / "change.patch"
    patch.write_text("not a real patch\n", encoding="utf-8")

    result = run_gate(
        str(patch),
        "--expected-sha256",
        "0" * 64,
    )

    assert result.returncode == 1
    assert "expected sha256 mismatch" in result.stdout


def test_patch_intake_gate_can_run_git_apply_check(tmp_path):
    patch = tmp_path / "add-file.patch"
    patch.write_text(
        "diff --git a/tmp_patch_gate_fixture.txt b/tmp_patch_gate_fixture.txt\n"
        "new file mode 100644\n"
        "index 0000000..ce01362\n"
        "--- /dev/null\n"
        "+++ b/tmp_patch_gate_fixture.txt\n"
        "@@ -0,0 +1 @@\n"
        "+hello\n",
        encoding="utf-8",
    )

    result = run_gate(str(patch), "--repo", str(ROOT), "--apply-check")

    assert result.returncode == 0
    assert '"git_apply_check"' in result.stdout

