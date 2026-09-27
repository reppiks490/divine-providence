"""Run subsystem code in isolated interpreter processes.

Every call gets a fresh ``sys.executable`` process whose ``PYTHONPATH`` holds
only the import roots it was given, so flat modules from different systems can
never shadow each other.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from . import registry

_SUMMARY = re.compile(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected)")


@dataclass
class RunResult:
    command: list[str]
    cwd: str
    returncode: int
    seconds: float
    stdout_tail: str
    stderr_tail: str
    timed_out: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# Inherited settings that could silently change what a suite or script checks
# (e.g. PYTEST_ADDOPTS="-k smoke" deselects tests, PYTHONOPTIMIZE strips asserts).
_UNSAFE_ENV = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONOPTIMIZE", "PYTHONINSPECT", "PYTHONSTARTUP", "PYTHONHOME")


def _env(pythonpath: list[str]) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _UNSAFE_ENV}
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run(args: list[str], *, cwd: Path, pythonpath: list[str], timeout_s: int, tail: int = 4000) -> RunResult:
    cmd = [sys.executable, *args]
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=str(cwd), env=_env(pythonpath), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout_s)
        return RunResult(cmd, str(cwd), p.returncode, round(time.monotonic() - t0, 2),
                         p.stdout[-tail:], p.stderr[-tail:])
    except subprocess.TimeoutExpired as ex:
        out = ex.stdout if isinstance(ex.stdout, str) else (ex.stdout or b"").decode("utf-8", "replace")
        return RunResult(cmd, str(cwd), -1, round(time.monotonic() - t0, 2), out[-tail:], "", timed_out=True)


def pytest_counts(text: str) -> dict[str, int]:
    last = next((ln for ln in reversed(text.strip().splitlines()) if _SUMMARY.search(ln)), "")
    counts: dict[str, int] = {}
    for n, kind in _SUMMARY.findall(last):
        counts["errors" if kind.startswith("error") else kind] = int(n)
    return counts


def run_system_tests(name: str, timeout_s: int | None = None, extra_args: list[str] | None = None) -> dict:
    s = registry.get(name)
    r = run([*s.test_args, *(extra_args or [])], cwd=s.path, pythonpath=s.pythonpath(),
            timeout_s=timeout_s or s.test_timeout_s)
    counts = pytest_counts(r.stdout_tail)
    ok = (r.returncode == 0 and not r.timed_out and counts.get("passed", 0) > 0
          and not any(counts.get(k, 0) for k in ("failed", "errors", "deselected")))
    return {"system": name, "passed": ok, "counts": counts, **r.to_dict()}


def run_json_driver(driver: str, pythonpath: list[str], args: list[str] | None = None, timeout_s: int = 300) -> dict:
    """Run ``divine_providence.drivers.<driver>`` and parse the JSON it prints last."""
    root = str(registry.repo_root() / "src")
    r = run(["-m", f"divine_providence.drivers.{driver}", *(args or [])], cwd=registry.repo_root(),
            pythonpath=[root, *pythonpath], timeout_s=timeout_s, tail=200_000)
    try:
        payload = json.loads(r.stdout_tail.strip().splitlines()[-1]) if r.stdout_tail.strip() else None
    except (json.JSONDecodeError, IndexError):
        payload = None
    # A result counts only if the driver exited cleanly and its last line is the driver's own
    # connection record; a crash after printing, a timeout or a stray JSON log line fails closed.
    if r.returncode != 0 or r.timed_out or not isinstance(payload, dict) or "connection" not in payload:
        return {"ok": False, "error": "driver failed or produced no connection record", "returncode": r.returncode,
                "timed_out": r.timed_out, "stderr_tail": r.stderr_tail[-2000:], "stdout_tail": r.stdout_tail[-2000:]}
    return payload
