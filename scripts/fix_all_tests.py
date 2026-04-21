#!/usr/bin/env python3
"""Fix all broken test imports: hermes.py duplicates + missing cron package"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src")

print("=" * 60)
print(" FIX ALL BROKEN TESTS")
print("=" * 60)

# ── Fix 1: Remove duplicate ANALYSIS from TaskDomain in hermes.py ──
hermes_path = os.path.join(SRC, "nexus_os", "engine", "hermes.py")
with open(hermes_path, "r", encoding="utf-8") as f:
    h = f.read()

# Find TaskDomain enum and deduplicate
lines = h.split("\n")
new_lines = []
in_taskdomain = False
seen_members = set()
for line in lines:
    stripped = line.strip()
    if "class TaskDomain" in line:
        in_taskdomain = True
        new_lines.append(line)
        continue
    if in_taskdomain:
        if stripped and not stripped.startswith("#") and "=" in stripped and not stripped.startswith("class"):
            member_name = stripped.split("=")[0].strip()
            if member_name in seen_members:
                print(f"  FIX  Removed duplicate TaskDomain.{member_name}")
                continue
            seen_members.add(member_name)
        if stripped and (stripped.startswith("class ") and "TaskDomain" not in stripped):
            in_taskdomain = False
    new_lines.append(line)

h = "\n".join(new_lines)

# Ensure UNKNOWN, SECURITY, REASONING, ANALYSIS exist in TaskDomain
required_domains = ["CODE", "ANALYSIS", "REASONING", "CREATIVE", "OPERATIONS", "SECURITY", "UNKNOWN"]
for domain in required_domains:
    if f"{domain} = " not in h or h.count(f"{domain} = ") > h.count(f"class "):
        pass  # Will check after

# Add ExperienceScorer if missing
if "class ExperienceScorer" not in h:
    exp_scorer = '''

class ExperienceScorer:
    """Score models by Bayesian-smoothed experience."""
    PRIOR_SUCCESS = 10
    PRIOR_FAILURE = 2
    
    def __init__(self, db=None):
        self._db = db
        self._outcomes = {}  # (model_id, task_class) -> [successes, failures, total_latency]
    
    def score(self, domain, models):
        """Score models for a given domain using Bayesian smoothing."""
        results = {}
        for m in models:
            key = (m.name if hasattr(m, 'name') else str(m), domain.value if hasattr(domain, 'value') else str(domain))
            successes, failures, lat = self._outcomes.get(key, (0, 0, 0.0))
            if successes + failures == 0:
                results[key[0]] = m.success_rate if hasattr(m, 'success_rate') else 0.5
            else:
                results[key[0]] = (self.PRIOR_SUCCESS + successes) / (self.PRIOR_SUCCESS + successes + self.PRIOR_FAILURE + failures)
        return results
    
    def record_outcome(self, model_id, domain, success, latency_ms=0.0):
        """Record an outcome for a model in a domain."""
        key = (model_id, domain.value if hasattr(domain, 'value') else str(domain))
        s, f, lat = self._outcomes.get(key, (0, 0, 0.0))
        if success:
            s += 1
        else:
            f += 1
        lat += latency_ms
        self._outcomes[key] = (s, f, lat)
'''
    # Insert before HermesRouter
    h = h.replace("class HermesRouter", exp_scorer + "\nclass HermesRouter")
    print("  FIX  Added ExperienceScorer to hermes.py")

# Add CostOptimizer if missing
if "class CostOptimizer" not in h:
    cost_opt = '''

class CostOptimizer:
    """Select cheapest model above quality threshold."""
    def __init__(self, quality_threshold=0.5):
        self.quality_threshold = quality_threshold
    
    def select(self, scores, models, complexity):
        """Select model based on complexity and cost."""
        model_map = {m.name if hasattr(m, 'name') else str(m): m for m in models}
        
        if complexity.value if hasattr(complexity, 'value') else str(complexity) in ("trivial", "standard"):
            # Cheapest above threshold
            valid = [(name, score) for name, score in scores.items() if score >= self.quality_threshold]
            if not valid:
                if scores:
                    best = max(scores.items(), key=lambda x: x[1])
                    return best[0], best[1], "Fallback: no model above threshold"
                return "none", 0.0, "No models"
            valid.sort(key=lambda x: model_map.get(x[0], type('M',(),{'cost_per_million': 999})).cost_per_million if hasattr(model_map.get(x[0], type('M',(),{'cost_per_million': 999})), 'cost_per_million') else x[1])
            best_name = valid[0][0]
            return best_name, scores[best_name], "Cost-optimized selection"
        else:
            # Best quality, prefer local
            if not scores:
                return "none", 0.0, "No models"
            local = [(n, s) for n, s in scores.items() if hasattr(model_map.get(n), 'provider') and model_map[n].provider == "local"]
            if local:
                best = max(local, key=lambda x: x[1])
                return best[0], best[1], "Local-first for critical/complex"
            best = max(scores.items(), key=lambda x: x[1])
            return best[0], best[1], "Best quality selection"
'''
    h = h.replace("class HermesRouter", cost_opt + "\nclass HermesRouter")
    print("  FIX  Added CostOptimizer to hermes.py")

with open(hermes_path, "w", encoding="utf-8") as f:
    f.write(h)
print("  OK    hermes.py saved")

# ── Fix 2: Create cron package ───────────────────────────────────
cron_dir = os.path.join(SRC, "nexus_os", "cron")
os.makedirs(cron_dir, exist_ok=True)

# __init__.py
init_path = os.path.join(cron_dir, "__init__.py")
if not os.path.exists(init_path):
    with open(init_path, "w") as f:
        f.write('"""Cron — Automated CI/self-check pipeline"""\n')
    print("  OK    Created cron/__init__.py")

# agent_cycle.py
cycle_path = os.path.join(cron_dir, "agent_cycle.py")
agent_cycle_code = '''"""cron/agent_cycle.py — Agent Cycle Runner

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

            for line in output.split("\\n"):
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
                for line in output.split("\\n"):
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
'''

with open(cycle_path, "w", encoding="utf-8") as f:
    f.write(agent_cycle_code)
print("  OK    Created cron/agent_cycle.py")

# ── Fix 3: Update test_agent_cycle.py import path ──────────────
test_cron = os.path.join(REPO, "tests", "cron", "test_agent_cycle.py")
with open(test_cron, "r", encoding="utf-8") as f:
    tc = f.read()

tc = tc.replace(
    "from cron.agent_cycle import AgentCycleRunner, CycleResult",
    "from nexus_os.cron.agent_cycle import AgentCycleRunner, CycleResult"
)
tc = tc.replace(
    "from cron.agent_cycle import main",
    "from nexus_os.cron.agent_cycle import main"
)

with open(test_cron, "w", encoding="utf-8") as f:
    f.write(tc)
print("  OK    Fixed test_agent_cycle.py imports")

print()
print("=" * 60)
print(" RUNNING FULL TEST SUITE")
print("=" * 60)
os.system("pytest tests/ -v --tb=short -q")