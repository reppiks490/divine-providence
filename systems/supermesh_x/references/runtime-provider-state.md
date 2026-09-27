# Runtime Provider State

Static capability registration answers **what a provider can do**. Runtime state answers **whether it can be used now**.

SuperMesh-X v0.2.0 separates those concerns so a high-priority provider is never selected merely because it exists in the registry.

## States

- `ready`: authenticated/initialized and suitable for normal routing.
- `degraded`: usable, but with reduced health or reliability.
- `quota_constrained`: usable, but conserve requests and prefer a healthy peer when equivalent.
- `preflight_required`: a session handshake, unlock, initialization, or equivalent step must happen first.
- `auth_required`: credentials or user connection are required.
- `unavailable`: provider is known but cannot be used in the current runtime.
- `unverified`: no fresh runtime observation exists; do not silently assume readiness.

## Routing rule

1. Discover static capability matches.
2. Join them with fresh runtime state.
3. Exclude non-routable states from the active selection set.
4. Penalize degraded or quota-constrained providers.
5. Preserve blocked candidates with the exact reason so the orchestrator can decide whether an authorized preflight is worthwhile.
6. Expire stale state observations rather than carrying readiness forever.

This makes authentication, preflight, quotas, rate limits, and provider outages explicit dependencies in the capability graph.
