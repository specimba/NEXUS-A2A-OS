"""cron/agent_cycle.py — Agent Cycle Runner

Automated CI/self-check pipeline:
  - Test suite execution and result parsing
  - Git auto-backup behavior
  - Log rotation logic
  - Canary health check
  - Full pipeline orchestration
"""

import os
import sys
import json
import time
import subprocess
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    """Result of a single agent cycle run."""
    cycle_number: int
    timestamp: str
    tests_passed: bool
    test_count: int
    test_duration_s: float
    error: Optional[str] = None
    canary_passed: Optional[bool] = None
    git_backup: bool = False
    log_rotated: bool = False

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle_number,
            "timestamp": self.timestamp,
            "tests_passed": self.tests_passed,
            "test_count": self.test_count,
            "test_duration_s": self.test_duration_s,
            "error": self.error,
            "canary_passed": self.canary_passed,
            "git_backup": self.git_backup,
            "log_rotated": self.log_rotated,
        }


class AgentCycleRunner:
    """Runs the automated agent cycle: test, canary, backup, rotate."""

    def __init__(
        self,
        project_root: Path = None,
        log_file: Path = None,
        report_file: Path = None,
        enable_canary: bool = False,
        git_backup_enabled: bool = True,
        max_log_size_bytes: int = 10 * 1024 * 1024,  # 10 MB
    ):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.log_file = Path(log_file) if log_file else self.project_root / "cron" / "cycle.log"
        self.report_file = Path(report_file) if report_file else self.project_root / "cron" / "cycle_report.json"
        self.enable_canary = enable_canary
        self.git_backup_enabled = git_backup_enabled
        self.max_log_size_bytes = max_log_size_bytes
        self._cycle_count = self._load_cycle_count()

    def _load_cycle_count(self) -> int:
        """Load cycle count from report file."""
        if self.report_file.exists():
            try:
                with open(self.report_file, "r") as f:
                    data = json.load(f)
                return data.get("last_cycle", 0)
            except Exception:
                pass
        return 0

    def run_tests(self) -> Tuple[bool, int, int, int, float, str]:
        """Run pytest and return results."""
        test_dir = self.project_root / "tests"
        if not test_dir.exists():
            return False, 0, 0, 0, 0.0, "No test directory"

        start = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_dir), "-v", "--tb=no", "-q"],
                capture_output=True, text=True, timeout=300,
                cwd=str(self.project_root),
            )
            duration = time.time() - start

            # Parse output
            output = result.stdout + result.stderr
            passed = result.returncode == 0
            total = failures = errors = 0

            for line in output.split("\n"):
                if " passed" in line and "failed" not in line.split("passed")[0]:
                    parts = line.strip().split()
                    for p in parts:
                        if p.isdigit():
                            total += int(p)
                if "failed" in line:
                    for p in line.split():
                        try:
                            if "failed" in p:
                                num = p.replace("failed", "").replace(",", "")
                                if num:
                                    failures += int(num)
                        except (ValueError, IndexError):
                            pass

            if total == 0:
                # Try to count from summary line
                for line in output.split("\n"):
                    if "passed" in line:
                        try:
                            parts = line.strip().split()
                            for i, p in enumerate(parts):
                                if p == "passed" and i > 0:
                                    total = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass

            return passed, total, failures, errors, duration, output

        except subprocess.TimeoutExpired:
            return False, 0, 0, 0, time.time() - start, "Timeout"
        except Exception as e:
            return False, 0, 0, 0, time.time() - start, str(e)

    def git_backup(self) -> Tuple[bool, str]:
        """Create git auto-backup commit."""
        if not self.git_backup_enabled:
            return False, "Git backup disabled"

        try:
            cwd = str(self.project_root)

            # Init if needed
            subprocess.run(["git", "init"], cwd=cwd, capture_output=True, timeout=30)

            # Add all
            subprocess.run(["git", "add", "-A"], cwd=cwd, capture_output=True, timeout=30)

            # Commit (allow-empty for no-change runs)
            result = subprocess.run(
                ["git", "commit", "--allow-empty", "-m", f"auto-backup: cycle {self._cycle_count + 1}"],
                cwd=cwd, capture_output=True, text=True, timeout=30,
            )

            return True, f"Auto-backup cycle {self._cycle_count + 1}"

        except Exception as e:
            return False, str(e)

    def rotate_logs(self) -> bool:
        """Rotate log file if exceeding size limit."""
        if not self.log_file.exists():
            return False

        try:
            size = self.log_file.stat().st_size
            if size < self.max_log_size_bytes:
                return False

            # Archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive = self.log_file.parent / f"cycle.{timestamp}.log"
            self.log_file.rename(archive)
            return True

        except Exception:
            return False

    def run_canary(self) -> Tuple[bool, str]:
        """Run canary health check against bridge server."""
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as resp:
                if resp.status == 200:
                    return True, "Bridge healthy"
                return False, f"Bridge returned {resp.status}"
        except Exception as e:
            return False, f"Bridge unreachable: {e}"

    def run_cycle(self) -> CycleResult:
        """Run full cycle: canary -> tests -> backup -> rotate."""
        self._cycle_count += 1
        cycle_num = self._cycle_count
        timestamp = datetime.now().isoformat()

        # Canary check
        canary_passed = None
        if self.enable_canary:
            canary_passed, canary_msg = self.run_canary()
            if not canary_passed:
                result = CycleResult(
                    cycle_number=cycle_num, timestamp=timestamp,
                    tests_passed=False, test_count=0, test_duration_s=0.0,
                    error=f"Canary failed: {canary_msg}",
                    canary_passed=False, git_backup=False,
                )
                self._save_report(result)
                return result

        # Run tests
        passed, total, failures, errors, duration, stderr = self.run_tests()

        # Git backup
        backed_up = False
        if passed:
            backed_up, _ = self.git_backup()

        # Log rotation
        rotated = self.rotate_logs()

        # Build result
        error_msg = None
        if not passed:
            error_msg = f"Tests failed: {failures} failures, {errors} errors"

        result = CycleResult(
            cycle_number=cycle_num, timestamp=timestamp,
            tests_passed=passed, test_count=total, test_duration_s=duration,
            error=error_msg, canary_passed=canary_passed,
            git_backup=backed_up, log_rotated=rotated,
        )

        self._save_report(result)
        return result

    def _save_report(self, result: CycleResult):
        """Save cycle report to JSON file."""
        try:
            self.report_file.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            if self.report_file.exists():
                with open(self.report_file, "r") as f:
                    data = json.load(f)
            data["last_cycle"] = result.cycle_number
            data["last_result"] = result.to_dict()
            with open(self.report_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save report: {e}")


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=str, default=os.getcwd())
    parser.add_argument("--no-git", action="store_true")
    args = parser.parse_args()

    runner = AgentCycleRunner(
        project_root=Path(args.root),
        git_backup_enabled=not args.no_git,
    )
    result = runner.run_cycle()

    if result.tests_passed:
        print(f"Cycle {result.cycle_number}: PASSED ({result.test_count} tests, {result.test_duration_s:.1f}s)")
        sys.exit(0)
    else:
        print(f"Cycle {result.cycle_number}: FAILED ({result.error})")
        sys.exit(1)


if __name__ == "__main__":
    main()
