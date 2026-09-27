# Task Lifecycle Observability

For MCP 2026-07-28 task-augmented tool calls, treat a task as one logical operation across polling, input-required transitions, cancellation, and completion.

1. Validate task ID entropy and status with the existing task guard.
2. Preserve server `ttlMs` and `pollIntervalMs`; never poll faster than the normalized directive.
3. On Streamable HTTP task methods, route with `Mcp-Name: <taskId>` and `Mcp-Method: <method>`.
4. Fail closed when the observable task TTL has elapsed. Do not silently recreate a write-capable task.
5. Re-apply privacy and external-write authority gates to every `tasks/update` input response and before consuming a terminal result.
6. Emit a secret-free lifecycle receipt tied to one `logical_operation_id` and optional trace ID. Poll attempts are children of the logical operation, not independent decisions.
7. Never enumerate tasks; only operate on task IDs already returned by an authorized flow.
