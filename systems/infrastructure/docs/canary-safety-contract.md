# Staged Canary Safety Contract (V5)

V5 adds an explicit staged-canary execution contract without weakening V3/V4 authorization gates.

## Invariants

1. Above-threshold risk is approved only when both a `StagedCanaryExecutor` is installed and the target adapter exposes callable `stage_canary`, `promote_canary`, and `abort_canary` methods.
2. Full `execute()` is never used as a substitute for staging an above-threshold action.
3. Promotion is impossible until post-stage health passes the independent verification policy.
4. Regression, rollback-floor breach, or loss of verification telemetry triggers abort and produces `promotion_authorized=false`.
5. Every staged attempt produces a SHA-256 proof object containing cycle, component, action fingerprint, before/observed scores, verification reason, authorization result, and terminal status.
6. Canary proofs are journaled separately from action results so orchestration may transport evidence without inheriting supervisory authority.
7. Topology authorization and mutation leases remain upstream of canary execution. Canary success cannot override an ActionGuard or BlastRadiusGovernor denial.

## Adapter contract

A canary-capable adapter must implement:

- `stage_canary(action, snapshot) -> (ok, token, message)`
- `promote_canary(token, action) -> (ok, message)`
- `abort_canary(token, snapshot, action) -> (ok, message)`

Merely placing `canary=true` in action metadata is not capability evidence.

## Scope limits

This package contains the protocol and proof-carrying execution path, not a production Kubernetes/Argo/traffic-split adapter. The default remains no canary executor, so existing deployments retain V3 fail-closed behavior.

Stale when: the adapter protocol, proof schema, or promotion/rollback policy changes.

## V6 proof integrity and learning eligibility

`CanaryProof.verify_integrity()` recomputes the canonical SHA-256 digest and detects post-finalization mutation or corruption. This is an integrity check, **not** an identity signature, authorization token, or remote attestation.

Successful execution and positive online-learning credit are separate decisions. `OutcomeMemory` may credit a successful action only when the result carries explicit causal eligibility plus a proof hash. For staged canaries, V6 requires an intact promoted proof, explicit promotion authorization, and a strictly positive observed health delta. A promoted flat/regressing canary may remain an execution success under the configured canary policy, but it earns no positive learning credit.

This contract becomes stale when a counterfactual/control-group causal estimator replaces the conservative eligibility gate or when proofs become cryptographically signed/attested.
