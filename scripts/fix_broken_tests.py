#!/usr/bin/env python3
"""Fix 2 broken test imports: cron/agent_cycle.py + hermes.py missing classes"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "src", "nexus_os")

print("=" * 60)
print(" FIX BROKEN TEST IMPORTS")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# FIX 1: Create cron/agent_cycle.py
# ═══════════════════════════════════════════════════════════════

cron_dir = os.path.join(SRC, "cron")
os.makedirs(cron_dir, exist_ok=True)

# __init__.py
init_path = os.path.join(cron_dir, "__init__.py")
if not os.path.exists(init_path):
    with open(init_path, "w") as f:
        f.write('"""Cron — Automated cycle runner"""\n')
    print("  OK  Created cron/__init__.py")

agent_cycle_code = '''"""cron/agent_cycle.py — Automated CI/Self-Check Pipeline

Runs test suites, git backup, log rotation, and canary health checks.
"""

import json
import os
import subprocess
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    """Result of a single agent cycle run."""
    cycle_number: int
    timestamp: str
    tests_passed: bool
    test_count: int = 0
    test_duration_s: float = 0.0
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
    """Automated CI/self-check pipeline runner.

    Runs: tests -> canary -> git backup -> log rotation -> report
    """

    MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB default
    MIN_SKILL_EXECUTIONS = 3

    def __init__(
        self,
        project_root: Path = None,
        log_file: Path = None,
        report_file: Path = None,
        enable_canary: bool = False,
        git_backup_enabled: bool = True,
    ):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.log_file = Path(log_file) if log_file else self.project_root / "cron" / "cycle.log"
        self.report_file = Path(report_file) if report_file else self.project_root / "cron" / "cycle_report.json"
        self.enable_canary = enable_canary
        self.git_backup_enabled = git_backup_enabled
        self.max_log_size_bytes = self.MAX_LOG_SIZE_BYTES
        self._cycle_count = self._load_cycle_count()

    def _load_cycle_count(self) -> int:
        """Load cycle count from report file."""
        if self.report_file.exists():
            try:
                with open(self.report_file, "r") as f:
                    data = json.load(f)
                return data.get("last_cycle", 0)
            except Exception:
                return 0
        return 0

    def _save_report(self, result: CycleResult):
        """Save cycle report to JSON file."""
        self.report_file.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if self.report_file.exists():
            try:
                with open(self.report_file, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["last_cycle"] = result.cycle_number
        data["last_result"] = result.to_dict()
        with open(self.report_file, "w") as f:
            json.dump(data, f, indent=2)

    def run_tests(self) -> Tuple[bool, int, int, int, float, str]:
        """Run pytest and return results.

        Returns: (passed, total, failures, errors, duration_s, stderr)
        """
        test_dir = self.project_root / "tests"
        if not test_dir.exists():
            return False, 0, 0, 0, 0.0, "No test directory found"

        start = time.time()
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_dir), "-v", "--tb=no", "-q"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            duration = time.time() - start
            stderr = result.stderr + result.stdout

            # Parse pytest output
            total = 0
            failures = 0
            errors = 0
            passed_count = 0

            for line in result.stdout.split("\\n"):
                line = line.strip()
                if " passed" in line or " failed" in line or " error" in line:
                    parts = line.split()
                    for part in parts:
                        if "passed" in part:
                            try:
                                passed_count = int(part.replace("passed", ""))
                            except ValueError:
                                pass
                        if "failed" in part:
                            try:
                                failures = int(part.replace("failed", ""))
                            except ValueError:
                                pass
                        if "error" in part and "errors" not in part:
                            try:
                                errors = int(part.replace("error", "").replace("errors", ""))
                            except ValueError:
                                pass

            total = passed_count + failures + errors
            passed = failures == 0 and errors == 0 and total > 0

            return passed, total, failures, errors, duration, stderr

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return False, 0, 0, 0, duration, "Test execution timed out"
        except Exception as e:
            duration = time.time() - start
            return False, 0, 0, 0, duration, str(e)

    def git_backup(self) -> Tuple[bool, str]:
        """Create git checkpoint commit.

        Returns: (success, message)
        """
        if not self.git_backup_enabled:
            return False, "Git backup disabled"

        try:
            cwd = str(self.project_root)

            # Init if needed
            if not (self.project_root / ".git").exists():
                subprocess.run(["git", "init"], cwd=cwd, capture_output=True, timeout=30)

            # Add all
            subprocess.run(["git", "add", "-A"], cwd=cwd, capture_output=True, timeout=30)

            # Commit
            result = subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "auto-backup: cycle checkpoint"],
                cwd=cwd, capture_output=True, text=True, timeout=30
            )

            return True, "auto-backup: cycle checkpoint"

        except Exception as e:
            return False, f"Git backup failed: {e}"

    def rotate_logs(self) -> bool:
        """Rotate log file if exceeding max size.

        Returns: True if rotated
        """
        if not self.log_file.exists():
            return False

        try:
            size = self.log_file.stat().st_size
            if size < self.max_log_size_bytes:
                return False

            # Archive
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            archive = self.log_file.parent / f"cycle.{timestamp}.log"
            self.log_file.rename(archive)
            return True
        except Exception:
            return False

    def run_canary(self) -> Tuple[bool, str]:
        """Run canary health check against Bridge server.

        Returns: (healthy, message)
        """
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as resp:
                if resp.status == 200:
                    return True, "Bridge healthy"
                return False, f"Bridge returned {resp.status}"
        except Exception as e:
            return False, f"Bridge unreachable: {e}"

    def run_cycle(self) -> CycleResult:
        """Execute full cycle: tests -> canary -> git -> rotate -> report."""
        self._cycle_count += 1
        cycle_number = self._cycle_count
        timestamp = datetime.now().isoformat()

        # 1. Run tests
        tests_passed, total, failures, errors, duration, stderr = self.run_tests()

        result = CycleResult(
            cycle_number=cycle_number,
            timestamp=timestamp,
            tests_passed=tests_passed,
            test_count=total,
            test_duration_s=duration,
        )

        if not tests_passed:
            result.error = f"Tests failed: {failures} failures, {errors} errors"
            self._save_report(result)
            return result

        # 2. Canary check (if enabled)
        if self.enable_canary:
            healthy, msg = self.run_canary()
            result.canary_passed = healthy
            if not healthy:
                result.error = f"Canary failed: {msg}"
                self._save_report(result)
                return result

        # 3. Git backup (if enabled)
        if self.git_backup_enabled:
            backed, msg = self.git_backup()
            result.git_backup = backed

        # 4. Log rotation
        result.log_rotated = self.rotate_logs()

        # 5. Save report
        self._save_report(result)

        return result


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Agent Cycle Runner")
    parser.add_argument("--root", type=str, default=".", help="Project root")
    parser.add_argument("--no-git", action="store_true", help="Disable git backup")
    parser.add_argument("--canary", action="store_true", help="Enable canary check")
    args = parser.parse_args()

    runner = AgentCycleRunner(
        project_root=Path(args.root),
        git_backup_enabled=not args.no_git,
        enable_canary=args.canary,
    )
    result = runner.run_cycle()

    if result.tests_passed:
        print(f"Cycle {result.cycle_number} PASSED ({result.test_count} tests)")
        sys.exit(0)
    else:
        print(f"Cycle {result.cycle_number} FAILED: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    import sys
    main()
'''

agent_cycle_path = os.path.join(cron_dir, "agent_cycle.py")
with open(agent_cycle_path, "w", encoding="utf-8") as f:
    f.write(agent_cycle_code)
print("  OK  Created cron/agent_cycle.py")

# ═══════════════════════════════════════════════════════════════
# FIX 2: Add ExperienceScorer + CostOptimizer to hermes.py
# ═══════════════════════════════════════════════════════════════

hermes_path = os.path.join(SRC, "engine", "hermes.py")

with open(hermes_path, "r", encoding="utf-8") as f:
    hermes = f.read()

# Add UNKNOWN and ANALYSIS to TaskDomain if missing
if "UNKNOWN" not in hermes:
    hermes = hermes.replace(
        'SECURITY = "security"',
        'SECURITY = "security"\n    UNKNOWN = "unknown"\n    ANALYSIS = "analysis"'
    )
    print("  OK  Added UNKNOWN and ANALYSIS to TaskDomain")

# Add ExperienceScorer class if missing
if "class ExperienceScorer" not in hermes:
    scorer_code = '''

class ExperienceScorer:
    """Bayesian-smoothed experience scoring from model_performance table.
    
    PRIOR_SUCCESS and PRIOR_FAILURE provide Bayesian smoothing
    to prevent small-sample overfitting.
    """
    PRIOR_SUCCESS = 10
    PRIOR_FAILURE = 2

    def __init__(self, db):
        self.db = db
        self._ensure_table()

    def _ensure_table(self):
        """Create model_performance table if not exists."""
        try:
            conn = self.db.get_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    model_id TEXT NOT NULL,
                    task_class TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    total_latency_ms REAL DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (model_id, task_class)
                )
            """)
            conn.commit()
        except Exception:
            pass

    def score(self, domain, models):
        """Score models using Bayesian smoothing.

        Returns dict of model_name -> score (0.0-1.0).
        """
        results = {}
        try:
            conn = self.db.get_connection()
        except Exception:
            # No DB connection - fall back to model quality_score
            for m in models:
                results[m.name if hasattr(m, 'name') else str(m)] = getattr(m, 'quality_score', 0.5)
            return results

        task_class = domain.value if hasattr(domain, 'value') else str(domain)

        for m in models:
            name = m.name if hasattr(m, 'name') else str(m)
            try:
                row = conn.execute(
                    "SELECT success_count, failure_count FROM model_performance WHERE model_id=? AND task_class=?",
                    (name, task_class)
                ).fetchone()

                if row and (row[0] + row[1]) > 0:
                    # Bayesian: (PRIOR_SUCCESS + successes) / (PRIOR_SUCCESS + successes + PRIOR_FAILURE + failures)
                    successes = row[0]
                    failures = row[1]
                    score = (self.PRIOR_SUCCESS + successes) / (
                        self.PRIOR_SUCCESS + successes + self.PRIOR_FAILURE + failures
                    )
                else:
                    # No data - fall back to model's quality_score
                    score = getattr(m, 'quality_score', 0.5)

                results[name] = score
            except Exception:
                results[name] = getattr(m, 'quality_score', 0.5)

        return results

    def record_outcome(self, model_id, domain, success, latency_ms):
        """Record a model execution outcome."""
        task_class = domain.value if hasattr(domain, 'value') else str(domain)
        try:
            conn = self.db.get_connection()
            # Upsert
            existing = conn.execute(
                "SELECT success_count, failure_count, total_latency_ms FROM model_performance WHERE model_id=? AND task_class=?",
                (model_id, task_class)
            ).fetchone()

            if existing:
                sc, fc, tl = existing
                if success:
                    sc += 1
                else:
                    fc += 1
                tl += latency_ms
                conn.execute(
                    "UPDATE model_performance SET success_count=?, failure_count=?, total_latency_ms=?, last_updated=CURRENT_TIMESTAMP WHERE model_id=? AND task_class=?",
                    (sc, fc, tl, model_id, task_class)
                )
            else:
                conn.execute(
                    "INSERT INTO model_performance (model_id, task_class, success_count, failure_count, total_latency_ms) VALUES (?, ?, ?, ?, ?)",
                    (model_id, task_class, 1 if success else 0, 0 if success else 1, latency_ms)
                )
            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record outcome: {e}")
'''

    # Insert before HermesRouter class
    if "class HermesRouter" in hermes:
        hermes = hermes.replace("class HermesRouter", scorer_code + "\nclass HermesRouter")
        print("  OK  Added ExperienceScorer to hermes.py")

# Add CostOptimizer class if missing
if "class CostOptimizer" not in hermes:
    optimizer_code = '''

class CostOptimizer:
    """Cost-aware model selection based on task complexity."""

    def __init__(self, quality_threshold=0.5):
        self.quality_threshold = quality_threshold

    def select(self, scores, models, complexity):
        """Select model based on scores + complexity.

        Args:
            scores: dict of model_name -> score
            models: list of ModelProfile objects
            complexity: TaskComplexity enum

        Returns:
            (selected_name, score, reason) tuple
        """
        model_map = {}
        for m in models:
            name = m.name if hasattr(m, 'name') else str(m)
            model_map[name] = m

        # Filter above threshold
        candidates = {k: v for k, v in scores.items() if v >= self.quality_threshold}

        if not candidates:
            # Fallback: use highest score regardless of threshold
            if scores:
                best = max(scores, key=scores.get)
                return best, scores[best], "Fallback (below threshold)"
            return None, 0.0, "No models available"

        comp_val = complexity.value if hasattr(complexity, 'value') else str(complexity)

        if comp_val in ("trivial", "standard"):
            # Cost-optimized: cheapest above threshold
            best = min(candidates, key=lambda k: self._get_cost(model_map.get(k)))
            return best, candidates[best], "Cost-optimized"

        elif comp_val == "critical":
            # Critical: prefer local if available and above threshold
            for name in candidates:
                m = model_map.get(name)
                if m and self._is_local(m):
                    return name, candidates[name], "local (critical preference)"
            best = max(candidates, key=candidates.get)
            return best, candidates[best], "Quality-first (critical)"

        else:
            # Default: highest score
            best = max(candidates, key=candidates.get)
            return best, candidates[best], "Quality-optimized"

    def _get_cost(self, model):
        """Get model cost."""
        if model is None:
            return 999.0
        return getattr(model, 'cost_per_million', getattr(model, 'cost', 0.0))

    def _is_local(self, model):
        """Check if model is local."""
        provider = getattr(model, 'provider', '')
        return provider in ('local', 'ollama')
'''

    if "class HermesRouter" in hermes:
        hermes = hermes.replace("class HermesRouter", optimizer_code + "\nclass HermesRouter")
        print("  OK  Added CostOptimizer to hermes.py")

# Write updated hermes.py
with open(hermes_path, "w", encoding="utf-8") as f:
    f.write(hermes)

# ═══════════════════════════════════════════════════════════════
# FIX 3: Ensure DatabaseManager has DBConfig and get_connection
# ═══════════════════════════════════════════════════════════════

db_path = os.path.join(SRC, "db")
db_init = os.path.join(db_path, "__init__.py")
db_mgr = os.path.join(db_path, "manager.py")

os.makedirs(db_path, exist_ok=True)

if not os.path.exists(db_init):
    with open(db_init, "w") as f:
        f.write('"""Database layer"""\n')
    print("  OK  Created db/__init__.py")

if not os.path.exists(db_mgr):
    db_mgr_code = '''"""Database Manager — SQLite with optional encryption."""

import sqlite3
import json
import logging
from dataclasses import dataclass
from typing import Optional, Any, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DBConfig:
    """Database configuration."""
    db_path: str = ":memory:"
    passphrase: str = ""
    encrypted: bool = False


class DatabaseManager:
    """SQLite database manager with optional SQLCipher support."""

    def __init__(self, config: DBConfig = None):
        self.config = config or DBConfig()
        self._conn = None
        self._connect()

    def _connect(self):
        """Establish database connection."""
        db_path = self.config.db_path
        if db_path == ":memory:":
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def get_connection(self):
        """Get raw SQLite connection."""
        return self._conn

    def setup_schema(self):
        """Create default tables."""
        conn = self._conn
        conn.execute("""CREATE TABLE IF NOT EXISTS vault (
            memory_id TEXT PRIMARY KEY, content TEXT, layer TEXT,
            metadata TEXT, created_at REAL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS model_performance (
            model_id TEXT NOT NULL, task_class TEXT NOT NULL,
            success_count INTEGER DEFAULT 0, failure_count INTEGER DEFAULT 0,
            total_latency_ms REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (model_id, task_class))""")
        conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
'''
    with open(db_mgr, "w", encoding="utf-8") as f:
        f.write(db_mgr_code)
    print("  OK  Created db/manager.py")
else:
    # Check if DBConfig exists
    with open(db_mgr, "r", encoding="utf-8") as f:
        mgr_content = f.read()
    if "class DBConfig" not in mgr_content:
        # Add DBConfig at the top
        dbconfig_addition = '''

@dataclass
class DBConfig:
    """Database configuration."""
    db_path: str = ":memory:"
    passphrase: str = ""
    encrypted: bool = False
'''
        # Add after imports
        mgr_content = mgr_content.replace(
            "\n\n\nclass ",
            dbconfig_addition + "\n\nclass ",
            1
        )
        with open(db_mgr, "w", encoding="utf-8") as f:
            f.write(mgr_content)
        print("  OK  Added DBConfig to db/manager.py")

print()
print("=" * 60)
print(" RUNNING FULL TEST SUITE")
print("=" * 60)

# Run tests
import subprocess
result = subprocess.run(
    ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-q"],
    capture_output=True, text=True, timeout=120
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr and "error" in result.stderr.lower():
    print("STDERR:", result.stderr[-1000:])

exit_code = result.returncode
print(f"\nExit code: {exit_code}")
print("=" * 60)