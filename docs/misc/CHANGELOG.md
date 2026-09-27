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
