# Current State

NEXUS v0.3 is a tested CSV-first, source-agnostic market-data fabric and sibling substrate.

Current verification: **117/117 NEXUS; AION 11/11; ARGUS 4/4; ATHENA 3/3; DAEDALUS 45/45 collected tests passed file-by-file**. Compileall, real five-market smoke and exact same-instant sibling validation pass.

v0.3 adds canonical atomic `ReplayInstant`, same-instant source-health/derivation routing, operational source SLO telemetry, immutable reviewed representation registry machinery, causal-transform certification, group ablation, deeply immutable factor genealogy, research-run manifests, appendable SQLite storage/source access and optional streaming partitioned Parquet.

The authoritative full corpus remains unresolved. Current accessible archive is 238 usable streams / 1,970,753 rows versus AION's older 626 usable / ~12.59M-row checkpoint. Full coverage must not be claimed.

Parquet code is implemented but **not runtime-validated here because pyarrow is absent**.


Latest SOL continuation adds canonical ReplayInstant routing, source-health persistence, contract-drift sentinel, and a deterministic 238-stream representation-review queue (92 P0).

## Advanced CSV research loop — added 2026-09-23

A resumable `nexus.research_loop` orchestration layer is now implemented above NEXUS v0.3 and exposed as `nexus loop-once`. Full test baseline is now **121/121 passed**. Iteration 0001 ran over `Full csv candles only.zip` and reproduced the sealed corpus counts: 476 physical CSV members, 238 usable streams, 1,970,753 rows, 174 default-integrity admissions, 64 withheld, 92 P0 / 146 P2 representation-review candidates. It emitted 85 descriptive/research-only candidates and a content-addressed checkpoint under `artifacts/advanced_csv_loop/`.

Iteration 0002 (2026-09-24) upgraded the loop with an explicit `stability_report.json`: core-artifact determinism, candidate persistence/new/resolved deltas, representation-review deltas and fail-visible unexpected nondeterminism. Iteration 0003 upgraded resume-state portability to loop code version 1.2.0 so iteration artifact paths are state-directory-relative rather than machine-specific absolute paths. Both unchanged-corpus replays reproduced all six core artifact hashes exactly: 85/85 research candidates persisted, 238/238 representation-review entries persisted, zero candidates/reviews were added or resolved, and `same_corpus_reproducible=true`. The separately uploaded loose CSV files in Library were also checked by SHA-256 and are exact members of the master archive, so they do not expand coverage.

Coverage remains unresolved and `production_authorized=false` everywhere in the loop.


## Validation bridge hardening — 2026-09-24

Advanced loop v1.3.1 / iteration 0007 adds a fail-closed NEXUS -> DAEDALUS validation handoff. Because NEXUS candidate discovery scanned the full accessible history, all current source rows are explicitly selection-contaminated and cannot later be relabeled as a pristine protected tail. The handoff routes 13 behavioral candidates to DAEDALUS development-only diagnostics, blocks 60 sampling-gap candidates on calendar/session semantics, blocks 8 representation-family disagreements on identity review, and keeps 4 upstream P0 dependencies blocked. Source evidence now carries discovery raw SHA-256 plus raw byte size so future append-only evidence can be verified by exact historical-prefix hash. Iteration 0007 reproduced the v1.3.1 semantic handoff hash on unchanged data with no unexpected nondeterminism.

The paired DAEDALUS receiver currently reports all 13 behavioral candidates as retrospectively stable/strong across chronological blocks, but none is independently confirmed. Its future-evidence gate reports `WAITING_NO_NEW_BYTES` for all 13 on the current corpus and touches no protected outcomes.

## Canonical latest continuation — 2026-09-25

- NEXUS advanced CSV loop: **v1.11.0 / iteration 0024**.
- Verification: **144/144 NEXUS tests passed**, unchanged replay is reproducible, `unexpected_nondeterminism=false`, and core artifact deltas are zero.
- Corpus remains partial: **238 usable streams / 1,970,753 rows** versus historical anchor **626 / 12,588,290**. Full coverage remains prohibited.
- Research queue: **78** candidates after removing 7 category-error sampling-gap hypotheses from event/transformed representations.
- Representation disagreement: **8/8 resolved as copy/snapshot lineage**; copies cannot vote independently.
- Session semantics: **53/53 fixed-time sampling-gap candidates resolved at the session-semantic layer; 0 blocked**. Three are recurring/coarse session canonicalizations; 50 remain open-session data-quality/no-trade diagnostics with `data_loss_asserted=false`.
- Residual gap triage: **28 cross-resolution-activity dominant / 10 mixed / 11 shared-silence dominant / 1 insufficient cross-resolution evidence**. This is diagnostic evidence only.
- P0 representation review: **92 unresolved**, compressed into **44 evidence clusters**: **47 event/transformed** requiring vendor representation definition and **45 timeframe-mismatch** requiring export/chart-setting evidence. `auto_resolved_count=0`.
- DAEDALUS receiver: **58/58 tests passed**, static audit passed across **34 source files / 6,022 lines**. It imports **13 development-only behavioral hypotheses**, with **0** session blockers, **0** representation blockers, and **0** protected-holdout-eligible tasks.
- Retrospective diagnostics remain 8 direction-stable + 5 strong nonstationarity cases, but **all 13 remain `WAITING_NO_NEW_BYTES` for confirmation**. No protected holdout has been spent and no production authorization exists.
- Canonical machine-readable state: `artifacts/advanced_csv_loop/CURRENT_RESEARCH_STATE.json`.

## Canonical current state — 2026-09-30

The historical archive-count gap is closed. The pinned source repos reproduce
the complete verified ten-archive checkpoint: **659 usable CSV members /
13,788,256 logical rows / 542 distinct contents**, reconciled with the
**803-physical-file / 542-content** DAEDALUS extraction checkpoint.

The earlier 238-stream state is now understood as the single
`Full csv candles only.zip` subset, not the whole accessible corpus.

NEXUS representation handling is now v1.17 and separates:

1. chart/view family (regular candles, Heikin Ashi, Renko, TPO, footprint,
   session profile, etc. when evidenced);
2. sampling domain/construction (time, tick, range);
3. native setting/timeframe;
4. instrument/symbol/venue identity.

Representation-sensitive fusion is
`stream -> sampling construction -> chart family -> symbol -> cross-asset`.
Unknown chart family or sampling construction fails closed rather than being
guessed. The latest GitHub Actions baseline is **161/161 passed**.

Remaining work is evidence reconciliation, not bulk CSV recovery: resolve only
the genuinely unknown chart-family/export settings, named expiries and roll
metadata, micro-contract tapes, sessions/entitlements, and missing required
matrix cells. Production authorization remains false.
