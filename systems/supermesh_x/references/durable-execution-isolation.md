# Durable Execution Store & Isolation Admission

SuperMesh-X v2.4.0 converts the v2.3 execution-domain invariants into a restartable reference persistence layer and a shared-capacity isolation admission layer. It does **not** launch computers or agents.

## Durable run-store invariants

1. **Transactional ownership.** Lease acquisition, renewal, checkpoint pointer changes, suspension, resume, worker-loss marking, and cancellation execute inside transactional SQLite writes in the portable reference backend.
2. **Monotonic fencing survives restart.** A fresh process opening the same store observes the current fencing token. Takeover after lease expiry increments both attempt and fencing token. A pre-takeover worker cannot commit a late checkpoint.
3. **CAS protects operator actions.** Versioned mutations such as cancellation require the caller's observed run version. Stale operator state fails with `VersionConflict` instead of overwriting a newer state.
4. **Lifecycle is explicit.** The reference states include `running`, `suspended`, `queued`, `worker_lost`, and terminal states. Suspended work requires an explicit resume key; duplicate use of the same key is idempotent.
5. **Cancellation fences immediately.** Cancellation increments the fencing token and clears the lease so an in-flight stale worker cannot later checkpoint.
6. **Durable checkpoints are receipts, not payload stores.** The database records the state hash, optional opaque state reference, attempt, fence, and time. It never stores raw checkpoint state.

## Isolation admission invariants

1. **Capacity is globally shared per admission store.** CPU millicores, memory, storage, GPU units, model tokens, provider calls, concurrent tasks, or other explicitly configured integer resources are transactionally reserved across controller instances.
2. **Unconfigured means denied.** A request cannot silently invent a new resource class or overcommit capacity.
3. **Authority is allowlisted.** Granted capabilities must remain a subset of requested capabilities and a subset of the isolation tier's admissible capabilities. Host filesystem writes and brokerage execution are not implicitly admitted.
4. **Credentials are references only.** Admission accepts opaque `secretref://...` references. It rejects raw keys/tokens and stores only a digest plus count, not the reference strings themselves.
5. **Admission is idempotent, mutation is explicit.** Repeating the exact request for one run returns the same receipt. Changing its resource or authority request requires release and explicit re-admission.
6. **Release is explicit and idempotent.** Capacity is returned only through a recorded release operation.

## Why this still precedes the computer/swarm layer

A multi-computer runtime and a 50+ logical-agent elastic swarm need durable ownership plus deterministic admission before they can safely share compute, provider quotas, GPU allocations, credentials, and writable artifacts. v2.4.0 therefore establishes the portable persistence and admission contracts first.

## Portability

SQLite is the deterministic local/reference backend, not a claim that every deployment must use SQLite. Remote PostgreSQL, Redis, cloud-database, or orchestration backends may replace it only if they preserve the same transactional lease, monotonic fencing, CAS, lifecycle, checkpoint-privacy, admission, and credential-reference semantics.
