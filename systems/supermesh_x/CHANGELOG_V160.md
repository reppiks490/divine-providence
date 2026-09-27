# SuperMesh-X v1.6.0 — Adaptive Provider Health Feedback

- Feeds cache-refresh, stale-cache, subscription-loss, reconnect-failure, and schema-drift signals into provider health.
- Uses time-decayed penalties so transient failures recover instead of permanently blacklisting a provider.
- Adds per-provider circuit states (closed/open/half-open) with cooldown and success recovery.
- Adds deterministic, secret-free provider-health receipts and stable provider ranking for failover.
- Preserves all v1.5 subscription restart and privacy/authority behavior.
