# SuperMesh-X v3.7.0

## Witness-policy expiry and trusted-time freeze resistance
- Added optional `WitnessPolicyEpoch.expires_unix`. The field is omitted when unset, preserving the exact serialized shape and digest of legacy v3.6-and-earlier policies.
- Added `TrustedTimeSample`, `TrustedTimeGuard`, and `DurableTrustedTimeFloor` in `scripts/trusted_time.py`.
- Trusted time is explicit: adapters must supply already-authenticated samples; the process wall clock is never silently promoted to a trust source. Time and uncertainty fields are strict integer seconds; fractional or string-coerced values are rejected.
- Added bounded uncertainty semantics. A policy is accepted only when its expiry is strictly beyond the sample's entire `[lower, upper]` interval; uncertainty overlapping expiry fails closed.
- Added a crash-consistent monotonic local time floor plus optional externally retained `minimum_lower_bound_unix` for rollback detection outside the local rollback domain. Floor updates use a fail-closed exclusive `.update.lock` and reload the latest durable floor before comparison, preventing stale concurrent writers from lowering the accepted floor.
- Bootstrap and dual-threshold rotation of expiring policies require trusted time. Rotation uses one fixed sample for both old and new policy checks.
- New checkpoint creation, active gossip admission, signed compaction, and compacted loading now enforce current-policy freshness when expiry is configured.
- Historical witness signature verification and strict forensic gossip replay deliberately remain valid after current policy expiry; freshness controls current acceptance authority, not the ability to audit past evidence.
- v3.6 signed compaction snapshots created under an expiring policy bind the fixed trusted-time report into both the snapshot and anchor statements.

## Compatibility and authority
- Existing non-expiring policies and their digests remain backward compatible.
- v3.1 remains the protected stable rollback baseline; v3.7 is an additive candidate only.
- Trusted-time evidence grants freshness authority only. It does not grant execution, routing, external-write, brokerage, credential, or filesystem permissions.

Stale when: trusted-time schemas, expiry rules, or active/historical verification boundaries change.
