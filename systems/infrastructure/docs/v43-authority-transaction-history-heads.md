# V43 Authority Transition Transaction and Signed History Heads

V43 wraps V42 recursive authority-set transition evidence and the underlying authority-set epoch write in a crash-reconcilable durable transaction payload. Previous-authority quorum is verified before PREPARED. Recovery revalidates payload integrity and predecessor quorum, writes only missing transition/authority state, verifies convergence, and is idempotent. Pending or tampered transaction state fails closed.

V43 also defines signed remote transparency history heads binding peer identity, sequence, record hash, observation time and signer key identity. Verification rejects signer substitution, signature tamper, future observations beyond configured skew, sequence rollback/replay and observed-time rollback.

These surfaces authenticate and reconcile evidence only. They grant no infrastructure execution, promotion, rollback, routing, lease, sibling-semantic, or live-trading authority.
