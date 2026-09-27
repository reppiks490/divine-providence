# Windows portability repairs: Infrastructure Supervisory Loop

Scope: `systems/infrastructure` only. Goal: the full suite passes on Windows while Linux semantics stay exactly the same. No cryptographic, canonical-serialization, hash-chain or authority logic was changed.

## Result

| Run | Command | Result |
|---|---|---|
| Baseline (Windows 11, CPython 3.10, cryptography 46) | `python -m pytest -q -p no:cacheprovider -o addopts=` | **38 failed, 307 passed** |
| After D1 only | same | 29 failed, 316 passed |
| After D1 + D2 + D3 | same | 1 failed, 344 passed |
| Final (D1 + D2 + D3 + one platform skip) | same, pytest exit 0 | **344 passed, 1 skipped** |
| Byte-compile | `python -m compileall -q .` | exit 0 (the generated `__pycache__` directories were removed afterwards) |

`PYTHONDONTWRITEBYTECODE=1` was set for all pytest runs. On Linux every change below is inert by construction (see "Linux equivalence"), so the Linux suite still runs all 345 tests with no skips. That was not executed here because this host has no WSL distribution.

## Defects, root causes and fixes

### D1: directory fsync is impossible on Windows (9 direct failures; also fatal for any `fsync=True` path)

- **Symptom:** `PermissionError: [Errno 13] Permission denied: '<dir>'` in `test_v48_provenance_index.py` (5 tests) and `test_v49_atomic_witnessed_provenance.py` (4 tests). The same code sits on the default `fsync=True` path of every durable store.
- **Root cause:** after each `os.replace`, the stores make the rename durable with the POSIX idiom `fd = os.open(str(directory), os.O_RDONLY); os.fsync(fd)`. The Windows C runtime cannot open a directory as a file descriptor, so `os.open(<dir>, O_RDONLY)` always raises EACCES (reproduced directly: `PermissionError 13 EACCES`). The exception escapes after the data file has already been renamed, so the operation is reported as failed even though its bytes were written.
- **Fix:** the directory-fsync block at all 21 sites is now skipped only when the OS cannot perform it: `if fsync:` became `if fsync and os.name != 'nt':` (one site already read `if fsync and self.directory.exists():`). The file fsync before each `os.replace` is unchanged on every platform. Windows has no CRT-level directory fsync; NTFS journals the rename's metadata.

### D2: `os.kill(pid, 0)` is not a liveness probe on Windows

- **Symptom:** `RuntimeError: no demonstrably dead pid available` (`test_v24_recovery_lock.py`). Latent in production: a stale lock left by a dead owner could never be reclaimed through the death path.
- **Root cause:** `RecoveryChainLock._pid_definitely_dead` relies on POSIX `kill(pid, 0)` semantics (ESRCH means dead). In CPython on Windows, `os.kill` with signal `0 == CTRL_C_EVENT` calls `GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)`. That is a console signal-delivery call, not an existence check. For a nonexistent PID it fails with winerror 87 / errno 22 (EINVAL), never ESRCH, so the function returned False for every PID (reproduced: `OSError 22 87`).
- **Fix:** `_pid_definitely_dead` dispatches to `process_identity.windows_pid_definitely_dead` when `os.name == 'nt'`. The POSIX `os.kill` path is byte-identical. The Windows probe returns True only on positive evidence:
  - `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` failing with `ERROR_INVALID_PARAMETER` (87), meaning the PID names no process; or
  - `GetExitCodeProcess` returning an exit code other than `STILL_ACTIVE`, meaning the process has terminated.

  Access denied, any other error, or an out-of-range PID returns False (not provably dead). An exit status of 259 (== `STILL_ACTIVE`) is treated as running, which errs toward "not dead".
  - Verified: live child → not dead; own PID → not dead; PID 4 (access denied) → not dead; nonexistent PID → dead; exited child → dead.

### D3: no process-identity provider on Windows, so the recovery lock always failed closed (28 failures)

- **Symptom:** `acquire()` always returned False. The integration tests (v23, v29, v31–v35) then showed an empty chain (`generation 0 == 1`, `[] == ['fd437ffe…']`, missing `auth-…json`/`checkpoint-…json`), because `infrastructure_loop.py` runs every chain append inside `with RecoveryChainLock(...)` and converts the resulting `TimeoutError` into `restore_eligible = False` (`except Exception`, ~line 558). Nothing was ever persisted or restored.
- **Root cause:** the V25/V26 lock correctly refuses to acquire without process identity evidence (`boot_id`, `process_start`). `default_process_identity_provider()` and the module-level hooks `recovery_lock._boot_identity` / `_process_start_identity` only read Linux `/proc`, so on Windows identity was always `unknown`. The fail-closed behavior was right; the Windows evidence source was missing.
- **Fix:** added `WindowsProcessIdentityProvider` (assurance STRONG), which `default_process_identity_provider()` selects when `os.name == 'nt'` (the Linux `/proc` check still runs first and is unchanged). The two module hooks gained an `os.name == 'nt'` branch. Evidence sources:
  - **`process_start`:** the absolute process creation time from `GetProcessTimes` (FILETIME, 100 ns since 1601 UTC). It is immutable for the life of the process object and, unlike Linux `starttime` ticks, unique across boots.
  - **`boot_id`:** `BootTime - BootTimeBias` from `NtQuerySystemInformation(SystemTimeOfDayInformation)`.
    - Raw `BootTime` was rejected because it moves whenever the wall clock is stepped. On this host it had already been shifted by `BootTimeBias = -20672530` (-2.07 s) since boot. A spurious boot change would let a live owner's lock be reclaimed.
    - The bias-corrected value equals WMI `Win32_OperatingSystem.LastBootUpTime` exactly (both `2026-09-24T12:28:36.5000000Z` on this host) and did not change across about 17 h of sleep (`SleepTimeBias`). Like Linux `boot_id`, it is constant for the kernel session, including across a Fast Startup (hybrid) restart, where hibernated session-0 services keep their PIDs.
    - Two consecutive reads must agree, so a read torn by a concurrent clock step cannot surface. If the call fails, the kernel omits the bias field, or reads never agree, the result is `unknown` and the lock fails closed as before.
  - The registry `PrefetchParameters\BootId` counter and the System process (PID 4) creation time were also considered and rejected. It is unclear whether `BootId` stays constant within a kernel session (writer and timing unknown, hybrid boots uncertain). PID 4 is not queryable without elevation (`OpenProcess` → error 5).
  - Verified the lock tests pass for the right reason, not through an invalid record:
    - a live old owner has a valid record and is refused because it is alive with matching identity;
    - a fresh dead owner has a valid record and is refused on age;
    - a stale dead owner is reclaimed on positive death evidence.
  - `_boot_identity()` returned the same value across 50 reads.

## Platform skips

| Test | Condition | Justification |
|---|---|---|
| `tests/test_process_identity.py::test_linux_provider_has_current_identity` | `sys.platform == "win32"` | It instantiates `LinuxProcProcessIdentityProvider` directly, which reads `/proc/sys/kernel/random/boot_id` and `/proc/<pid>/stat`. Those don't exist on Windows. The Windows default provider's availability is still asserted by `test_v25_recovery_lock_identity.py::test_owner_is_versioned_and_fingerprinted` (`boot_id != 'unknown'`, `process_start != 'unknown'`). |

No test was deleted and no assertion was changed or weakened.

## Linux equivalence

- D1 appends `and os.name != 'nt'` to existing conditions; on Linux that is the constant `True`, so every condition evaluates exactly as before.
- D2/D3 branches are all guarded by `os.name == 'nt'` and placed before the unchanged POSIX code.
- `default_process_identity_provider()` still checks Linux `/proc` first. Other POSIX systems still get the base UNAVAILABLE provider.
- The new Windows helpers import `ctypes` lazily inside `_windows_api()`, so importing `process_identity` or `recovery_lock` on Linux loads nothing new beyond `os`.
- The skip marker is inert off Windows.

## Audited suspects that are not defects (unchanged)

- **Newline translation:** every hashed or canonical record is written in binary (`'wb'`/`'xb'`/`'ab'`). Two text-mode writers (`CrashReconciledGovernanceStore._write_payload`, `AnchoredCheckpointImporter.admit`) and the loop's event journal (`InfrastructureSupervisoryLoop._journal`) produce JSON that is read back only through `json.loads` and never hashed as bytes.
- **Locale encoding:** every canonicalizer uses `json.dumps` with the default `ensure_ascii=True`, so on-disk records are pure ASCII and `read_text()` without an explicit encoding (cp1252 on Windows) decodes them exactly.
- **Path separators:** the only stored path (`StartupRecoveryPolicy` / `RecoveryDecision` `journal_path`) is produced by `str(Path)` on the same host that verifies it.
- **`O_EXCL` lock creation and `os.replace` of a closed target:** both work on Windows (exercised by the passing suite).

## Residual platform differences (not exercised by the suite; documented, not changed)

1. **Rename durability window on Windows:** with directory fsync skipped, `os.replace` (MoveFileExW without `MOVEFILE_WRITE_THROUGH`) can return before the rename reaches disk. File contents are still fsynced first. After a power loss the rename may be lost, leaving the kind of "entry written, head older" state the crash-reconciliation and fail-closed verification paths already handle. This is a durability difference, not a relaxed check.
2. **`os.replace` over a file another handle holds open fails on Windows:** verified: `PermissionError`, winerror 5. CPython opens files without `FILE_SHARE_DELETE`. A verifier in another process reading a HEAD at the moment of an append makes that append raise, and the loop fails closed (no restore, no advance). This is an availability limit under concurrency, not a safety one.
3. **PID low-bit aliasing:** Windows ignores the low two bits of a PID (verified: `OpenProcess(pid+1)` opens `pid`). Liveness and identity queries both resolve the same way, so they stay mutually consistent. A forged record with a non-multiple-of-4 PID can only look alive (conservative).
4. **`NtQuerySystemInformation` layout:** `SYSTEM_TIMEOFDAY_INFORMATION` is only partially documented. Any failure yields `unknown` and the lock fails closed.

## Changed functions

- `process_identity.py`:
  - `import os` added.
  - New: `_windows_api`, `windows_pid_definitely_dead`, `windows_process_start_identity`, `windows_boot_identity` (with its inner `read`), `WindowsProcessIdentityProvider` / `.current`.
  - Modified: `default_process_identity_provider` (Windows branch after the unchanged Linux branch).
- `recovery_lock.py`: the import line, `_boot_identity`, `_process_start_identity`, `RecoveryChainLock._pid_definitely_dead`.
- Directory-fsync guard (D1):
  - `recovery_asymmetric.py`: `RecoveryTrustRootManifest.write`
  - `recovery_atomic_witnessed_provenance.py`: `AtomicWitnessedProvenanceStore._write`, `AtomicWitnessedProvenanceStore._unlink`
  - `recovery_authority_governance.py`: `AuthoritySetStore._write_atomic`
  - `recovery_authority_transaction.py`: `_write`, `CrashReconciledAuthoritySetStore._finish`
  - `recovery_chain.py`: `AppendOnlyRecoveryChain.append`
  - `recovery_checkpoint.py`: `AtomicRecoveryCheckpointStore.write`
  - `recovery_equivocation_ledger.py`: `EquivocationEvidenceLedger._write`
  - `recovery_governance_state_machine.py`: `GovernanceTransactionJournal._write`
  - `recovery_key_policy.py`: `_atomic_write`, `RecoveryKeyPolicyStore.append`
  - `recovery_provenance_index.py`: `ProvenanceIndex._write`
  - `recovery_remote_head_chain.py`: `SignedRemoteHeadChain._write`
  - `recovery_transaction.py`: `_atomic_write`
  - `recovery_trust_root.py`: `_atomic_write`, `RecoveryTrustRootStore.append`
  - `recovery_witness.py`: `_atomic_write`
  - `recovery_witness_governance.py`: `_atomic_write`, `TransparencyCheckpointStore.append`, `WitnessGovernanceStore.append`
- `tests/test_process_identity.py`: `import sys, pytest`; `skipif` marker on `test_linux_provider_has_current_identity`.
