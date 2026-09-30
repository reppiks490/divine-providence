# Next Task

## Turn State
- state: checkpointed / resumable
- last agent: GPT-5.6 Sol
- next agent: shared / next available coding-research agent
- updated: 2026-09-25
- canonical loop state: v1.11.0 / iteration 0024
- production authorization: false

## Read first
1. `artifacts/advanced_csv_loop/CURRENT_RESEARCH_STATE.json`
2. `artifacts/advanced_csv_loop/loop_state.json`
3. `docs/NEXUS_DAEDALUS_VALIDATION_BRIDGE.md`
4. latest iteration artifacts under `artifacts/advanced_csv_loop/iteration_0024/`

## Highest-value continuation
1. Recover missing CSV/ZIP batches by raw/content hash. Current coverage is 238 streams / 1,970,753 rows versus the historical 626 / 12,588,290 anchor; do not claim full coverage.
2. Work the 44 P0 representation-evidence clusters using authoritative vendor/source/export-setting evidence. There are 92 unresolved P0 streams; never infer bar-open/bar-close/event-completion semantics from filename/cadence alone.
3. Keep the 13 behavioral candidates development-only until genuinely unseen appended bytes or a reviewed independent non-overlapping source arrives. Use the DAEDALUS future-evidence readiness gate before any confirmatory evaluation.
4. The fixed-cadence/session blocker is closed: 53/53 session-semantic candidates are resolved at that layer. Do not reopen this work without new evidence.
5. Residual open-session gaps are diagnostics only: 28 activity-dominant, 10 mixed, 11 shared-silence, 1 insufficient sibling evidence. Never turn them into automatic data-loss claims.
6. Preserve subsystem ownership: NEXUS=data/evidence fabric, DAEDALUS=scientific validation, ARGUS=microstructure truth, ATHENA=supervision, AION=memory, Icarus=execution.

## Verification before architecture changes
- `PYTHONPATH=src pytest -q -o addopts=''` in NEXUS: require 144 passed or better.
- `python -m compileall -q src tests`.
- DAEDALUS: require 58 passed or better and rerun `scripts/audit.py`.
- If the corpus and loop version are unchanged, require `same_corpus_reproducible=true` and `unexpected_nondeterminism=false`.

## Superseding next task — 2026-09-30

Do **not** spend the next cycle searching for the old 626/800-file corpus gap.
The ten historical ZIPs are recovered and independently reconciled.

Current verified baseline:

- 10 ZIPs
- 659 usable archive members
- 13,788,256 logical rows
- 542 distinct byte contents
- 803 extracted physical CSV files mapping to the same 542 contents
- NEXUS CI: 169/169 passed
- representation contract: v1.18
- production authorization: false

Highest-value continuation:

1. Consume the O14 representation probe and bind only mathematically proved
   standard/Heikin-Ashi identities.
2. Keep unresolved TPO/footprint/session-profile/Renko identities fail-closed
   unless exact export/vendor evidence exists; do not infer them from column
   names alone.
3. Build the O14 gap matrix from the recovered corpus and request only genuinely
   missing cells: named expiries/roll metadata, micro contracts, session
   metadata, and missing required timeframes.
4. Keep chart family and tick/range/time sampling as separate axes through all
   joins, replay, ablation and model inputs.
5. Preserve DAEDALUS holdout/selection-contamination rules and all existing
   production gates.

The 238-stream `Full csv candles only.zip` subset remains useful as the
known-standard reference plane, but it is not the complete corpus.


### 2026-09-30 fourth-pass identity hardening

Price geometry is not treated as chart/view identity. Exact standard-OHLC or
Heikin-Ashi transform matches can prove geometry, but they cannot by themselves
distinguish an ordinary candlestick view from a TPO/footprint/profile view that
preserves that geometry. The canonical representation contract is therefore
four-axis: **chart/view family, price geometry, sampling domain, sampling
construction**. Family-specific modeling remains fail-closed without reviewed
view identity. Current GitHub Actions verification: **169/169 tests passed** and
`python -m compileall -q src tests scripts` passed.
