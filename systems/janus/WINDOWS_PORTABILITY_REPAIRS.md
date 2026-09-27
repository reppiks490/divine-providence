# JANUS ∞ — Windows Portability Repairs (post Run 038)

Scope: `systems/janus` only. Goal: full suite green on Windows 11 / CPython 3.10.11 (venv) without changing
Linux semantics, hash/serialization/canonicalization logic, schemas, or authority semantics.

## Result

| Run (Windows 11, `python -m pytest -q -p no:cacheprovider -o addopts=`, `PYTHONPATH=src`) | Summary |
|---|---|
| Before (pristine Run 038 files) | 39 failed, 104 passed, 1 skipped, 31 errors in 352.54s |
| After | 140 passed, 4 skipped in 84.94s |
| After, README runner `python -m unittest discover -s tests` | Ran 143 tests, OK (skipped=4) |

The 4 skips are the pre-existing `/dev/full unavailable` runtime skip plus the 3 platform skips listed in D3.
(pytest counts 144 and unittest 143 because `test_run016_authorized_sync_fails_before_mutation_without_quorum(tmp_path)`
is a pytest-only module-level function; this predates these repairs.)

`python -m compileall -q src`: exit 0. Schemas: 72/72 parse and pass Draft 2020-12 meta-schema validation (no schema touched).

## File hashes (SHA-256)

| File | Run 038 capsule (verified: reversing these edits reproduces it byte-for-byte) | After repairs |
|---|---|---|
| `src/janus_infinity/core.py` | `910084cd582a575e30cc2918fa8814faed0d154c9f5e320ba193d5dc3f9e2ad0` | `19a1d94988fc5cdac72aabf0a364d6e0253c6dba92532e065e5f0cd2d6aa10c2` |
| `tests/test_janus.py` | `c5b5725fc9ba43cf590663cf29ad2e5ee1157fcefe5409da0f91ef1df7faa789` | `79a7c11568f8d7bafb91b27593faaaf33300f3d6643274205a9576ff4d8cde63` |

Total diff: core.py +4 / −3; test_janus.py +54 / −26 (mostly re-indentation of the two kill blocks into `try/finally`).

## D1 — Leaked SQLite integrity-probe connection (production defect; 34 PermissionErrors + 31 teardown errors)

- **Symptom**: `PermissionError: [WinError 32] ... *.stage` raised from the `finally:` stage cleanup in
  `atomic_joint_sync`, masking the expected `ValueError('storage_stage_integrity_failed:...')`. Every test that uses the
  `corrupt_stage_before_promotion` / `truncate_stage_before_promotion` fault, including the shared
  `_certified_sender()` fixture of Run031–Run038, failed. The 31 ERRORs were the resulting `TemporaryDirectory` teardown failures.
- **Root cause**: `probe=sqlite3.connect(stage_path); integrity=...probe.execute("PRAGMA integrity_check")...; probe.close()`.
  On a corrupted or truncated file, `connect()` succeeds and `execute()` raises `DatabaseError`, so `close()` is skipped. The
  still-referenced `probe` local keeps the OS file handle open until the function returns, but the `finally:` unlink of the
  stage file runs before that return. POSIX allows unlinking an open file, so Linux never showed the leak. Windows refuses.
  A standalone repro confirmed that the unfixed pattern fails unlink with WinError 32 and `contextlib.closing` fixes it.
- **Fix**: `with contextlib.closing(sqlite3.connect(...)) as probe: integrity=...`. The connection now closes on every path.
  The computed `integrity` string and the exceptions caught are identical, so Linux behaviour is unchanged apart from the
  handle being released earlier. The same leak shape was fixed at the two other integrity-probe sites.
- **Changed functions** (`core.py`, plus `import contextlib`):
  - `JanusTwin.atomic_joint_sync`: stage integrity probe (the failing site).
  - `JanusTwin.classify_storage_artifacts`: same pattern. The handle leaked until return; not hit by tests.
  - `JanusTwin.classify_storage_artifacts_non_mutating`: same pattern inside a `TemporaryDirectory`, whose Windows
    cleanup would fail whenever the snapshot integrity check raises. Not hit by tests.

## D2 — `signal.SIGKILL` in external-kill tests, and the Windows venv launcher PID (2 failures, 2 errors, later intermittent)

- **Symptom**: `AttributeError: module 'signal' has no attribute 'SIGKILL'`. Because the child was never killed, it sat in the
  `hard_wait_at` infinite sleep holding the DB, so teardown also errored and the child process was orphaned.
- **Root cause (a)**: `SIGKILL` does not exist on Windows. It is used only in the tests; production code never sends signals.
- **Root cause (b)**, found after (a) was patched and the test became intermittent (3/12 teardown failures): on Windows,
  `venv\Scripts\python.exe` is a launcher stub that runs the real interpreter as a *child*. `Popen.pid` is the launcher PID
  (verified: `Popen.pid` 26912 vs interpreter `os.getpid()` 9600, parent 26912). Killing `proc.pid` killed only the launcher.
  The DB-holding interpreter was then torn down asynchronously by the launcher's kill-on-close job object, racing `tearDown`.
- **Fix** (test code only; the POSIX kill and assertion statements are unchanged):
  - The child prints `os.getpid()` first. The parent reads that one line from a pipe and closes it. Nothing else on the
    child's path writes to stdout.
  - On `win32` only: `os.kill(db_pid, signal.SIGTERM)`. On Windows this is an unconditional external `TerminateProcess`
    with exit code = sig (documented CPython behaviour), i.e. the Windows hard-kill primitive: no `finally`/`atexit` runs. It
    targets the process that actually holds the DB. The launcher waits for that process and propagates its exit code, so
    `proc.wait()` returns only after the DB holder is gone. The test then asserts `proc.returncode == 15` (the externally
    imposed code), which is the Windows equivalent of POSIX `returncode < 0`.
  - On POSIX: `os.kill(proc.pid, signal.SIGKILL); proc.wait(timeout=5); self.assertLess(proc.returncode, 0)`, unchanged.
  - All recovery assertions (`integrity_check == 'ok'`, `recover_promotion` → `aborted` / `committed`, receipt binding,
    journal status, facts promoted) run unchanged on both platforms. Coverage of external-kill recovery is kept on Windows,
    not skipped.
  - Child reaping is guaranteed on both platforms: the poll/kill block runs inside `try/finally: _reap_crash_child(proc, db_pid)`.
    If an assertion fails before the kill line (the path that previously orphaned `hard_wait_at` children, which sleep
    forever holding their temp DB), the reaper hard-kills the DB-holding interpreter (`db_pid`, falling back to `proc.pid`)
    and waits, with a timeout fallback to `proc.kill()`. On the success path it is a no-op because `proc.poll()` is already set.
- **Changed tests / helpers**: `Run027ExternalKillAuditTests.test_external_sigkill_after_prepare_recovers_aborted`,
  `Run028WalRecoveryCrossLinkTests.test_external_sigkill_after_authoritative_backup_recovers_committed`, and the new
  module-level helper `_reap_crash_child` (not collected as a test).
- **Evidence**: before the reaper, both tests were run together 15 times, 30/30 passes. After the reaper, 10 more runs gave
  20/20 passes. A forced-failure check (a subclass that fails `assertIsNotNone` right after polling, i.e. before the kill)
  produced 2 FAILs, 0 ERRORs (the tempdir teardown succeeded) and 0 surviving `hard_wait_at` processes.

## D3 — Kernel rlimit fault probes (3 failures): POSIX-only capability → platform skip, production unchanged

- **Symptom**: `'kernel_file_size_limit' != 'probe_failed'`, `'kernel_fd_limit' != 'unexpected'`,
  `'kernel_file_size_limit' != 'unexpected'`.
- **Root cause**: `run_host_storage_fault_probe`, `run_host_fd_exhaustion_probe` and `run_host_file_size_limit_probe`
  exercise kernel-enforced `setrlimit(RLIMIT_FSIZE)` → `EFBIG`/`SIGXFSZ` and `setrlimit(RLIMIT_NOFILE)` → `EMFILE` (the fd probe
  also opens `/dev/null`). Windows has no `resource` module, no per-process file-size limit and no `/dev/null`, so the
  behaviour asserted by these tests cannot exist there.
- **Why production was not changed**: on Windows the probes already fail closed and report no false positive. Verified outputs:
  `probe_failed` (stderr: `ModuleNotFoundError: No module named 'resource'`), `unexpected`, `unexpected`, each with
  `errno=None` and `returncode=1`, and all valid against their schemas. A new `unsupported_platform` classification is not in
  the `classification` enums of `host_storage_fault_probe`, `host_fd_fault_probe` or `host_file_size_fault_probe`
  (the last also sets `additionalProperties:false`), so adding one would require a schema change, which is out of scope.
- **Platform skips added** (`@unittest.skipIf(sys.platform=='win32', ...)`; `unittest` is used because the suite is
  `unittest`-based and the README runs it with `python -m unittest`, so a `pytest` import would add a dependency):
  - `Run029ShmHostFaultForensicDagTests.test_kernel_rlimit_fault_probe_is_real_and_isolated`: asserts real
    RLIMIT_FSIZE / errno 27 EFBIG.
  - `Run031IndependentReceiverReplayTests.test_kernel_fd_exhaustion_probe_is_real_and_isolated`: asserts real
    RLIMIT_NOFILE / errno 24 EMFILE.
  - `Run032ObjectReplayForkFaultTests.test_kernel_file_size_limit_probe_is_real_and_isolated`: asserts real
    RLIMIT_FSIZE / errno 27 EFBIG.
  These skip only on Windows. On Linux they run exactly as before, and no assertion was weakened or removed.

## Not changed

Hash, serialization, canonicalization, digest, signature, schema and authority logic are untouched. There are no production
behaviour changes on Linux beyond releasing SQLite handles on the error path. No tests were deleted. No git operations.

## Residual notes

- The Linux suite was not re-run: no Linux runtime (WSL/docker) is available on this host. Linux-path equivalence rests on
  the diff. POSIX branches keep the original statements, and the D1 change is a pure resource-release fix.
- `pyproject.toml` declares `requires-python >= 3.11`, but this venv is 3.10.11. The suite passes on 3.10; the metadata is unchanged.
- Pre-fix runs on this host had left orphaned `hard_wait_at` children (launcher + interpreter pairs), which sleep forever holding
  `%TEMP%\tmp*\sigkill*.db`. They were terminated, and the D2 reaper prevents new ones. The reaper cannot cover a hard kill of
  the test runner itself.
