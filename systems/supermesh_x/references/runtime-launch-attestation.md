# Runtime Launch Attestation — v2.8.0

This layer verifies what a concrete runtime actually enacted, rather than trusting a launch request. It does **not** activate the 50+ logical-agent swarm.

## Invariants
- Every launch request is bound to `run_id`, worker identity and monotonic fencing token.
- Enforced resource ceilings must be at least as restrictive as the admitted request.
- Input mounts are immutable/read-only and the outbox is a distinct writable mount.
- DNS resolution produces a public-IP answer set; the actual connection must use one of those pinned public IPs. A changed or private/link-local/metadata address fails closed.
- Crash reconciliation compares the observed runtime owner/fence with durable ownership. Stale or unowned runtimes are destroyed; a missing runtime is marked lost/requeued; an apparently matching runtime is adopted only after attestation.
- Receipts contain digests and metadata, not raw credentials or private payloads.

A real container/VM adapter remains required before claiming OS-level isolation or real resource enforcement.
