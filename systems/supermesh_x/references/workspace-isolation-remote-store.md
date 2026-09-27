# v2.5 Workspace Isolation & Remote Store Boundary

SuperMesh-X v2.5 extends the v2.4 durable execution/admission layer with the contract that a future computer or agent runtime must satisfy. It does **not** launch a VM, container, browser computer, or agent swarm. The 50+ logical-agent architecture remains deferred until an actual runtime can prove these boundaries under failure injection.

## Workspace boundary

A workspace has a stable identity, a read-only root, and an explicit mount manifest. Mount sources are opaque references (`artifactref://`, `fileref://`, `workspace://`, `scratch://`, or `artifactout://`), never host filesystem paths. Relative targets are normalized and parent traversal or absolute paths are rejected. Writable capacity is limited to explicitly admitted workspace/scratch/output mounts.

The default policy is **deny-by-default**. Host filesystem visibility is false. Runtime implementations must not reinterpret an opaque reference as a host path without a separate trusted materialization layer and an auditable authority decision.

## Network egress

Network policy has three classes: `none`, `public_https`, and `provider_allowlist`. The default is `none`. The public class is HTTPS-only and rejects literal private, loopback, link-local, multicast, unspecified, and reserved addresses plus localhost-style targets. Provider allowlists require exact public hostnames. This contract is only the decision layer; a future VM/container runtime must enforce it using its own network namespace/firewall controls.

## Process/terminal boundary

Execution specifications are argv-only and reject `shell=True`. Working directories must remain inside the workspace. Secret-like environment variables cannot be placed in the public environment and must instead be represented by `secretref://` references. Execution receipts intentionally omit raw command arguments, public environment values, secret references, and secret-lease IDs; they retain only safe metadata such as executable name, argument count, digests, timing, output byte counts, and exit/killed status.

## Reservation-to-runtime enforcement

A runtime enforcement hook can only reduce limits that were already admitted by the v2.4 reservation. It cannot invent CPU, RAM, storage, GPU, token/provider-call/concurrency capacity or capabilities. Authority can only narrow from the admitted capability set. No host escape, brokerage order, or external-write authority is inferred from resource admission.

## Vault broker boundary

Vault resolution requires explicit `secrets.resolve` authority and accepts only `secretref://...` references. Broker requests may contain those opaque references because a vault implementation must know what to resolve, but durable receipts store only digests/counts. Resolved values and lease IDs must never appear in logs, evidence receipts, state capsules, or public-provider prompts.

## Remote durable-store adapter

The backend-neutral contract requires `read(run_id)` plus atomic `compare_and_swap(run_id, expected_version, new_record)`. The adapter preserves lease expiry, fencing tokens, version-CAS, terminal-state closure, secret-free checkpoint receipts, and cancellation fencing. If the remote store is unavailable, ownership mutation fails rather than silently falling back to a local owner record; a local fallback could create split-brain workers.

The included in-memory CAS backend is a deterministic conformance/reference backend only. It is not a claim of production durability. PostgreSQL, Redis/etcd, cloud KV, or another distributed backend must pass the same observable contract before it can replace the SQLite reference store.

## Watchdog/orphan cleanup

The watchdog is a planner, not an executor. It detects expired leases, terminal runs that still hold reservations, and optionally runaway runtimes, then emits deterministic cleanup actions. A future runtime controller must execute those actions through the same fenced lifecycle and authority gates; the watchdog itself receives no kill, shell, broker, or host-write authority.

## External design alignment

The design is intentionally consistent with common container/orchestration security principles: isolate filesystem/process/network resources, use least privilege, keep secrets behind a dedicated broker, and separate control-plane decisions from data-plane enforcement. Runtime-specific mechanisms remain deferred so ChatGPT, Codex, Claude, local containers, remote sandboxes, and future computer backends can implement the same portable contract without weakening it.
