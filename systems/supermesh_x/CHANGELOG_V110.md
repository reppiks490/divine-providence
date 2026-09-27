# SuperMesh-X v1.1.0 — Resumable MCP Safety

- Added MCP 2026-07-28 Multi Round-Trip Request validation.
- Added opaque request-state echoing and unknown-response stripping.
- Added bounded round/request budgets with fail-closed exhaustion.
- Rejects deprecated roots/sampling requests in modern MCP resumable flows.
- Added Tasks-extension descriptor validation with high-entropy IDs and no enumeration.
- Preserved all existing privacy, schema-drift, provider-failover, and external-write authority gates across resumed calls.
