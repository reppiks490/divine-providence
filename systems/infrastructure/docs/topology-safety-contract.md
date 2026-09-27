# V4 Topology Safety Contract

## Purpose

Topology knowledge may only reduce autonomous mutation authority. It must never create actions, elevate evidence confidence, or absorb authority from sibling systems.

## Invariants

1. `authority != local` means observation-only for this supervisor.
2. Unknown topology fails closed for RESTART/SCALE/REPAIR/ISOLATE.
3. A high-impact mutation is denied when a transitive downstream component is marked critical.
4. A redundancy-group mutation is denied if removing the target would leave fewer than `min_healthy` currently healthy peers.
5. Failure-domain, redundancy-group, and component scopes are reserved before an approved mutation can coexist with another mutation in the same supervisor cycle.
6. Mutation leases are process-local only. They make no distributed-safety claim.
7. Topology is operator-supplied in V4. The supervisor does not self-edit its authority graph.
8. V3 ActionGuard remains authoritative and runs before topology authorization. Topology cannot override a V3 denial.
9. V4 adds no staged-canary executor. V3's canary threshold remains fail-closed.

## Fail-open meaning

Failure of the supervisory control plane must not cause the supervised service to fail. This does **not** mean uncertainty grants mutation permission. Observation may continue when topology is incomplete; high-impact mutation does not.

## Stale when

Review this contract when a distributed lease backend, dynamic topology discovery, staged-canary executor, or a new high-impact action class is introduced.
