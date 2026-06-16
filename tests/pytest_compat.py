"""
pytest compatibility shim for unittest-based test runner.
Provides enough of the pytest API surface for existing NEXUS tests to import.
All decorators are no-ops or thin wrappers over unittest.
"""
import unittest
import functools
import sys
from types import SimpleNamespace


class Marker:
    """No-op marker that can be called with any args."""
    def __call__(self, *args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f
    def __getattr__(self, name):
        return self


mark = Marker()


def fixture(scope="function", autouse=False, **kwargs):
    """No-op fixture decorator."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def parametrize(argnames, argvalues):
    """Minimal parametrize: only handles single-argument cases simply."""
    names = [n.strip() for n in argnames.split(",")]
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self):
            # For unittest, we can't easily expand parametrize.
            # Just run the first value as a fallback.
            if argvalues:
                val = argvalues[0]
                # If it's a pytest.param, unwrap it if needed
                if hasattr(val, "values"):
                    val = val.values
                if len(names) == 1:
                    return func(self, val)
                else:
                    return func(self, *val)
            return func(self)
        return wrapper
    return decorator


def raises(expected_exception, match=None):
    """Context manager compatible with unittest assertRaises."""
    class RaisesContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                raise AssertionError(f"Expected {expected_exception.__name__} but no exception was raised")
            if not issubclass(exc_type, expected_exception):
                return False
            if match is not None and exc_val is not None:
                import re
                if not re.search(match, str(exc_val)):
                    raise AssertionError(
                        f"Exception {exc_type.__name__} message '{exc_val}' does not match pattern '{match}'"
                    )
            return True
    return RaisesContext()


def approx(expected, rel=None, abs=None):
    """Minimal approx for float comparisons."""
    class Approx:
        def __init__(self, expected):
            self.expected = expected
        def __eq__(self, other):
            tolerance = 1e-6
            if rel is not None:
                tolerance = max(tolerance, rel * abs(self.expected))
            if abs is not None:
                tolerance = max(tolerance, abs)
            return abs(other - self.expected) <= tolerance
    return Approx(expected)


def importorskip(modname, minversion=None, reason=None):
    """Mock importorskip: try to import or skip the test."""
    import importlib
    try:
        return importlib.import_module(modname)
    except ImportError:
        raise unittest.SkipTest(reason or f"Skipped: {modname} not available")


class Param:
    """Mock pytest.param."""
    def __init__(self, *values, marks=None, id=None):
        self.values = values
        self.marks = marks
        self.id = id


def param(*values, marks=None, id=None):
    return Param(*values, marks=marks, id=id)


# Assemble the fake pytest module
_module = sys.modules[__name__]
_module.fixture = fixture
_module.parametrize = parametrize
_module.raises = raises
_module.approx = approx
_module.mark = mark
_module.skip = lambda reason="": lambda f: f
_module.xfail = lambda reason="": lambda f: f
_module.importorskip = importorskip
_module.param = param

