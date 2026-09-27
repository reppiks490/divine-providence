# Execution-Domain Foundation

SuperMesh-X v2.3.0 introduces the control-plane substrate required before multi-computer or large-agent execution is permitted.

## Invariants

1. **One authoritative owner per run.** Workers acquire an expiring lease before execution. A new owner receives a strictly higher fencing token; stale owners cannot checkpoint, complete, or roll back the run.
2. **Terminal means terminal.** Completed, failed, or cancelled runs are not silently reopened.
3. **Every resource is bounded.** Provider calls, model tokens, CPU time, wall-clock time, concurrent tasks, storage, and future GPU allocations are represented as explicit budgets. Unbudgeted resources fail closed.
4. **Authority is exact.** Granted capabilities must be a subset of requested capabilities. `repo.read` does not imply `repo.write`; research does not imply brokerage execution; terminal access does not imply host access.
5. **Dispatch is idempotent.** External/retriable operations derive deterministic operation-specific dispatch keys from run, task, attempt, and operation digest.
6. **Checkpoints do not become secret containers.** Durable receipts keep hashes and optional opaque storage references, not raw private task state.
7. **Trace context is not an exfiltration path.** Only explicitly allowed correlation fields cross provider boundaries. Arbitrary baggage, credentials, customer identifiers, email addresses, and private context are stripped.
8. **Rollback is fenced.** A worker may request rollback only while it holds the current lease/fencing token and only to a checkpoint belonging to that run.
9. **Execution substrate cannot self-elevate.** This module grants no external write, broker order, live-trading, host-filesystem, or credential authority by itself.

## Why this precedes the swarm

A checkpoint says where work can resume; it does not establish who is currently allowed to advance that state. Large swarms and isolated computers magnify duplicate execution, stale-worker, race, runaway-budget, and credential-propagation failure modes. The execution-domain layer must therefore be stable before worker count or computer count increases.

## Production adapter requirements

Future persistent backends must implement lease acquisition/renewal/takeover and checkpoint writes atomically (for example using compare-and-swap or transactional updates), preserve monotonically increasing fencing tokens across process restarts, store checkpoint payloads outside receipts, and enforce authority/budget checks immediately before dispatch. A stale worker must be unable to commit after takeover even if it wakes up later.

## Deferred by design

v2.3.0 does **not** yet launch the planned 50+ logical agents, multi-computer workspaces, unrestricted shells, or live brokerage actions. Those features must be built on top of this contract and receive separate concurrency, isolation, credential-vault, failure-injection, rollback, privacy, and authority verification.

## Design references

- Kubernetes Lease objects: coordination and leader ownership semantics.
- OpenTelemetry context/baggage guidance: baggage can cross service boundaries and must not carry secrets to untrusted downstreams.
- MCP authorization guidance: protected capabilities require explicit authorization rather than inheriting access from unrelated tools.
