# Resumable Tool Execution

1. Run normal MCP era and capability-plan preflight.
2. If a tool returns `input_required`, validate request state, request count, method allowlist, and round budget.
3. Fulfill only approved input requests; never synthesize authorization from elicitation.
4. Resume using the exact opaque `requestState`; include responses only for request IDs present in the prior result.
5. Re-run authority, privacy, schema-fingerprint, and protocol checks on every resumed tool invocation.
6. For Tasks, accept only non-enumerable high-entropy task IDs and known task states; never expose task IDs in public-provider queries or logs.
7. Stop closed on round-budget exhaustion, malformed state, deprecated modern requests, or authority escalation.
