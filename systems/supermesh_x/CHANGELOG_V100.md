# SuperMesh-X v1.0.0 — Protocol-Era Safety & Tool Observability

- Added MCP 2026-07-28 modern-era preflight with per-request protocol-version enforcement.
- Preserved compatibility with handshake-era MCP providers.
- Added conservative normalization for read-only, destructive, idempotent, and open-world tool annotations.
- Added annotation-aware authority classification; unknown/write-capable tools require explicit authorization.
- Added redacted `execute_tool` trace envelopes tied to the deterministic capability-plan digest.
- Added protocol mismatch fail-closed behavior without weakening provider failover.
