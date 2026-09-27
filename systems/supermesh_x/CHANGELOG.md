# v2.5.0 — Sandbox/Workspace Isolation & Remote-Store Adapter Boundary

- Added deny-by-default workspace mount manifests with host-path and traversal rejection.
- Added network-egress classes (`none`, `public_https`, `provider_allowlist`) with HTTPS and internal-address guards.
- Added argv-only execution specs and secret-redacted process receipts.
- Added reservation-to-runtime enforcement hooks that can narrow but never expand admitted resources/authority.
- Added `secretref://` vault-broker request/receipt boundary without durable secret/lease disclosure.
- Added deterministic watchdog cleanup planning for expired/orphaned/runaway work.
- Added backend-neutral atomic-CAS remote run-store adapter with fencing, checkpoint, cancel, outage and CAS-conflict handling.
- Preserved v2.4 and earlier APIs; actual isolated computers and 50+ agent fan-out remain deferred.

# v2.3.0 — Execution-Domain Foundation

- Added authoritative per-run execution leases with monotonically increasing fencing tokens.
- Added stale-writer rejection, lease renewal, terminal-run non-reopen behavior, and takeover after expiry.
- Added hard resource budgets for provider calls, tokens, CPU time, and future extensible resource classes.
- Added least-privilege authority manifests; read authority cannot imply write, broker, or external-action authority.
- Added deterministic operation-specific idempotency keys.
- Added content-addressed checkpoint and rollback receipts that do not serialize private state.
- Added privacy-safe trace propagation that strips secrets and arbitrary baggage before public/provider boundaries.
- Kept multi-computer launch and 50+ agent swarm creation explicitly deferred until isolation and durable-store adapters are independently verified.

# v1.8.0

Cross-SDK MCP conformance fixtures and secret-free conformance receipts.

# v1.7.0
- Distributed provider-health convergence and quota headroom guard.

# 0.8.0 — Adaptive Capability Director

- Added stable runtime tool-surface fingerprints and compatibility-aware schema drift classification.
- Added compact discovery receipts with exposed/withheld candidate audit metadata and no raw payload retention.
- Added capability-specific provider feedback using bounded success/quality/latency observations.
- Added adaptive routing that combines verified runtime readiness with capability-specific feedback.
- Added automatic replacement planning for breaking provider/tool-surface changes.
- Added cross-runtime guidance and a portable adaptive-provider recovery workflow.
- Preserved private-source boundaries, circuit breakers, auth/transport negotiation, and explicit write/trade authority gates.

# 0.6.0 — Unified Provider & Broker Fabric

- Added unified integration registry and user-facing plugin aliases for all previously requested plugins/skills.
- Added Interactive Brokers connection/permission model for retail Client Portal Gateway, TWS/IB Gateway, and eligible OAuth Web API environments.
- Added IBKR read-only-by-default portfolio/market-data/depth/scanner capabilities with explicit confirmation gates for order-changing actions.
- Added Forex Factory structured macro-calendar normalization, revisions, impact metadata, and surprise calculation.
- Added public Substack RSS/long-form normalization with authorized-content boundaries.
- Added Finances to the capability mesh as an authenticated account/holding/watchlist source when connected.
- Expanded named market-mover seed profiles while retaining runtime verification for current roles.
- Added one capability resolver for ready/degraded/deferred integration states.

# Changelog

## 0.5.0
- Added Event Fabric deduplication and syndication clustering.
- Added append-only hash-chained public-event ledger with separate event/publication/retrieval clocks.
- Added observed cross-asset shock graph with lag, channel breadth, and propagation score.
- Added market-relevance-only mover priority scoring.
- Added confidence decay for stale or conflicting event attribution.
- Added deterministic point-in-time replay bundles that exclude future-known evidence.
- Added integrated `event_fabric.py` pipeline and replayable market-event workflow.
- Preserved the v0.3.0 compatibility baseline while retaining all v0.4.0 market-mover behavior.

## 0.4.0 — Current Event & Market-Mover Intelligence

- Added public-event classification and cross-asset market-impact measurement.
- Added event-study primitives for abnormal return, cumulative abnormal return, and pre-event placebo checks.
- Added recency weighting that strongly favors current/breaking evidence and rejects future timestamps.
- Added geopolitical classification for Iran, Strait of Hormuz, sanctions, armed conflict, shipping chokepoints, energy supply, and diplomacy.
- Added cross-asset transmission mapping across energy, gold, USD, rates, volatility, equity indices, sectors, and crypto.
- Added current Trump market-impact profile with public-only social/official/news/regulatory inputs and explicit Iran/Hormuz topics.
- Added Elon Musk and dynamically resolved role buckets for central-bank, Treasury/economic, energy/geopolitical, mega-cap technology, semiconductor, major-bank, and crypto leadership.
- Added current-geopolitical reference and current-market-mover monitoring workflow.
- Preserved v0.3 dynamic discovery, circuit breaker, provenance, social/public-signal, counterfactual, and market-mover interfaces.

## 0.3.0 — Dynamic Discovery, Provenance & Market-Mover Intelligence

- Added runtime capability catalog and dynamic provider discovery descriptors.
- Added adapter negotiation across native tools, MCP, and REST-style providers.
- Added provider circuit-breaker logic and recursive frontier planning.
- Added provenance graph lineage and autonomous source-expansion workflow.
- Added Public Market Signal normalization with strict public-only boundaries.
- Added configurable Market-Mover Intelligence Network seeded with Donald Trump and Elon Musk plus dynamic role buckets.
- Added social/public-statement acquisition planning with direct-source preference and search/crawl/video fallbacks.
- Added multi-horizon event-study windows, pre-event anticipation checks, counterfactual planning, confounder checks, and conservative attribution scoring.

## 0.2.0 — Runtime Truth & Evidence Fusion

- Added explicit provider runtime states, readiness-aware capability planning, point-in-time guards, evidence-family fusion, query expansion, provider benchmarking, and adaptive federated research.

- Added `scripts/smoke_check.py`, a deterministic local end-to-end smoke gate for routing, public-event attribution guardrails, geopolitical transmission mapping, and recency handling.
# v0.6.0 — Unified Plugin Mesh & External Intelligence Gateways

- Added unified plugin/provider universe covering the major plugins and skills accumulated in the SuperMesh build.
- Added Interactive Brokers adapter contract with read/write authority separation.
- Added Substack API/RSS/public-page research ingestion contract.
- Added Forex Factory macro-calendar normalization and confounder integration.
- Expanded named Market-Mover seeds while requiring runtime role verification.
- Added unified market-intelligence workflow joining macro calendar, public figures, social/public events, structured market data, Substack research and authorized IBKR data.

## 0.9.0

Introduced Adaptive Execution Contracts: provider selections are compiled into permission-aware, privacy-aware, schema-pinned execution plans before invocation. Transactional writes require explicit authorization, raw private data cannot route to public providers, schema drift forces rediscovery, and each persisted plan receives a deterministic audit digest without runtime secrets.

## 1.0.0

- Added MCP 2026-07-28 modern-era negotiation and legacy handshake compatibility.
- Added conservative, trust-aware tool annotation normalization.
- Added secret-redacted execution trace envelopes keyed by plan digest.
- Added protocol mismatch and missing-version fail-closed behavior.

## 1.4.0
Subscription event integrity: acknowledgment gating, dedupe/debounce, deterministic invalidation receipts.

## 1.5.0
- Added resilient modern-MCP subscription restart semantics: no replay across streams, mandatory refetch, fresh subscription IDs, bounded per-provider exponential backoff, stale-event rejection, and deterministic secret-free restart receipts.
- Preserved legacy and v1.4 subscription integrity behavior.


## v1.6.0
Adaptive provider health feedback converts freshness, schema-drift, and subscription instability into decaying health penalties, circuit-breaker state, deterministic receipts, and failover ranking.
