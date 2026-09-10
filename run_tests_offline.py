"""Offline test runner.

The system Python here has neither pytest nor pip/venv available. This runner
executes the project's test functions directly, providing minimal shims for the
few pytest features the tests use (``monkeypatch`` fixture and ``pytest.raises``),
so the suite can be verified without installing anything.

When pytest IS available, prefer:  python -m pytest -q

Usage:  python run_tests_offline.py
"""

from __future__ import annotations

import contextlib
import importlib
import inspect
import os
import sys
import types

TEST_MODULES = [
    "tests.test_agreement_harness",
    "tests.test_calibration_bias_evals",
    "tests.test_track_b_grader",
]


class _MonkeyPatch:
    """Minimal stand-in for pytest's monkeypatch (env var subset)."""

    def __init__(self) -> None:
        self._saved: list[tuple[str, str | None]] = []

    def delenv(self, name: str, raising: bool = True) -> None:
        self._saved.append((name, os.environ.get(name)))
        if name in os.environ:
            del os.environ[name]
        elif raising:
            raise KeyError(name)

    def setenv(self, name: str, value: str) -> None:
        self._saved.append((name, os.environ.get(name)))
        os.environ[name] = value

    def undo(self) -> None:
        for name, val in reversed(self._saved):
            if val is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = val
        self._saved.clear()


@contextlib.contextmanager
def _raises(exc_type):
    try:
        yield
    except exc_type:
        return
    except Exception as e:  # wrong exception type
        raise AssertionError(
            f"expected {exc_type.__name__}, got {type(e).__name__}: {e}"
        ) from e
    raise AssertionError(f"expected {exc_type.__name__} to be raised, none was")


def _install_pytest_shim() -> None:
    """Install a fake 'pytest' module so `import pytest` works in tests."""
    if "pytest" in sys.modules:
        return
    shim = types.ModuleType("pytest")
    shim.raises = _raises  # type: ignore[attr-defined]
    sys.modules["pytest"] = shim


def main() -> int:
    _install_pytest_shim()
    total = passed = 0
    failures: list[str] = []

    for mod_name in TEST_MODULES:
        mod = importlib.import_module(mod_name)
        funcs = [
            getattr(mod, n)
            for n in sorted(dir(mod))
            if n.startswith("test_") and callable(getattr(mod, n))
        ]
        for f in funcs:
            total += 1
            kwargs = {}
            mp = None
            if "monkeypatch" in inspect.signature(f).parameters:
                mp = _MonkeyPatch()
                kwargs["monkeypatch"] = mp
            try:
                f(**kwargs)
                passed += 1
                print(f"PASS {mod_name}::{f.__name__}")
            except Exception as e:  # noqa: BLE001 - report all test failures
                failures.append(f"{mod_name}::{f.__name__} -> {e!r}")
                print(f"FAIL {mod_name}::{f.__name__} -> {e!r}")
            finally:
                if mp is not None:
                    mp.undo()

    print(f"\n--- {passed}/{total} tests passed ---")
    if failures:
        print("FAILURES:")
        for x in failures:
            print("  ", x)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
