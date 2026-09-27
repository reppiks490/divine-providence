# Protocol Era Preflight

1. Discover the provider's MCP protocol version and tool surface.
2. For `2026-07-28` or later, use `server/discover` semantics and require the same protocol version on each request.
3. For handshake-era versions, use `initialize` negotiation.
4. Normalize tool annotations with conservative defaults.
5. Combine annotation-derived authority with the existing capability authority contract; the stricter result wins.
6. Re-run schema fingerprint and privacy preflight before execution.
7. Emit a redacted `execute_tool` trace keyed by the capability-plan digest.
8. On mismatch, block that hop, rediscover, and try only a policy-compatible fallback.
