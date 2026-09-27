# SuperMesh-X v1.3.0 — Freshness & Subscription Guard

- Adds MCP 2026-07-28 list-result TTL/cache-scope normalization.
- Defaults malformed/missing modern cache hints to ttl=0/private.
- Prevents private cache reuse across principals.
- Bounds provider TTLs locally and treats expiry boundary as stale.
- Normalizes modern list-change delivery through subscriptions/listen while preserving legacy unsolicited behavior.
- Adds five regression tests for cache freshness and subscription semantics.
