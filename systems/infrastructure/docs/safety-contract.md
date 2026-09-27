# Infrastructure Supervisory Loop Safety Contract

This document states safety behavior that sibling systems and future agents may rely on. It describes current truth; it is not a roadmap.

## Authority boundary

The supervisory loop surrounds infrastructure through `InfraAdapter`. It does not absorb authority from sibling systems. Adapters remain the explicit boundary through which observation, mutation, snapshot, and rollback occur.

## Evidence-confidence boundary

`HealthReport.confidence` represents confidence in the current observation used to authorize a mutation. Historical action outcomes in `OutcomeMemory` may influence expected utility, but **must not increase current telemetry confidence**. A previously successful action is not evidence that the present diagnosis is correct.

Do not change this rule unless the evidence model is redesigned so historical and current confidence are represented separately and the mutation guard is updated accordingly.

## Observer failure

Observer errors are uncertainty, not evidence that the target is unhealthy. Synthetic reports containing `observer_error:*` do not produce mutation candidates.

## Canary threshold

`GuardPolicy.canary_required_above_risk` is enforced conservatively. The current adapter contract does not provide a genuine staged-canary execution/promote interface. Therefore actions with estimated risk above the threshold are denied with:

`canary required above risk threshold; canary execution unavailable`

A boolean payload flag is deliberately insufficient. The threshold may be relaxed only after a real canary execution contract exists and is independently verified.

## Critical health floor

High-impact autonomous mutations require explicit current health context. If health is unknown, they are denied. When current health is below `GuardPolicy.critical_health_floor`, autonomous high-impact mutation classes are denied:

- `RESTART`
- `SCALE`
- `REPAIR`
- `ISOLATE`

Low-impact reversible actions such as `TUNE` and `ROUTE` may still proceed when all other policy gates pass. This preserves bounded recovery options without allowing a fragile target to receive disruptive autonomous intervention.

## Rollback and verification

Every executed mutation is preceded by a snapshot and followed by health verification. Failed verification triggers rollback. A failed observer must not be converted into a target mutation.

## Stale when

Review this document whenever the adapter protocol, `GuardPolicy`, `ActionGuard.approve`, `Planner.propose`, or canary execution model changes.
