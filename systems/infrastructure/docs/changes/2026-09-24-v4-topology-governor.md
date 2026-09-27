# V4 topology governor change record

**Date:** 2026-09-24

**Before:** V3 safely gated individual component mutations but had no cross-component dependency, failure-domain, redundancy, authority-owner, or lease reasoning.

**Change:** Added an optional immutable `TopologyModel`, pure `BlastRadiusGovernor`, and process-local `MutationLeaseManager`; integrated them after `ActionGuard` and before execution; journal/summary now exposes topology decisions.

**Why:** Two locally safe actions can combine into an unsafe infrastructure event. Sibling-owned components also need an executable observation-only boundary rather than a prose convention.

**Operational consequence:** No topology model means V3 behavior is preserved. Supplying a topology model can only reduce eligible mutations. Process-local leases are not distributed coordination.

**Not included:** dynamic discovery, distributed leases, Kubernetes adapters, staged-canary execution, causal attribution.

**Rollback:** Remove the optional topology model argument/integration and `topology_governor.py`; V3 gates remain independent.

**Stale when:** the topology source becomes dynamic, leases become distributed, or canary execution is added.
