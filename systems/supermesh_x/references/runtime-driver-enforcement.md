# v2.6 Runtime Driver & Enforcement Harness

SuperMesh-X v2.6 adds the backend-neutral contract between the durable execution/isolation control plane and a future real sandbox, VM, or container implementation. This release does **not** activate the 50+ logical-agent swarm and the bundled `InMemorySandboxBackend` is a deterministic conformance harness, not a claim that a real isolated computer was launched.

Every runtime mutation carries the durable owner identity plus a monotonic **fencing token**. A stale owner cannot stop, heartbeat, or destroy a runtime after takeover. Runtime creation requires a matching isolation reservation and positive resource limits; admitted limits are handed to the backend as enforced limits rather than advisory metadata.

Secret references are accepted only as `secretref://` identifiers and are transformed into one-way, run/fence-bound ephemeral handles before the backend boundary. Receipts contain counts and digests, not raw references. Egress classification fails closed for loopback, RFC1918/private, link-local/metadata, multicast, reserved and local-name targets.

The lifecycle contract is create -> start -> heartbeat -> stop -> destroy. Termination has deterministic TERM -> KILL escalation planning, and orphan cleanup destroys abandoned runtimes while clearing secret-handle state. Real backends must satisfy the conformance surface before admission; backend absence must fail open at discovery but fail closed for execution ownership.

## Deferred intentionally

Actual Docker/VM/browser-computer launch, OS cgroup/job-object adapters, real DNS resolution/rebinding enforcement, vault materialization, and multi-machine swarm activation remain deferred until a concrete runtime provider is exposed and independently verified. Research/private context still cannot authorize external writes or live trades.
