# ICARUS CSV Research — All Current Work

Snapshot date: 2026-09-24

This is the post-continuation recovery bundle. It contains both the NEXUS discovery/orchestration side and the DAEDALUS receiving/validation side.

## NEXUS state

- Advanced CSV loop: v1.3.1
- Latest real iteration: 0007
- Accessible corpus: 476 physical CSV entries, 238 usable streams, 1,970,753 rows
- Default integrity: 174 admitted / 64 withheld
- Research candidates: 85
- Candidate stability on unchanged corpus: stable
- Validation handoff routes:
  - 13 DAEDALUS development-only behavioral hypotheses
  - 60 blocked pending calendar/session semantics
  - 8 blocked pending representation identity/lineage
  - 4 upstream evidence/integrity/corpus blockers
- Protected holdout spent: false
- Production authorized: false
- Tests: 121/121 passed

## DAEDALUS integration state

- NEXUS handoff receiver is fail-closed.
- Current NEXUS-scanned history is explicitly selection-contaminated and cannot be relabeled as a pristine protected tail.
- Retrospective chronological block diagnostics:
  - 8/8 lag-direction candidates direction-stable
  - 5/5 volatility-shift candidates strong blockwise nonstationarity
- These are prioritization/stability results, not independent confirmation.
- Future-evidence readiness gate uses discovery raw SHA-256 + raw byte size to require exact append-only historical-prefix continuity before unseen rows can unlock confirmatory evaluation.
- Current readiness: 0 ready; 13 WAITING_NO_NEW_BYTES.
- Protected outcomes touched by readiness scan: false
- Protected holdout spent: false
- Production authorized: false
- Tests: 56/56 passed
- Static audit: passed across 34 source files / 5,982 source lines

## Evidence files

`evidence/daedalus_validation_handoff.json`
- canonical NEXUS -> DAEDALUS routing/provenance contract

`evidence/nexus_handoff_ingest_summary.json`
- DAEDALUS receiver summary for the real handoff

`evidence/nexus_retrospective_diagnostics.json`
- development-only blockwise stability diagnostics

`evidence/nexus_confirmation_readiness.json`
- future unseen-evidence readiness state

## Reproduction note

The raw market-data ZIP is not duplicated inside this source/work bundle. Its SHA-256 is recorded in `SOURCE_CORPUS_SHA256.txt`. Supply the exact source archive when reproducing real corpus iterations.

## Remaining high-priority work

1. Recover the missing historical CSV corpus; current data remains far below the historical 626-stream / 12,588,290-row anchor and the owner's roughly 800+ file expectation.
2. Resolve the 92 P0 representation/timestamp/identity reviews with source/vendor evidence.
3. Resolve calendar/session semantics before interpreting the 60 sampling-gap candidates as data loss.
4. Wait for genuinely unseen appended evidence (or a separately reviewed independent non-overlapping source) before confirmatory validation of the 13 behavioral hypotheses.
5. DAEDALUS still has its pre-existing release tasks, including SQLite ResourceWarning cleanup and authoritative full-corpus validation; this integration does not falsely mark those tasks complete.
