# MCP Protocol-Era Safety

SuperMesh-X normalizes MCP tools before routing them. For protocol `2026-07-28` and later, discovery is treated as modern-era `server/discover` and every request must carry the negotiated protocol version. Earlier supported eras use the `initialize` handshake path.

Tool annotations are safety hints, not permissions. Missing annotations default conservatively: not read-only, destructive, non-idempotent, and open-world. Annotations are treated as untrusted unless the server itself is trusted. Only a trusted server tool explicitly marked read-only and non-destructive can receive read authority automatically. Unknown or write-capable tools require explicit authorization under the existing SuperMesh authority contract.

Protocol mismatch, missing modern-era version metadata, schema drift, or privacy-policy failure blocks only the dependent provider hop. Credentials and authorization headers are never persisted in tool traces.

The trace envelope uses a portable `execute_tool` span name and records capability, provider, tool, protocol version, plan digest, and outcome so ChatGPT, Codex, and Claude runtimes can correlate execution without sharing secrets.
