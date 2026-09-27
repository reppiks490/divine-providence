# SuperMesh-X v0.9.0

## Adaptive Execution Contracts

- Added deterministic capability-plan compilation from adaptive provider rankings.
- Added ordered provider fallbacks and pinned schema fingerprints per executable step.
- Added authority contracts separating reads, external writes, and transactional brokerage writes.
- Added a plan-time privacy firewall blocking raw private data from public providers.
- Added allowlisted derived-private-feature routing for safe aggregate features.
- Added schema-drift preflight that forces rediscovery before execution.
- Added deterministic SHA-256 execution-plan digests that exclude runtime secrets.
- Extended smoke verification to exercise planning, privacy, authority, and schema-rediscovery gates.
