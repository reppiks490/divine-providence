"""Real child-process checks for the shared subsystem/connection runner."""
from __future__ import annotations

import os
from pathlib import Path
import time

import pytest

from divine_providence import runner


def test_timeout_kills_descendant_and_retains_both_output_tails(tmp_path: Path):
    marker = tmp_path / "orphan-survived"
    child = f"import time,pathlib;time.sleep(3);pathlib.Path({str(marker)!r}).write_text('bad')"
    script = ("import subprocess,sys,time;"
              f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
              "print('stdout before timeout',flush=True);"
              "print('stderr before timeout',file=sys.stderr,flush=True);"
              "time.sleep(10)")
    result = runner.run(["-c", script], cwd=tmp_path, pythonpath=[], timeout_s=1.5)
    assert result.timed_out is True
    assert result.returncode != 0
    assert result.cleanup_error == ""
    assert "stdout before timeout" in result.stdout_tail
    assert "stderr before timeout" in result.stderr_tail
    time.sleep(3.2)
    assert not marker.exists(), "timed-out suite left a descendant running"


def test_deadline_covers_descendant_pipe_after_direct_process_exits(tmp_path: Path):
    marker = tmp_path / "escaped-child"
    child = f"import time,pathlib;time.sleep(3);pathlib.Path({str(marker)!r}).write_text('bad')"
    script = ("import subprocess,sys;"
              f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
              "print('parent exited',flush=True)")
    result = runner.run(["-c", script], cwd=tmp_path, pythonpath=[], timeout_s=1.5)
    assert result.timed_out is True
    assert result.returncode != 0
    assert result.cleanup_error == ""
    assert "parent exited" in result.stdout_tail
    time.sleep(3.2)
    assert not marker.exists(), "runner returned while an inherited output pipe stayed open"


@pytest.mark.skipif(os.name != "posix", reason="POSIX isolated process groups")
def test_successful_suite_does_not_leave_background_worker(tmp_path: Path):
    marker = tmp_path / "background-survived"
    child = ("import os,time,pathlib;os.close(1);os.close(2);"
             f"time.sleep(.8);pathlib.Path({str(marker)!r}).write_text('bad')")
    script = ("import subprocess,sys;"
              f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
              "print('parent passed',flush=True)")
    result = runner.run(["-c", script], cwd=tmp_path, pythonpath=[], timeout_s=2)
    assert result.returncode == 0 and result.timed_out is False
    assert result.cleanup_error == ""
    assert "parent passed" in result.stdout_tail
    time.sleep(.9)
    assert not marker.exists(), "successful suite left a background worker running"


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object containment")
def test_successful_suite_does_not_leave_windows_descendant(tmp_path: Path):
    marker = tmp_path / "windows-background-survived"
    child = ("import os,time,pathlib;os.close(1);os.close(2);time.sleep(.8);"
             f"pathlib.Path({str(marker)!r}).write_text('bad')")
    script = ("import subprocess,sys,os;"
              f"child=subprocess.Popen([sys.executable,'-c',{child!r}]);"
              "os.close(1);os.close(2)")
    result = runner.run(["-c", script], cwd=tmp_path, pythonpath=[], timeout_s=2)
    assert result.returncode == 0 and result.timed_out is False
    assert result.cleanup_error == ""
    time.sleep(.9)
    assert not marker.exists(), "successful suite left a Windows descendant running"


def test_runner_retains_only_bounded_output_tail(tmp_path: Path):
    script = ("import os;"
              "os.write(1,b'x'*1000000+b'last out');"
              "os.write(2,b'y'*1000000+b'last err')")
    result = runner.run(["-c", script], cwd=tmp_path, pythonpath=[], timeout_s=10, tail=64)
    assert result.returncode == 0 and result.timed_out is False
    assert result.stdout_tail.endswith("last out") and len(result.stdout_tail) <= 64
    assert result.stderr_tail.endswith("last err") and len(result.stderr_tail) <= 64


def test_cancellation_during_reader_setup_reaps_child(monkeypatch, tmp_path: Path):
    processes = []
    popen = runner.subprocess.Popen

    def capture_process(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process

    def cancel_start(_self):
        raise KeyboardInterrupt

    monkeypatch.setattr(runner.subprocess, "Popen", capture_process)
    monkeypatch.setattr(runner.threading.Thread, "start", cancel_start)
    with pytest.raises(KeyboardInterrupt):
        runner.run(["-c", "import time;time.sleep(30)"], cwd=tmp_path,
                   pythonpath=[], timeout_s=5)
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed


@pytest.mark.skipif(os.name != "nt", reason="Windows suspended process setup")
@pytest.mark.parametrize("failure", [KeyboardInterrupt, OSError])
def test_failed_job_assignment_reaps_child_and_closes_job(monkeypatch, tmp_path: Path, failure):
    processes, closed_jobs = [], []
    popen = runner.subprocess.Popen
    close_job = runner._close_windows_job

    def capture_process(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process

    def cancel_assignment(_process, _job):
        raise failure("injected assignment failure")

    def capture_close(job):
        result = close_job(job)
        closed_jobs.append(result)
        return result

    monkeypatch.setattr(runner.subprocess, "Popen", capture_process)
    monkeypatch.setattr(runner, "_assign_windows_job_and_resume", cancel_assignment)
    monkeypatch.setattr(runner, "_close_windows_job", capture_close)
    if failure is KeyboardInterrupt:
        with pytest.raises(KeyboardInterrupt):
            runner.run(["-c", "import time;time.sleep(30)"], cwd=tmp_path,
                       pythonpath=[], timeout_s=5)
    else:
        result = runner.run(["-c", "import time;time.sleep(30)"], cwd=tmp_path,
                            pythonpath=[], timeout_s=5)
        assert result.returncode == -1 and result.timed_out is False
        assert "Windows process containment setup failed" in result.cleanup_error
    assert len(processes) == 1 and processes[0].poll() is not None
    assert processes[0].stdout.closed and processes[0].stderr.closed
    assert closed_jobs == [""]
