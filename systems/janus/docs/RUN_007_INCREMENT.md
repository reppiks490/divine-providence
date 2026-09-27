# JANUS ∞ Run 007 — Temporal Conflict Replay + Proof Lifecycle

Run 007 makes proof validity and conflict reconstruction knowledge-time aware. Proof bundles remain immutable; an append-only `proof_lifecycle_events` ledger records `proved`, `integrated`, `revoked`, and `superseded` transitions with actor, reason, and `known_at`. Verification can therefore answer whether a bound proof was valid at a historical knowledge boundary instead of applying its latest status retroactively.

`temporal_conflicts_as_of(valid_at, known_at)` now reconstructs the conflict surface at an explicit bitemporal coordinate. It selects only facts known by `known_at`, applies only normalization overlays whose decisions and proof lifecycle are valid at that same boundary, evaluates interval membership at `valid_at`, and then applies the existing authority-first/evidence-second resolution policy. Results carry blast radius and normalization lineage. The archival `temporal_conflicts()` detector is unchanged.

The proof lifecycle ledger participates in state digests and handoff export/import, so historical replay semantics survive transfer. Unknown proof targets fail explicitly. Revocation and supersession affect only boundaries at or after their recorded knowledge time.

Safety invariant: later proof invalidation must never rewrite what JANUS was justified in believing at an earlier knowledge boundary, and no lifecycle event mutates the original proof bundle.
