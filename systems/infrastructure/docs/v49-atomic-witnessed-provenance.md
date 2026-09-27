# V49 — Atomic Witnessed Head + Provenance Admission

`AtomicWitnessedProvenanceStore` crash-reconciles the V47 signed remote-head admission and V48 durable provenance index. It persists an integrity-bound TXN payload before either component mutation, verifies the independent observer receipt before PREPARED, and permits only the exact next remote-head sequence.

Recovery validates the TXN payload and receipt, detects whether the signed head and/or provenance record already exist, verifies exact object/hash agreement, writes only missing state, and removes TXN only after both components converge. A pending or tampered TXN fails closed; replay/gap and substitution fail closed. The store remains evidence-only and grants no mutation authority.

Failure boundaries covered: PREPARED, HEAD_WRITTEN (head exists/provenance missing), and PROVENANCE_WRITTEN (both durable/TXN still present). Recovery is deterministic and idempotent for each reachable state.
