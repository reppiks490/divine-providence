# V40 Journal-Integrated Governance Recovery

V40 integrates the V39 append-only transaction journal into the V38 composite governance coordinator. A governance transaction is admitted only after M-of-N approval verification, then progresses through PREPARED, GOVERNANCE_WRITTEN, ADMISSION_WRITTEN, and COMMITTED. The epoch plus approval bundle is retained as recovery payload until commit.

On restart, recovery verifies journal integrity, reconstructs the exact phase, validates payload/epoch-hash agreement, advances only the missing component, and commits only after governance and admission histories agree. Repeated recovery is idempotent. Pending or tampered journal state fails closed.

V40 remains evidence/persistence safety infrastructure only. It grants no execution, promotion, rollback, lease, routing, sibling semantic, or live-trading authority.
