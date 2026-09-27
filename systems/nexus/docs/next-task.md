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
