# NEXUS Advanced CSV Research Loop v1

## Purpose

The loop adds resumable research orchestration above the existing NEXUS v0.3 forensic, integrity, representation, lineage and sibling contracts. It does **not** replace NEXUS primitives, infer authoritative clock semantics, statistically promote candidates, or authorize execution.

Each iteration performs:

1. ZIP-native content-addressed cataloging of every accessible CSV member.
2. Non-authoritative representation hypothesis triage consistent with extracted-corpus cataloging.
3. Default NEXUS integrity assessment and duplicate-safe factor-universe selection.
4. Full-stream descriptive sweep using sequential-only calculations: log-return moments, lag-1 return correlation, sign persistence, path efficiency, normalized OHLC range, cadence-gap sensitivity, first/second-half volatility shift and volume coverage.
5. Representation review queue regeneration.
6. Research-candidate generation for corpus recovery, representation review, integrity blockers, representation-family disagreement, return persistence/reversal, regime volatility shifts and sampling-gap sensitivity.
7. Immutable per-iteration JSON artifacts with SHA-256 hashes plus a resumable `loop_state.json` checkpoint.
8. Delta comparison to the prior iteration corpus hash.

All behavioral discoveries are explicitly `descriptive_only=true`, `statistical_promotion_performed=false`, and `production_authorized=false`. Behavioral candidates must go through DAEDALUS chronological/walk-forward validation before any promotion discussion.

## Command

```bash
PYTHONPATH=src python -m nexus.cli loop-once <archive-root> --state-dir <state-dir>
```

Default historical reconciliation anchor is the PARALLAX ten-archive checkpoint: 659 usable archive members / 13,788,256 logical rows / 542 distinct byte contents across 10 ZIPs. The separate DAEDALUS extracted-corpus reconciliation observed 803 physical files with the same 542 distinct contents. The 803 physical count must not be compared directly to usable archive-member count.

## Iteration 0001 — 2026-09-23

Input archive SHA-256:

`dbdbfe9553fddc37c1bde95adf9458c5e192b411ff962b5df4b3074a0a81fd24  Full csv candles only.zip`

Observed corpus:

- 476 physical CSV members
- 238 AppleDouble/resource-fork sidecars
- 238 usable market streams
- 1,970,753 usable rows
- 174 admitted by default integrity policy
- 64 withheld by default integrity policy
- 167 selected duplicate-safe factor-universe streams
- representation review queue: 92 P0 / 146 P2
- 85 generated research candidates
- coverage claim remains **false**

Iteration hash:

`458f2cf2554b4630d995dacc745bc3dab489ac68b2c6cefccd28a88c72abd3e1`

## Candidate families in iteration 0001

- corpus recovery: 1 P0
- owner coverage gap: 1 P0
- representation review: 1 P0
- integrity rejections: 1 P0
- representation-family disagreement: 8 P1
- regime-volatility shift: 5 P1
- return persistence: 1 P1
- return reversal: 7 P1
- sampling-gap sensitivity: 60 P1

The candidate counts are discovery workload, not trading-edge claims. Sampling-gap candidates in particular require session/calendar decomposition before modeling.

## Iteration 0002 — 2026-09-24 — stability hardening

Loop code version 1.1.0 adds `stability_report.json` and compact stability fields in the iteration summary. On an unchanged corpus the loop now proves whether its six core research artifacts are byte-content deterministic and explicitly marks unexpected nondeterminism if any core artifact changes without a corpus change.

Real iteration 0002 results on the same master archive:

- corpus changed: false
- loop code changed: true (1.0.0 -> 1.1.0)
- same-corpus reproducible: true
- unexpected nondeterminism: false
- changed core artifacts: 0
- research candidates: 85 current / 85 persistent / 0 new / 0 resolved
- representation-review streams: 238 current / 238 persistent / 0 new / 0 resolved
- iteration hash: `8b94fe96946b8678330d1edd9d1be485f3f26479c704fdfec4df733f56f9377f`

The loose CSV uploads present in Library were also SHA-256 reconciled against the ZIP and are exact archive members, so they do not increase corpus coverage.

## Iteration 0003 — 2026-09-24 — portable resume state

Loop code version 1.2.0 makes checkpoint state portable across agent/container paths. `latest_iteration_dir` and `latest_summary_path` are now relative to `state_dir`; the current corpus location is retained only as `corpus_root_hint` and is not required for resume logic.

Real iteration 0003 again confirmed unchanged-corpus determinism:

- corpus changed: false
- same-corpus reproducible: true
- unexpected nondeterminism: false
- changed core artifacts: 0
- research candidates: 85 persistent / 0 new / 0 resolved
- representation-review streams: 238 persistent / 0 new / 0 resolved
- iteration hash: `74a935304fdae90f10bd71d3458da1a3b5b5f365367e304e9265a04d678570b7`


## Iterations 0004-0007 — contamination-aware validation handoff

v1.3 introduced `daedalus_validation_handoff.json`, which routes NEXUS discoveries without allowing NEXUS to become its own statistical validator. The key rule is selection-contamination awareness: because candidate discovery scanned all currently accessible rows, DAEDALUS may use that history only for development/retrospective diagnostics. It may not carve a post-hoc protected tail from the same files and call it independent confirmation.

Iteration 0005 proved the new handoff semantic content deterministic on an unchanged corpus. v1.3.1 then added each source's discovery raw byte size alongside SHA-256 so future append-only evidence can be verified by exact historical-prefix hashing. Iteration 0007 reproduced the v1.3.1 semantic hash on unchanged data.

Current routing:

- 13 behavioral hypotheses -> DAEDALUS development-only
- 60 sampling-gap candidates -> blocked pending calendar/session semantics
- 8 representation-family disagreements -> blocked pending representation identity/lineage
- 4 P0 evidence/integrity/corpus dependencies -> blocked upstream

No protected holdout has been spent and no production authorization exists.


## Representation-safe fusion contract

The corpus is multi-representation by design. Seconds/minutes/hours, tick, range,
Renko, Heikin Ashi, TPO, volume-footprint/profile and session-profile streams may
describe overlapping market state and therefore are not independent votes.

Loop v1.16 records non-authoritative representation claims and sampling domains
from explicit member/path/filename evidence. Tick (T) and range (R) suffixes are
event-driven construction claims, never fixed-time intervals. Profile-like
headers are schema tags and do not by themselves prove chart construction.

For modeling, use `HierarchicalFactorEngine.build_from_manifests`:

1. preserve each raw stream and lineage;
2. causally align only at valid native visibility boundaries;
3. fuse streams inside each reviewed representation family;
4. fuse the representation families to one symbol-level state;
5. retain family disagreement/agreement/coverage as diagnostics;
6. only then perform cross-asset weighting.

Unknown and `time_bars_unspecified` families fail closed by default so regular
candles and Heikin Ashi cannot be silently merged. Exact/logical duplicates may
share compute but receive no additional evidence weight. Missing observations
stay missing during representation consensus. Event-driven bars are never
assigned fictional minute/hour completion times.
