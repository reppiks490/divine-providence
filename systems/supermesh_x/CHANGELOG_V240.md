# SuperMesh-X v2.4.0

## Added
- portable transactional `SQLiteDurableRunStore`;
- restart-safe lease/fencing ownership and crash/takeover recovery;
- durable checkpoint metadata without raw state persistence;
- explicit suspension, idempotent resume, worker-lost and cancellation lifecycle behavior;
- version-CAS protection for operator cancellation;
- transactional shared-capacity `SQLiteIsolationAdmission`;
- resource admission for CPU, memory, storage, GPU, model-token, provider-call and concurrency budgets (or any explicitly configured integer resource);
- capability allowlisting at isolation admission;
- opaque `secretref://` credential-reference validation with digest-only durable recording.

## Preserved
v2.3 execution-domain, privacy, authority, provider, conformance, subscription, and brokerage boundaries remain intact. This release does not launch the future multi-computer runtime or 50+ logical-agent swarm.
