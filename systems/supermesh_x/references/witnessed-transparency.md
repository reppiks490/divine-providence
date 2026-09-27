# Witnessed Transparency v3.2.0
Independent Ed25519 witness quorum receipts are required for accepted checkpoints. Growth is verified append-only, rollback and same-size split views fail closed, revoked witnesses cannot count toward quorum, duplicate identities cannot satisfy quorum, and witness signatures never grant execution capabilities.

The included proof representation intentionally carries leaf material for deterministic reference/conformance testing. Production adapters should replace it with compact RFC 9162/RFC 6962-style node consistency proofs and independently persisted/gossiped witness checkpoints.
