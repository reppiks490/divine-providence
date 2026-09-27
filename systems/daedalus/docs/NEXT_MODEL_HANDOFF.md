# NEXT AI MODEL HANDOFF — DAEDALUS RELEASE COMPLETION + ATHENA NEXT SYSTEM

## Read this first

You are inheriting a partially completed but working project named `daedalus-research-os`.

Do **not** restart from scratch. Do **not** collapse alternate chart representations. Do **not** weaken validation gates to make more candidates pass. Do **not** connect this package to live trading.

The user's authoritative market-data corpus is expected to contain **800+ real CSV files** in the Work/repo environment. The archive visible in the prior chat (`Full csv candles only.zip`) contained only 238 real data CSVs plus matching macOS metadata entries and is explicitly a subset, not the authoritative corpus.

Same-symbol/similar-filename files may represent different chart constructions. Treat them as distinct unless they are proven byte-identical. Even byte-identical files remain separate catalog records; only compute may be shared.

## Preferred repo layout

```text
<workspace-root>/
  Icarus/
  Icarus-engine/
  multi-level-csv/
  daedalus-research-os/
  athena-supervisory-fabric/   # future separate project; see ATHENA_SUPERVISORY_FABRIC.md
```

## Current DAEDALUS status at handoff

Verified in the current snapshot:

- Python package imports and runs.
- **45 / 45 tests pass** with numerical-library thread counts pinned.
- Static audit passes across **32 Python source files / 5,235 source lines**.
- Audit covers syntax/AST, duplicate fields/definitions, broad exception handling, mutable defaults, look-ahead/backfill/as-of risks, timestamp-dedup risks, dynamic/shell execution, unsafe pickle, unresolved markers, and production-authorization flags.
- Test coverage is currently approximately **79%**.
- Protocol v3 is documented and implemented.
- Protected holdout budgeting, ledgering, frozen ensemble evaluation, regime-conditioned diagnostics, corpus FDR, fusion, shadow book, and development-only batch behavior are present.

### Exact clean commands

Run from repo root:

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

pytest -q
python scripts/audit.py
pytest --cov=daedalus --cov-report=term-missing -q
```

The thread settings are important for deterministic/fast CI behavior; without them numerical libraries previously caused severe oversubscription and apparent hangs/timeouts.


## NEXUS integration checkpoint — 2026-09-24

A fail-closed NEXUS candidate bridge has been added without weakening Protocol v3. Current local verification is **56/56 tests passing** and the static audit is clean across **34 Python source files / 5,982 lines**. See `docs/NEXUS_INTEGRATION.md`.

The real NEXUS v1.3.1 / iteration 0007 handoff contains 85 candidates, of which 13 are routed to DAEDALUS development-only diagnostics. Retrospective block diagnostics report 8 direction-stable return hypotheses and 5 strong volatility-nonstationarity cases, but all remain selection-contaminated and unconfirmed. The future-evidence readiness gate reports 13/13 `WAITING_NO_NEW_BYTES`, so **no protected holdout has been spent and no candidate has independent confirmation**.

This integration does not resolve the pre-existing DAEDALUS release tasks below (including SQLite ResourceWarning cleanup and authoritative 800+ corpus validation).

## Known unfinished release work — do these before declaring DAEDALUS finished

### 1. Fix SQLite connection resource leaks

Coverage runs currently emit many `ResourceWarning: unclosed database` warnings.

Likely cause: the code frequently uses:

```python
with sqlite3.connect(path) as con:
    ...
```

Python's sqlite connection context manager manages commit/rollback but does not reliably serve as the desired explicit close lifecycle for this codebase.

Occurrences exist in at least:

- `src/daedalus/holdout.py`
- `src/daedalus/meta.py`
- `src/daedalus/registry.py`
- `src/daedalus/shadow.py`

Implement one canonical helper, preferably in `utils.py`, with explicit rollback/commit/close semantics:

```python
@contextmanager
def sqlite_connection(path):
    con = sqlite3.connect(path)
    try:
        yield con
    except Exception:
        con.rollback()
        raise
    else:
        con.commit()
    finally:
        con.close()
```

Adapt read-only uses as appropriate. Do not change database schema semantics unnecessarily.

Then run tests with ResourceWarnings escalated so leaks cannot recur:

```bash
pytest -W error::ResourceWarning -q
```

Add a CI/test configuration that catches future connection leaks.

### 2. Raise meaningful test coverage

Current total is ~79%, but several important orchestration surfaces have weak or zero direct coverage:

- `src/daedalus/cli.py` — 0%
- `src/daedalus/corpus.py` — 0%
- `src/daedalus/bridge.py` — 0%
- `src/daedalus/identity.py` — ~48%
- `src/daedalus/ensemble.py` — ~68%

Do **not** add trivial coverage-only tests. Add behavior/invariant tests.

Priority tests:

- CLI `catalog`, `batch`, `research-corpus`, `research`, `research-fusion`
- ensure `batch` cannot spend protected holdouts
- ensure `research-corpus` enforces holdout budget and diversity caps
- ensure `bridge.py` always exports `production_authorized=false`
- identity-scaffold roundtrip and validation
- ensemble membership/weight freezing before holdout
- error paths for missing/invalid configuration

A practical release target is >=90% for core orchestration modules and materially higher total coverage, but invariant quality matters more than an arbitrary global number.

### 3. Re-run protocol-v3 smoke tests on real data after resource fixes

Use scratch artifact paths and a scratch holdout ledger. Never contaminate the persistent ledger just to test code.

Use at least:

- one conventional time-based execution-safe source
- one variable-cadence or fractional/repeated-timestamp representation
- one fusion case with an explicit execution-safe anchor

Verify:

- repeated timestamps remain intact in standalone research
- backward timestamps fail or are surfaced rather than silently sorted
- fusion rejects ambiguous repeated-timestamp alignment unless ordering metadata exists
- execution/PnL remains anchored to the execution-safe source
- protocol-v3 regime diagnostic uses development-frozen thresholds
- weak sources die before protected holdout exposure
- corpus budget spends only the permitted number of tails
- global FDR is applied only to actually exposed protected tests

### 4. Validate against the authoritative 800+ corpus in Work

First command:

```bash
daedalus catalog /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --output artifacts/catalog.csv
```

**Stop if the count does not match the user's expected 800+ real CSVs.** Do not proceed on the 238-file chat subset and claim corpus completion.

Then:

```bash
daedalus identity-scaffold /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --output config/source_identity.csv

daedalus batch /ABSOLUTE/PATH/TO/AUTHORITATIVE/CSV/ROOT --project-root . --limit 20

daedalus meta --registry artifacts/experiments.sqlite3
```

Only after representative chart classes pass development-only pilots should `research-corpus` spend protected tails.

### 5. Final line-level audit after all changes

Re-run:

```bash
python scripts/audit.py
pytest -W error::ResourceWarning -q
```

Also manually inspect every changed source file for:

- accidental lookahead
- target leakage
- hidden row sorting/deduplication
- holdout reuse
- feature/model selection after holdout exposure
- direct live-order authority
- production authorization changes
- silent broad exception swallowing

Update `AUDIT_CHECKPOINT.txt` with the exact final counts and test commands.

### 6. Final Work delivery

The repo should remain a sibling project. Do not overwrite Icarus.

Final delivery should include:

- updated README
- architecture document
- handoff document
- test/audit results
- protocol version
- exact corpus catalog count
- exact commit/hash if Git is available in Work
- explicit statement that DAEDALUS has no live execution authority

## Important validation invariants that must not be broken

1. Feature/model discovery occurs only on development evidence.
2. Ensemble membership and weights freeze before protected-tail exposure.
3. Protected holdout exposure is recorded before evaluation.
4. Corpus protected tails are budgeted rather than automatically spent for every source.
5. Corpus-level FDR uses the actual protected tests.
6. Alternate chart representations are not assumed executable.
7. Fusion PnL/targets are anchored to an explicit execution-safe source.
8. Same-symbol files are not merged by filename similarity.
9. Repeated timestamps are preserved in standalone research.
10. DAEDALUS bridge manifests remain research-only with `production_authorized=false`.

## After DAEDALUS release completion: build ATHENA separately

Read `docs/ATHENA_SUPERVISORY_FABRIC.md` in full.

ATHENA should be a new sibling repository and must not be used as an excuse to modify DAEDALUS's protected-holdout protocol.

Recommended first ATHENA milestone:

### Phase 0 — interface contracts only

Implement schemas and tests for:

- DAEDALUS -> ATHENA candidate/evidence event
- DAEDALUS -> ATHENA drift/shadow health event
- Icarus -> ATHENA execution telemetry event
- ATHENA -> Icarus advisory state/risk/routing event
- event provenance / source lineage
- research vs shadow vs production data-plane labels

No ML and no live execution authority in Phase 0.

Exit only when contract/firewall tests prove the three data planes cannot be silently mixed.

## Do not do these things

- Do not train a giant transformer merely because it is more complex.
- Do not use synthetic data as proof of empirical edge.
- Do not optimize the system around historical net profit alone.
- Do not let ATHENA see a holdout outcome and then use that same outcome to tune the research design being judged by that holdout.
- Do not let ATHENA place live orders in its initial versions.
- Do not weaken DAEDALUS gates to generate more candidates for ATHENA.
- Do not treat the visible 238-file archive as the user's full data universe.

## Final philosophy

DAEDALUS should remain the skeptical scientist.

Icarus should remain the controlled executor.

ATHENA should become the state-aware supervisor that knows which validated capability fits the current world, how uncertain that judgment is, and when the safest decision is to abstain.
