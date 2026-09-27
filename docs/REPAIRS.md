# Repairs made during consolidation

Each entry: defect → root cause → fix → evidence. The original corpus is untouched;
before/after test runs are in `docs/VALIDATION.md`.

## R1 NEXUS: contract-drift sentinel reported byte-identical files as semantic changes
- **Defect:** `nexus.contract_sentinel.compare_contract_snapshots` flagged all five sibling
  boundaries (AION contracts/store, ARGUS, ATHENA, DAEDALUS) as `semantic_change` against the
  v0.3 release baseline, although AION/ARGUS/ATHENA are byte-identical to it (raw SHA-256 equal).
- **Root cause:** the semantic fingerprint is `sha256(ast.dump(...))`, and `ast.dump` output
  differs between Python versions. The baseline was captured on a newer interpreter; 3.10 and
  3.11 both produce a different dump for the same bytes.
- **Fix:** `semantic_changed = raw_changed and ast differs`. Identical bytes are identical code,
  and differing bytes are still judged by AST, which stays fail-closed.
- **Evidence:** new test `test_contract_sentinel_ignores_interpreter_specific_ast_for_identical_bytes`
  fails on the original code and passes on the fix. Drift now isolates the one genuine change,
  the additive DAEDALUS bridge, which was reviewed and re-pinned in R17.

## R2 NEXUS: `scripts/real_smoke.py` hard-coded `/mnt/data/nexus_build/...`
- Now takes the CSV root from argv[1] or `NEXUS_CSV_ROOT`, exits with usage text if absent,
  and creates `artifacts/` before writing.

## R3 NEXUS: missing v0.3 sibling-contract baseline
- PROMETHEUS pins release snapshot `1119ef3d…`, but the baseline file was not in the canonical
  archive. It was restored from an earlier NEXUS package into
  `systems/nexus/contracts/baselines/`; it self-verifies to `1119ef3d…`.

## R4 ORACLE: sibling tests hard-coded the original handoff workspace layout
- 6/34 tests failed with `ModuleNotFoundError: aion|argus|athena|daedalus`.
- Added `systems/oracle/tests/conftest.py`, which resolves the siblings from `systems/`.
  ORACLE runtime code still imports no sibling. Result: 34/34, with the sibling contracts
  validated against the real monorepo trees.

## R5 ASCENSION: placeholder test file
- `test_context_distillation.py` contained only a comment and collected zero tests.
  Replaced with 10 behavioural tests: required sections, canonical provenance digest,
  normalisation, dedupe scope, determinism, loss auditing of dropped/tampered/missing items,
  and rejection of records without `source_id`.

## R6 ASCENSION: five separately shipped kits unified
- One package directory. Overlapping modules were verified byte-identical and the assembler
  aborts on any conflict. Per-kit metadata lives in `kits/<kit>/`.
- 160 tests (the exact union 13 + 105 + 32 of the kit suites, plus R5). The 6,800-case
  conformance failure-injection run and the other property/hostile scripts were re-run
  (`dp validate`).

## R7 PROMETHEUS: two divergent v0.5 branches
- `experiment-router` (77 tests) and `attestation-lineage` (119 tests) forked at v0.3 and each
  had unique functionality. They were merged as `136563e2`:
  - the two different `lineage.py` modules are kept apart (`lineage` = staleness lineage,
    `provenance_lineage` = ancestry verification);
  - the promotion packet requires both bindings;
  - both CLI demos are kept.
- 156 tests: the full 150-ID union plus 6 new unified-gate tests. Details are in
  `systems/prometheus/docs/changes/2026-09-26-prometheus-v0.5-unified-merge.md`.

## R8 Infrastructure: Windows portability (38 failures → 0)
- **Directory fsync:** `os.open(dir)` is impossible on Windows and raised after the rename.
  It is now skipped on NT only (21 sites).
- **Liveness probe:** `os.kill(pid, 0)` is not a liveness probe on Windows, so dead lock owners
  could never be reclaimed. It now uses `OpenProcess`/`GetExitCodeProcess`.
- **Process identity:** there was none outside Linux `/proc`, so every lock refused and chains
  stayed empty. Added `WindowsProcessIdentityProvider` (process creation time; bias-corrected
  boot time).
- **Evidence:** 344 passed + 1 Linux-only skip. Linux paths are unchanged by construction.
  Full record: `systems/infrastructure/WINDOWS_PORTABILITY_REPAIRS.md`.

## R9 Hub: MCP SDK 2.x
- `mcp` 2.x renamed `FastMCP` to `MCPServer`. The server imports the 2.x name and falls back
  to 1.x. A stdio handshake test guards it.
- Note: `icarus-bridge/icarus_bridge/mcp_server.py` (outside this repo, left untouched) still
  imports `mcp.server.fastmcp` and will fail if its environment upgrades to `mcp` 2.x.

## R10 SuperMesh-X: cross-runtime conformance preserved from the divergent v3.7 variant
- `supermesh_x_v3_7_0_cycle7_final.zip` is a second v3.7 branch. Its trusted-time design
  (`trusted_time_policy.py`, policy-freshness checks inside `durable_gossip_journal.py`)
  conflicts with FINAL2's (`trusted_time.py`, compaction snapshots), so it was not merged.
- Its independent Node.js conformance check was ported: `conformance/v37_anchor_fixture.json`,
  `scripts/verify_v37_fixture.mjs` and `tests/test_non_python_conformance_v370.py`. Node
  re-canonicalises the statement, matches Python's `canonical_json_bytes` byte-for-byte and
  verifies the Ed25519 signature. This is the handoff's stated "v3.8 cross-runtime
  canonicalization" direction.
- Evidence: full suite 352 passed (FINAL2's 351 + 1). The test skips only if `node` is absent.

## R11 JANUS: Windows portability (39 failed + 31 errors → 0)
- **Leaked integrity-probe connections (production):** `probe=sqlite3.connect(...)`, then
  `execute(...)`, then `close()`, skipped `close()` whenever `PRAGMA integrity_check` raised,
  which is exactly the corrupted-stage path. The open handle blocked the stage unlink on
  Windows (34 `PermissionError`s and 31 teardown errors). Fixed at all three probe sites with
  `contextlib.closing`; the result strings are unchanged.
- **Crash-injection tests:** these used `signal.SIGKILL` (absent on Windows) and killed the
  venv launcher stub instead of the interpreter holding the database, so children were
  orphaned forever at `hard_wait_at`. On Windows the test now terminates the real interpreter
  PID with `TerminateProcess` and asserts the propagated exit code. The POSIX path is
  unchanged, and a `finally` reaper guarantees no child can outlive a failed assertion.
- **Platform skips:** three kernel-`RLIMIT` probe tests are skipped on Windows only (no
  `resource` module or `/dev/null`); on Windows the production probes already fail closed.
- **Evidence:** 140 passed + 4 skipped on 3.11 and 3.10. Record:
  `systems/janus/WINDOWS_PORTABILITY_REPAIRS.md`.

## R12 AION: test leaked a SQLite handle (fails only on Python 3.11)
- `with sqlite3.connect(...) as db:` only ends the transaction and never closes. The tracebacks
  kept by `assertRaises` held the connection past temp-dir cleanup on 3.11. Now uses
  `contextlib.closing`. Evidence: 11/11 on 3.11 and 3.10. Production code already closed correctly.

## R13 SuperMesh-X: production SQLite connection leak (9 failures on Python 3.11)
- `SQLiteIsolationAdmission` and `SQLiteDurableRunStore` used `with self._connect() as conn:`
  at 14 sites, and each call leaked a handle. Added `_ClosingConnection(sqlite3.Connection)`,
  whose `__exit__` keeps the stock commit/rollback and then closes, passed via
  `factory=`. Every query at those sites already materialises its results inside the block.
- Evidence: 352/352 on 3.11 and 3.10.

## R14 Bootstrap: PowerShell swallowed the `--` separator
- A bare `--` is PowerShell's end-of-parameters token when calling the `claude.ps1` shim, so
  `claude mcp add ... -- python -m ...` failed with `unknown option '-m'`. It is now quoted
  (`'--'`). The `claude mcp remove` pre-step also no longer aborts on a first install:
  PowerShell 5.1 promotes native stderr to a terminating error under `Stop`.

## R15 Validator: no bytecode written into subsystem trees
- The compile gate used `compileall`, which writes `__pycache__` into `systems/` regardless of
  `PYTHONDONTWRITEBYTECODE`. It now byte-compiles every file in memory (the same syntax gate)
  and writes nothing.

## R16 Line endings: byte-faithful git exports
- The machine-wide `core.autocrlf=true` checked out ORACLE (bundle clone) and PROMETHEUS
  (`git archive`) with CRLF, although their commits store LF. Both were re-exported with
  `core.autocrlf=false`; every file's `git hash-object` equals the commit tree blob
  (55/55 and 86/86). `.gitattributes` pins LF for the future repository.

## R17 NEXUS → PROMETHEUS reconnected under a reviewed contract pin (resolves the R1 follow-up)
- The only drift from the v0.3 contract PROMETHEUS pinned was the DAEDALUS bridge, and it
  is **additive only**: 166 lines added, none changed. The bundle's DAEDALUS payload
  (`SCHEMA_VERSION`, `export_candidate`) is unchanged.
- NEXUS: `ContractDriftSnapshot.capture(..., relative_to=...)` gives a path-independent
  baseline, which fixes the environment-dependent aggregate hash noted in PROMETHEUS ADR 0002.
  `save()` now writes LF on every platform. The recorded baseline
  `contracts/baselines/sibling_contract_drift_baseline.v1.15.monorepo.json` has identity `b394df6c…`.
- PROMETHEUS ADR 0004 pins `{v0.3, v1.15}`: v0.3 so historical bundles still replay, v1.15 as
  the current pin. Drift failures report the current pin. Five new tests cover
  bind + normalize of a fresh v1.15 bundle, v0.3 replay, quarantine of unpinned identities
  and rejection of `production_authorized`.
- Hub: the drift connection compares against the current pin and reports the v0.3
  comparison for history. `nexus-prometheus` supplies the identity only when there is no
  drift, and now yields normalized observations.
- Evidence: PROMETHEUS 161/161 and NEXUS 155/155 on 3.11 and 3.10; all 5 hub connections pass.

## R18 Independent review fixes (two code-reviewer passes, both APPROVE_WITH_NITS)
- **PROMETHEUS (MEDIUM):** the v0.3 identity now binds only recorded historical bundles
  (`HISTORICAL_V03_BUNDLE_HASHES`), so a fresh bundle can never be recorded against the
  historical contract. New test; 162/162 on 3.11 and 3.10. ADR 0004 and `CLAUDE.md` updated.
- **Hub gates (MEDIUM):**
  - `nexus-prometheus` has an explicit `link_state` (LINKED / QUARANTINED_AS_EXPECTED / BROKEN).
    `ok` means LINKED with all four siblings and the fail-closed tiers. On drift it presents the
    live snapshot identity, so PROMETHEUS's real refusal path is exercised.
  - `dp validate` exits non-zero when any connection fails.
  - `run_json_driver` rejects non-zero exits, timeouts and non-record output.
  - Suite runs strip `PYTEST_ADDOPTS`/`PYTHONOPTIMIZE`/… and treat deselected tests as failure.
- **MCP surface (MEDIUM):** `read_system_doc` rejects drive, root, UNC, `..` and `:` (NTFS
  streams) lexically **before** any filesystem call; before this, a UNC path would open an SMB
  connection. `max_chars` is bounded.
- **LOW items fixed:**
  - `run_system_tests` timeout clamped and serialized per system.
  - Engine symbols validated (`[A-Za-z0-9!_-]{1,20}`).
  - Bearer token only on research routes, via an unredirected header.
  - `prometheus-ascension` compares exactly against PROMETHEUS `_REQUIRED_CHECKS`.
  - `nexus-oracle` checks the packet contract and every feature value.
  - Stale hint and contract texts fixed.
  - Bootstrap scripts: explicit `-Python` paths with spaces, `py`-missing tolerance, pip exit
    check, caller directory restored, unknown flags rejected, Git Bash venv layout.
    `claude mcp list` replaces `mcp get`, which printed the token.
  - `.gitignore`: more key/cert/env/journal/archive/media patterns.
  - Hub `requires-python >=3.11`.
- **Also fixed:**
  - The JANUS crash-test PID handshake is now bounded (`_read_child_pid`, 30 s), so a stalled
    child fails the test instead of hanging it.
  - SuperMesh `_connect()` closes the connection if a PRAGMA fails, a pre-existing leak.
- **Not changed (noted):**
  - The JANUS error-path close-before-hash ordering, which only affects a corrupted-DB diagnostic.
  - Subprocess grandchildren on timeout (Windows Job Objects).
  - The NEXUS snapshot not recording the Python version.
- **Evidence:** hub suite 37/37 (24 + 13 new tests, including a UNC/ADS no-I/O test);
  `bootstrap.ps1 -RegisterMcp` re-run end to end reports ✔ Connected.

## R19 Connection coverage: SuperMesh-X witness link; three systems confirmed standalone
- Two read-only explorers audited AEGIS, JANUS, Infrastructure and SuperMesh-X for existing
  cross-system contracts: imports, a repo-wide search in both directions, and every named
  module. None has a sibling contract in code. The AEGIS adapter registry is intra-AEGIS only.
- SuperMesh-X's `RFC9162WitnessedCheckpointLedger` is generic by design (opaque leaves,
  caller-chosen `log_id`, append-only / rollback / split-view invariants). New connection
  `supermesh-witness`:
  - The NEXUS instant bundle and the pinned contract baseline are checkpointed under a 2-of-2
    Ed25519 witness quorum.
  - `GossipReceiptStore` re-verifies signatures and consistency proofs independently.
  - A history rewrite is rejected ("RFC9162 consistency verification failed"), and so is a rollback.
- Infrastructure's schemas are closed to its own lifecycle (`proof_envelope.STAGE_ORDER` and the
  checkpoint and receipt fields), so recording foreign artifacts there would mislabel them. It
  stays standalone, as do AEGIS and JANUS. `connections.STANDALONE` records the evidence;
  `connections.coverage()` and the MCP tool `connection_coverage` report every system.
- Evidence: 6/6 connections pass; hub suite 39/39.
