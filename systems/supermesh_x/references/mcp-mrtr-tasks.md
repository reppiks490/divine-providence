# MCP Multi Round-Trip and Tasks Safety

SuperMesh-X v1.1.0 treats MCP 2026-07-28 resumable interactions as explicit state machines. `input_required` results must carry opaque `requestState`, bounded `inputRequests`, and only supported request methods. Resume envelopes echo the opaque state and discard responses for unknown request IDs. The default maximum is ten round trips.

On the modern protocol, roots and sampling are deprecated and are rejected from new multi-round-trip plans. Elicitation remains supported. The Tasks extension is treated as bearer-state: task identifiers must be high entropy, are never enumerable, and task status is validated before use. These guards do not grant write authority; existing SuperMesh authority and private-source firewalls still apply to every resumed tool call.
