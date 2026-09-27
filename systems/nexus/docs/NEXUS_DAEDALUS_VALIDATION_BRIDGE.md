# NEXUS -> DAEDALUS Validation Bridge

## Purpose

NEXUS discovers descriptive research candidates; DAEDALUS owns chronological/statistical validation. The bridge prevents candidate-selection history from being mislabeled as a pristine protected holdout.

## Current contract

`nexus.daedalus-validation-handoff.v1` is emitted by every advanced CSV loop iteration.

Hard invariants:

- `production_authorized=false`
- `protected_holdout_spent=false`
- the full currently accessible source history was scanned before candidate selection
- no tail carved from those already-scanned files is pristine confirmatory evidence
- behavioral candidates may enter DAEDALUS development-only / retrospective diagnostics
- clean confirmation requires genuinely unseen evidence

For each behavioral candidate, the handoff records:

- candidate id/family/priority/score
- source stream ids and physical source evidence
- raw SHA-256 and raw byte size at discovery
- first/last event bounds and cadence metadata
- the per-stream discovery cutoff
- an explicit `UNSEEN_EVIDENCE_ONLY` confirmation rule

The raw byte size plus SHA-256 allow DAEDALUS to verify append-only future evidence: an updated source must preserve the exact historical byte prefix before any appended rows can be treated as unseen evidence.

## Iteration 0024 status — v1.11.0

- 78 total NEXUS research candidates
- 13 `DAEDALUS_DEVELOPMENT_ONLY` behavioral hypotheses
- 50 `SESSION_SEMANTICS_RESOLVED_OPEN_SESSION_DIAGNOSTIC` data-quality/no-trade diagnostics
- 3 `RESOLVED_RECURRING_SESSION_CLOSURE` canonicalizations
- 8 `RESOLVED_REPRESENTATION_COPY_LINEAGE` candidates
- 4 upstream `BLOCKING_DEPENDENCY` items
- 0 session-semantic blockers
- 0 representation-lineage blockers
- 0 protected-holdout-eligible tasks
- no protected holdout spent
- no production authorization
- handoff semantic hash: `31072d1f4924afd75391504922dd1b27d1cf8d52a48af16323608a89b0679c79`

DAEDALUS validates route-count consistency and fails closed if a resolved session diagnostic asserts data loss or if copy lineage is marked eligible for independent-view fusion. Existing discovery history remains development-only; confirmation still requires genuinely unseen evidence.
