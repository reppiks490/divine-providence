# JANUS Run 007 Implementation Plan

**Goal:** Add knowledge-time proof lifecycle and bitemporal conflict replay without changing raw archival conflict semantics.

**Architecture:** Extend the SQLite twin with an append-only proof lifecycle ledger. Thread `known_at` through proof verification and overlay verification, then add a point-in-time conflict surface that reuses the existing authority/evidence adjudication rules.

**Tech Stack:** Python 3 standard library, sqlite3, unittest.

**Spec:** `docs/RUN_007_DESIGN.md`

## Global Constraints
- Immutable source facts and proof bundles.
- Fail closed for unverified proof references, fail open for the JANUS process.
- No inferred subsystem authority.
- Preserve existing `temporal_conflicts()` behavior.

## Review Focus
- A proof revoked after K must remain valid when replaying an earlier K.
- A proof revoked before K must not activate a normalization overlay.
- Conflict replay must change only when knowledge-time-valid overlays change interval membership.
- Handoff import must reproduce proof lifecycle and state digest.
- Unknown proof lifecycle targets must fail explicitly.

### Task 1: Proof lifecycle ledger
**Files:** modify `src/janus_infinity/core.py`, `tests/test_janus.py`; create `schemas/proof_lifecycle_event.schema.json`.
**Produces:** `record_proof_lifecycle_event(...)`, knowledge-time-aware `_verify_proof_ref(...)`.
- [ ] Write failing lifecycle tests.
- [ ] Run focused tests and confirm expected failure.
- [ ] Implement schema/table/API/effective status.
- [ ] Run focused and full suite.

### Task 2: Bitemporal conflict replay
**Files:** modify `src/janus_infinity/core.py`, `tests/test_janus.py`; create `schemas/temporal_conflict_replay.schema.json`.
**Consumes:** verified overlays with proof lifecycle at `known_at`.
**Produces:** `temporal_conflicts_as_of(valid_at, known_at)`.
- [ ] Write failing replay tests.
- [ ] Run focused tests and confirm expected failure.
- [ ] Implement point-in-time conflict detection and lineage.
- [ ] Run focused and full suite.

### Task 3: Transfer and evidence
**Files:** modify handoff/status/docs; create Run 007 generated handoff and reports.
- [ ] Write failing round-trip test for lifecycle ledger.
- [ ] Implement export/import/digest participation.
- [ ] Run full suite and compile check.
- [ ] Generate seed status, handoff round-trip evidence, SHA-256 manifest, and ZIP.
