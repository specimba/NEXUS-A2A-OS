#!/usr/bin/env python3
"""
Minimal test runner using unittest (stdlib) — no pytest dependency.

Injects a pytest compatibility shim so existing pytest-style tests can import.
Discovers both unittest.TestCase classes and pytest-style test classes/functions.

Usage:
    python3 tests/run_tests.py              # discover and run all tests
    python3 tests/run_tests.py -v           # verbose mode
    python3 tests/run_tests.py security     # only tests/security/
    python3 tests/run_tests.py bridge        # only tests/bridge/
"""
import sys
import os
import unittest
import argparse
import inspect
import importlib.util
from pathlib import Path

# Ensure repo root is on path so imports resolve
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

# Detect if real pytest is available in the environment
has_real_pytest = False
try:
    import importlib.util
    orig_path = sys.path.copy()
    if str(ROOT / "tests") in sys.path:
        sys.path.remove(str(ROOT / "tests"))
    spec = importlib.util.find_spec("pytest")
    sys.path = orig_path
    if spec is not None:
        has_real_pytest = True
except Exception:
    pass

# Inject pytest compatibility shim before any test imports (if real pytest is not used)
import pytest_compat
sys.modules["pytest"] = pytest_compat


def _is_test_class(obj):
    """Detect pytest-style or unittest test classes."""
    if not inspect.isclass(obj):
        return False
    name = obj.__name__
    if not name.startswith("Test"):
        return False
    if name == "TestCase":
        return False
    return True


def _is_test_function(obj):
    """Detect test functions inside test classes."""
    if not inspect.isfunction(obj):
        return False
    return obj.__name__.startswith("test_")


def load_module_safely(path: Path):
    """Load a Python module from file path, with shim injected."""
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[WARN] Failed to import {path}: {e}")
        return None
    return module


def collect_from_module(module) -> list:
    """Collect test cases from a loaded module."""
    cases = []
    for name, obj in inspect.getmembers(module):
        if _is_test_class(obj):
            # If it inherits from unittest.TestCase, let unittest handle it
            if issubclass(obj, unittest.TestCase):
                cases.append(obj)
                continue
            # Pytest-style class: wrap methods into a synthetic TestCase
            test_methods = [
                (mname, mfunc)
                for mname, mfunc in inspect.getmembers(obj)
                if _is_test_function(mfunc)
            ]
            if test_methods:
                # Build a synthetic unittest.TestCase subclass
                for mname, mfunc in test_methods:
                    def _make_run(fn, cls):
                        def runTest(self):
                            # Instantiate the pytest-style class to provide fixture context
                            instance = cls() if cls.__init__ is object.__init__ else cls()
                            # Simple fixture: if fn takes 'detector' or 'vault' arg, provide one
                            import inspect
                            sig = inspect.signature(fn)
                            kwargs = {}
                            temp_dir = None
                            for param_name in sig.parameters:
                                if param_name == "self":
                                    continue
                                if param_name == "detector":
                                    from nexus_os.security.meta_attack_detector import MetaAttackDetector
                                    kwargs["detector"] = MetaAttackDetector()
                                if param_name == "vault":
                                    import tempfile
                                    from pathlib import Path
                                    from nexus_os.vault.manager import VaultManager
                                    temp_dir = tempfile.TemporaryDirectory()
                                    db_path = Path(temp_dir.name) / "vault.db"
                                    manager = VaultManager(str(db_path))
                                    manager.conn.execute("""
                                        CREATE TABLE IF NOT EXISTS agent_memory_tracks (
                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            agent_id TEXT NOT NULL,
                                            lane TEXT NOT NULL,
                                            track_type TEXT,
                                            key TEXT NOT NULL,
                                            value TEXT,
                                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                            UNIQUE(agent_id, lane, track_type, key)
                                        )
                                    """)
                                    manager.conn.commit()
                                    kwargs["vault"] = manager
                            try:
                                fn(instance, **kwargs)
                            finally:
                                if temp_dir is not None:
                                    try:
                                        temp_dir.cleanup()
                                    except Exception:
                                        pass
                        return runTest
                    case_cls = type(
                        f"{obj.__name__}_{mname}",
                        (unittest.TestCase,),
                        {"runTest": _make_run(mfunc, obj)},
                    )
                    cases.append(case_cls)
    return cases


def discover_pytest_style(start_dir: Path) -> unittest.TestSuite:
    """Discover pytest-style tests and wrap them into unittest cases."""
    suite = unittest.TestSuite()
    for pyfile in start_dir.rglob("test_*.py"):
        if pyfile.name == "run_tests.py":
            continue
        if "__pycache__" in str(pyfile):
            continue
        module = load_module_safely(pyfile)
        if module is None:
            continue
        for case_cls in collect_from_module(module):
            if issubclass(case_cls, unittest.TestCase):
                suite.addTests(unittest.TestLoader().loadTestsFromTestCase(case_cls))
    return suite


def discover_unittest(start_dir: Path) -> unittest.TestSuite:
    """Standard unittest discovery."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    if not start_dir.exists():
        return suite
    discovered = loader.discover(str(start_dir), pattern="test_*.py")
    suite.addTests(discovered)
    return suite


def run_tests(suite: unittest.TestSuite, verbosity: int = 1) -> bool:
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return result.wasSuccessful()


def main():
    parser = argparse.ArgumentParser(description="NEXUS minimal test runner")
    parser.add_argument("filter", nargs="?", default="", help="subdirectory filter (e.g. 'security', 'bridge')")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    args = parser.parse_args()

    verbosity = 2 if args.verbose else 1
    tests_dir = ROOT / "tests"

    if args.filter:
        target = tests_dir / args.filter
        print(f"[INFO] Running tests in: {target}")
    else:
        target = tests_dir
        print(f"[INFO] Discovering tests under: {tests_dir}")

    # If real pytest is available, use it instead of our basic shim wrapper
    if has_real_pytest:
        print("[INFO] Real pytest detected in environment. Running tests via pytest...")
        import sys
        # Restore real pytest to sys.modules
        import importlib
        try:
            # Force reload of pytest to get the real one
            if "pytest" in sys.modules:
                del sys.modules["pytest"]
            real_pytest = importlib.import_module("pytest")
            sys.modules["pytest"] = real_pytest
            
            pytest_args = []
            if args.verbose:
                pytest_args.append("-v")
            if args.filter:
                pytest_args.append(str(target))
            else:
                pytest_args.append(str(tests_dir))
                
            sys.exit(real_pytest.main(pytest_args))
        except Exception as e:
            print(f"[WARN] Failed to run tests via real pytest: {e}. Falling back to unittest...")
            # Restore the shim
            sys.modules["pytest"] = pytest_compat

    # Combine both unittest and pytest-style discovery
    suite = unittest.TestSuite()
    suite.addTests(discover_unittest(target))
    suite.addTests(discover_pytest_style(target))

    count = suite.countTestCases()
    print(f"[INFO] Discovered {count} test case(s)")
    if count == 0:
        print("[WARN] No tests found.")
        sys.exit(0)

    ok = run_tests(suite, verbosity=verbosity)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
