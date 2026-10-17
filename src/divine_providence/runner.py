"""Run subsystem code in isolated interpreter processes.

Every call gets a fresh ``sys.executable`` process whose ``PYTHONPATH`` holds
only the import roots it was given, so flat modules from different systems can
never shadow each other.
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
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
    cleanup_error: str = ""

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


def _terminate_tree(process: subprocess.Popen) -> str:
    """Stop the isolated process group, including workers started by a suite.

    Windows has no portable ``killpg`` equivalent; taskkill's tree mode is the
    same fallback used by the Observatory collector. Surface a failed cleanup
    instead of silently treating the process tree as contained.
    """
    error = ""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as exc:
            error = f"process-group cleanup failed: {exc}"
    elif os.name == "nt":
        try:
            killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    timeout=5, check=False)
            if killed.returncode != 0:
                error = f"taskkill tree cleanup failed (exit {killed.returncode})"
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = f"taskkill tree cleanup failed: {exc}"
    if process.poll() is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        except OSError as exc:
            error = f"{error}; direct-process cleanup failed: {exc}".strip("; ")
    return error


def _create_windows_job() -> int:
    """Create a kill-on-close Job Object for one isolated subsystem run."""
    import ctypes
    from ctypes import wintypes

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = ExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        ok = kernel32.SetInformationJobObject(
            handle, 9, ctypes.byref(info), ctypes.sizeof(info))  # JobObjectExtendedLimitInformation
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(handle)
    except BaseException:
        kernel32.CloseHandle(handle)
        raise


def _assign_windows_job_and_resume(process: subprocess.Popen, job: int) -> None:
    """Assign a suspended child before its code can create uncontained workers."""
    import ctypes
    from ctypes import wintypes

    class ThreadEntry32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry32)]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(ThreadEntry32)]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

    if not kernel32.AssignProcessToJobObject(job, process._handle):
        raise ctypes.WinError(ctypes.get_last_error())
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)  # TH32CS_SNAPTHREAD
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    thread = wintypes.HANDLE()
    try:
        entry = ThreadEntry32()
        entry.dwSize = ctypes.sizeof(entry)
        found = kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == process.pid:
                thread = kernel32.OpenThread(0x0002, False, entry.th32ThreadID)  # THREAD_SUSPEND_RESUME
                if not thread:
                    raise ctypes.WinError(ctypes.get_last_error())
                break
            found = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        if not thread:
            raise OSError(f"could not find suspended primary thread for pid {process.pid}")
        if kernel32.ResumeThread(thread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if thread:
            kernel32.CloseHandle(thread)
        kernel32.CloseHandle(snapshot)


def _close_windows_job(job: int) -> str:
    import ctypes
    from ctypes import wintypes

    close_handle = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL
    if close_handle(job):
        return ""
    return f"Windows Job Object cleanup failed: {ctypes.WinError(ctypes.get_last_error())}"


def _tail_text(buf: bytearray, chars: int) -> str:
    return bytes(buf).decode("utf-8", "replace")[-chars:] if chars else ""


def run(args: list[str], *, cwd: Path, pythonpath: list[str], timeout_s: int, tail: int = 4000) -> RunResult:
    """Run with a bounded deadline, process-tree teardown, and bounded output.

    The deadline covers both the direct interpreter and descendants that keep
    inherited stdout/stderr handles open after that interpreter exits.
    """
    if timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    if tail < 0:
        raise ValueError("tail must be nonnegative")
    cmd = [sys.executable, *args]
    t0 = time.monotonic()
    deadline = t0 + timeout_s
    # Retain enough bytes for up to four-byte UTF-8 characters, but never the
    # entire output of a noisy subsystem or driver.
    max_bytes = max(4 * tail, 4) if tail else 0
    buffers = (bytearray(), bytearray())
    read_errors: list[str] = []
    windows_job = 0
    p = subprocess.Popen(cmd, cwd=str(cwd), env=_env(pythonpath), stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=(os.name == "posix"),
                         creationflags=(0x00000004 if os.name == "nt" else 0))  # CREATE_SUSPENDED
    def drain(pipe, target: bytearray) -> None:
        try:
            read = getattr(pipe, "read1", pipe.read)
            while block := read(8192):
                if max_bytes:
                    target.extend(block)
                    if len(target) > max_bytes:
                        del target[:-max_bytes]
        except (OSError, ValueError) as exc:
            read_errors.append(f"output drain failed: {exc}")
        finally:
            try:
                pipe.close()
            except OSError as exc:
                read_errors.append(f"output pipe close failed: {exc}")

    readers: list[threading.Thread] = []
    timed_out = False
    interrupted_setup = False
    setup_error = ""
    cleanup_error = ""
    try:
        if os.name == "nt":
            try:
                windows_job = _create_windows_job()
                _assign_windows_job_and_resume(p, windows_job)
            except OSError as exc:
                setup_error = f"Windows process containment setup failed: {exc}"
        if not setup_error:
            for pipe, buffer in zip((p.stdout, p.stderr), buffers):
                reader = threading.Thread(target=drain, args=(pipe, buffer), daemon=True)
                readers.append(reader)
                reader.start()
            try:
                p.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
            if not timed_out:
                for reader in readers:
                    reader.join(timeout=max(0, deadline - time.monotonic()))
                timed_out = any(reader.is_alive() for reader in readers)
    except BaseException:
        # A cancelled MCP call or Ctrl-C must not leave the isolated suite alive.
        interrupted_setup = True
        raise
    finally:
        if timed_out or interrupted_setup or setup_error:
            if windows_job:
                # The parent may already have exited while a descendant holds
                # its output pipes. The job still owns that descendant; PID
                # based taskkill cannot reliably find it after parent exit.
                cleanup_error = _close_windows_job(windows_job)
                if not cleanup_error:
                    windows_job = 0
                    # Setup can be interrupted before job assignment. Closing
                    # an empty job does not kill its still-suspended child.
                    if p.poll() is None:
                        try:
                            p.kill()
                        except OSError as exc:
                            if p.poll() is None:
                                cleanup_error = f"direct-process cleanup failed: {exc}"
                else:
                    fallback_error = _terminate_tree(p)
                    if fallback_error:
                        cleanup_error += f"; {fallback_error}"
            else:
                cleanup_error = _terminate_tree(p)
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                cleanup_error = f"{cleanup_error}; direct process did not exit after kill".strip("; ")
            for reader in readers:
                if reader.ident is not None:
                    reader.join(timeout=1)
            if any(reader.is_alive() for reader in readers):
                cleanup_error = f"{cleanup_error}; output pipe remained open after cleanup".strip("; ")
            for index, pipe in enumerate((p.stdout, p.stderr)):
                if index >= len(readers) or readers[index].ident is None:
                    pipe.close()
        elif os.name == "posix":
            # A suite may close its pipes and exit while a background worker is
            # still in its process group. Its worker has no hub lifecycle.
            cleanup_error = _terminate_tree(p)
        if windows_job:
            job_cleanup = _close_windows_job(windows_job)
            if job_cleanup:
                cleanup_error = f"{cleanup_error}; {job_cleanup}".strip("; ")
    if read_errors:
        cleanup_error = f"{cleanup_error}; {'; '.join(read_errors)}".strip("; ")
    if setup_error:
        cleanup_error = f"{setup_error}; {cleanup_error}".strip("; ")
    return RunResult(cmd, str(cwd), -1 if timed_out or setup_error else p.returncode,
                     round(time.monotonic() - t0, 2),
                     _tail_text(buffers[0], tail), _tail_text(buffers[1], tail),
                     timed_out=timed_out, cleanup_error=cleanup_error)


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
    ok = (r.returncode == 0 and not r.timed_out and not r.cleanup_error and counts.get("passed", 0) > 0
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
    if r.returncode != 0 or r.timed_out or r.cleanup_error or not isinstance(payload, dict) or "connection" not in payload:
        return {"ok": False, "error": "driver failed or produced no connection record", "returncode": r.returncode,
                "timed_out": r.timed_out, "cleanup_error": r.cleanup_error,
                "stderr_tail": r.stderr_tail[-2000:], "stdout_tail": r.stdout_tail[-2000:]}
    return payload
