# SuperMesh-X v1.5.0 — Subscription Resilience & Replay Safety

Modern MCP subscription events are level-triggered refetch signals. A lost or gracefully closed stream is not replayable: clients back off, open a new listen request, and refetch state. This release makes that rule explicit and auditable.
