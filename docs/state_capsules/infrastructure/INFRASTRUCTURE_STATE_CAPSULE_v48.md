# Infrastructure STATE CAPSULE v48

Authoritative checkpoint: Infrastructure Supervisory Loop V48.

Artifact: `infrastructure_supervisory_loop_v48.zip` SHA-256:
`f0e904ea07959abf92ba8eff9956efff1928407703a4028fe73f04aa72f84132`
Parent V47 SHA-256:
`c52eb5b64cb0d169a9e861a62dfc7d966c0514aff5c78085910e9668824561a4`

## Completed

V48 adds `ProvenanceIndex`, a durable append-only predecessor-linked and
HEAD-bound index connecting each witnessed remote-history-head admission
to the exact signed remote-head-chain entry and the independent observer
gossip receipt that witnessed it. Admission verifies the underlying
signed-head chain, observer receipt, exact remote-head hash, and exact
chain-entry hash before persistence. Reopen verification repeats those
checks rather than trusting stored validation state. Duplicate
provenance, receipt/head substitution, entry tamper, underlying
remote-head-chain tamper, and HEAD rollback fail closed.

All V48 surfaces remain evidence/supervisory-safety mechanisms only and
grant no infrastructure mutation, promotion, routing, lease, sibling
semantic, or live-trading authority.

## Verification

V47 parent SHA-256 verified exactly. V47 baseline: 336 passed. TDD RED
observed for missing `recovery_provenance_index`. Focused V48 suite: 5
passed. Full development suite: 341 passed. Fresh extracted package: 341
passed. `python -m compileall -q .`: PASS. ZIP compressed-data
integrity: PASS.

## Interfaces

New `recovery_provenance_index.py`: `ProvenanceIndex`,
`ProvenanceIndexVerdict`. New contract
`docs/v48-durable-provenance-index.md`. README updated. No new
third-party dependency.

## Capability status/tools

First-party Deep Research: NO --- unavailable in exposed capability
inventory. Installed skill inventory: empty. Actually used: capability
inventory, skills inventory, persistent File Library retrieval,
container/Python engineering, pytest, compileall, clean ZIP
extraction/integrity verification, SHA-256, artifact generation.

## Risks

V48 persists exact head/receipt provenance but does not yet atomically
co-commit provenance with the underlying signed-head-chain append; a
crash after head append and before provenance append leaves a detectable
but unindexed head rather than silent false provenance.
EquivocationEvidenceLedger records do not yet contain direct
provenance-index entry hashes for both conflicting heads. Syscall-level
failpoints inside transition/TXN atomic rename/fsync/unlink sequences
remain incomplete. External gossip/public-log transport, HSM/PKI
custody, positive OutcomeMemory restoration, distributed operational
mutation events, and production staged-canary evidence remain outside
scope. READY_TO_COMMIT remains false for production/live adoption.

## Next

V49: make witnessed-head append + provenance-index append
crash-reconcilable with a durable intent/journal; bind
equivocation-ledger entries to both provenance-index hashes; add restart
tests for head-written/provenance-missing and provenance tamper;
continue deeper syscall failpoint coverage.

## Exact resume

Verify V48 SHA exactly
`f0e904ea07959abf92ba8eff9956efff1928407703a4028fe73f04aa72f84132`;
clean extract; require 341 tests plus compileall; preserve V3-V48
evidence-only authority boundaries; RED/GREEN V49 atomic
witnessed-head/provenance reconciliation + evidence provenance linkage;
package/hash/capsule without overwriting V48.
