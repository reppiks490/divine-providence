# V38 Crash-Reconcilable Composite Governance

V38 composes the signed witness-governance chain with the M-of-N governance-admission chain through a durable intent record. Quorum is verified before any component write. If a crash occurs after one component advances, `recover()` deterministically completes the matching second component from the signed epoch and approval bundle recorded in the intent. Recovery is idempotent. Verification requires both chains at the same epoch and the same epoch hash, and treats an unreconciled intent as fail-closed.

V38 also adds `AnchoredCheckpointImporter`, which admits received transparency checkpoints only when V36 freshness/anti-rollback policy passes and an independent transparency-anchor quorum verifies the exact sequence/hash. Partial quorum, stale evidence, rollback, and same-sequence disagreement fail closed.

These are evidence/persistence safety mechanisms only; they expose no infrastructure mutation, live-trading, sibling semantic, promotion, routing, or lease authority.
