# Run 007 Self-Review

Fresh reviewer unavailable in this runtime; this is an author self-review and is weaker than an independent review.

## Findings

### Important — contradictory lifecycle events at identical `known_at`
Current lookup orders same-time events by `event_id`, which is deterministic but semantically arbitrary. If two different lifecycle statuses are recorded for the same proof at the same knowledge boundary, JANUS could choose one silently. This must be quarantined or rejected before Run 007 is called complete.

### Minor — adjudication logic duplicated
`temporal_conflicts_as_of()` repeats the authority/evidence policy logic used by `temporal_conflicts()`. Tests currently pin both behaviors, but a future policy change could drift. Defer refactor until a dedicated policy object/helper is justified.

### Minor — replacement-chain semantics are recorded, not validated
`superseded_by` is preserved but replacement existence/cycle validation is intentionally deferred.

## Fix pass

The Important same-boundary ambiguity was fixed with `test_proof_lifecycle_rejects_conflicting_same_knowledge_boundary`: RED (no `ValueError`) → GREEN after rejecting conflicting `(status, superseded_by)` values at the same `(change_id, known_at)` boundary. Full suite subsequently passed 30/30.
