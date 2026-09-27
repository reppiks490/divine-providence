# DAEDALUS Research OS

DAEDALUS is an isolated market-research operating system designed to sit beside Icarus, not inside its execution path.

Its purpose is to discover candidate relationships, model them without look-ahead, attack them adversarially, preserve experiment memory, detect regime/drift fragility, and export only research candidates that survive explicit local and corpus-level gates.

## Core principles

1. **Every source is provenance-bearing.** Similar filenames are never merged merely because they share a symbol or suffix.
2. **Chart construction is observed, not guessed.** Cadence, repeated/fractional timestamps, OHLC geometry, gaps, and volume behavior are profiled. Exact-byte duplicates may share compute, but remain separately catalogued.
3. **Features are causal by construction.** The complete predictor matrix is lagged before target construction.
4. **Development and protected evidence are different assets.** Feature discovery, model-family comparison, ensemble membership/weights, regime thresholds, and feature ablation are frozen on development data before a protected tail is exposed.
5. **Validation is purged and embargoed.** Target overlap is separated from later validation blocks explicitly.
6. **Discovery is corrected for multiple testing.** Feature/interactions use Benjamini-Hochberg FDR; corpus candidates receive another global FDR layer after budgeted holdout tests.
7. **Every edge is attacked.** Frozen predictions face serial-structure-preserving permutation tests, moving-block bootstrap, cost/threshold surfaces, temporal segments, development-only feature ablation, ensemble disagreement, drift checks, and development-defined regime-conditioned holdout diagnostics.
8. **Protected holdouts are budgeted at corpus scale.** Hundreds of locally interesting files do not automatically consume hundreds of pristine tails.
9. **No production authorization.** Candidate manifests are research-only and hard-code `production_authorized: false`.
10. **No writes into Icarus.** Integration is a separate explicit promotion/review step.

See `docs/HANDOFF_TO_WORK.md` for placement and operating instructions.

## Safe operating sequence

```bash
pip install -e .
pytest -q
python scripts/audit.py

daedalus catalog /ABSOLUTE/PATH/TO/DATA --output artifacts/catalog.csv
# development-only, resumable, no protected holdouts spent
daedalus batch /ABSOLUTE/PATH/TO/DATA --project-root . --limit 20
# two-phase corpus protocol: development screen -> holdout budget -> global FDR
daedalus research-corpus /ABSOLUTE/PATH/TO/DATA --project-root . --limit 20
```

Remove `--limit` only after the authoritative Work/repo root returns the expected corpus size and representative pilots have passed.

Useful diagnostics:

```bash
daedalus meta --registry artifacts/experiments.sqlite3
daedalus cross-asset source_A.csv source_B.csv --max-lag 10
daedalus identity-scaffold /ABSOLUTE/PATH/TO/DATA --output config/source_identity.csv
```

For alternate chart representations whose prices should **not** be treated as execution prices, use `research-fusion`: choose one execution-safe OHLC stream for target/PnL and align representation features strictly backward in time.

## Next system / continuation

For the proposed whole-stack supervisory layer, see `docs/ATHENA_SUPERVISORY_FABRIC.md`.
For exact continuation instructions and known unfinished release work, see `docs/NEXT_MODEL_HANDOFF.md`.
