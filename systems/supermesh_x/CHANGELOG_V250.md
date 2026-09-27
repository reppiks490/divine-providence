# v2.5.0 — Sandbox/Workspace Isolation & Remote-Store Adapter Boundary

- Deny-by-default workspace/mount policy with no implicit host filesystem visibility.
- HTTPS-only public egress and exact provider allowlist classes with private/link-local/localhost guards.
- Argv-only process specs, secret-reference environment separation, and redacted process receipts.
- Runtime-limit hooks cannot exceed v2.4 resource reservations or granted capabilities.
- Vault broker requires `secrets.resolve` and keeps secret/lease identifiers out of durable receipts.
- Remote durable-store adapter requires atomic read/CAS, preserves fencing, and refuses unsafe local fallback on outage.
- Watchdog emits deterministic cleanup plans for expired/terminal/runaway work but performs no privileged action itself.
- Actual isolated computers and the 50+ logical-agent swarm remain deferred.
