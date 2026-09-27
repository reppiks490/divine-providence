# SuperMesh-X v2.3.0 Build Report

Built from the durable verified `v2.2.0-cycle6` checkpoint. Prior archives and capsules were not overwritten.

## Change

Added the **Execution-Domain Foundation**, a safety/control-plane substrate required before multi-isolated-computer and 50+ logical-agent expansion:

- authoritative expiring execution leases;
- monotonically increasing fencing tokens on ownership takeover;
- stale-owner rejection at checkpoint/rollback/completion boundaries;
- hard resource budgets with fail-closed unbudgeted/overrun handling;
- exact least-privilege authority manifests;
- deterministic operation-specific idempotency keys;
- content-addressed secret-free checkpoint/rollback receipts;
- privacy-safe trace propagation that strips arbitrary baggage and secrets;
- terminal-run non-reopen semantics.

The implementation deliberately does **not** launch the future agent swarm, isolated computers, unrestricted shells, or brokerage actions.

## Research basis

Architecture preflight compared current official/distributed-systems guidance and live provider surfaces. Lease ownership/renewal semantics were checked against Kubernetes Lease documentation; trace/baggage boundaries were checked against OpenTelemetry guidance; MCP authorization material was checked for explicit protected-capability authorization. Research/search providers were used only where materially relevant.

## Test-first evidence

- Baseline before change: `206 passed`.
- RED checkpoint: `ModuleNotFoundError: No module named 'scripts.execution_domain_kernel'`.
- Minimum implementation focused suite: `11 passed`.
- Focused package-contract + execution-domain suite: `13 passed`.
- First full regression: `218 passed, 1 failed`; failure was an obsolete v2.2 test that incorrectly required the *current* manifest version to remain exactly `2.2.0`.
- Compatibility-test repair: v2.2 now verifies its capabilities remain present in newer versions instead of pinning the current version.
- Final full regression: `219 passed`.
- Critical failure/rollback/privacy/authority/provider-health/subscription/conformance suite: `63 passed`.

## Capability preflight actually exercised

Skills/control-plane guidance loaded or applied: Capability Orchestrator, Baton Pass, Astral Orchestrator, Akinator, Exa Search, Tavily, Firecrawl, Google Drive, Stock Market Summary, Adaptive Codex Orchestrator, and selected domain skills relevant to the requested inventory. No child-agent launch surface was exposed, so Astral did not fabricate workers.

Successful provider/tool probes included Exa, Parallel Search, Firecrawl developer search, DataBlue, omgskills discovery, TickerLayer, Massive, CoinGecko, Bybit, Runway authentication metadata, Scite, Zacks, FMP, Next Stock Market Insights, Exum, and Blockscout session unlock. Google Drive/File Library was used for continuity discovery/persistence.

Degraded/unavailable during preflight: Tavily Research (plan usage limit), Twelve Data auth-status call (internal provider failure), U.S. Gold Bureau health check (IP authorization failure). These failures were isolated and did not block unrelated capabilities. Gmail and Finances were intentionally not accessed because no private user data was required.

## Authority/privacy

The new kernel cannot self-grant external-write, brokerage-order, host-filesystem, credential, or live-trading authority. Read scopes do not imply write scopes. Checkpoint receipts contain hashes/opaque references, not raw task state. Trace sanitization does not forward arbitrary OpenTelemetry baggage or secrets across provider boundaries.

## Deferred

The planned multi-isolated-computer runtime and 50+ logical-agent elastic swarm remain deferred until persistent transactional run-store adapters, credential-vault boundaries, sandbox isolation, concurrency admission, deadlock/runaway controls, and their failure-injection tests are independently verified.
