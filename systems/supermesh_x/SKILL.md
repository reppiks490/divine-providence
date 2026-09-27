---
name: supermesh-x
description: Use when a task benefits from cross-platform research, data acquisition, market/crypto intelligence, coding orchestration, repository coordination, study workflows, or multi-provider evidence fusion across ChatGPT, Codex, and Claude.
---

# SuperMesh-X

SuperMesh-X is a capability router and evidence-fusion skill. It does **not** replace provider plugins; it discovers available capabilities, selects the smallest useful provider set, expands when evidence is weak, normalizes results, cross-checks conflicts, and preserves provenance.

## Core rule

Route by **capability**, never by hard-coded provider name. A provider is an implementation detail. If one provider is unavailable, stale, incomplete, or quota-limited, select another registered provider with the same capability.

## Operating loop

1. Classify the request into one or more capability domains.
2. Discover available runtime tools, plugins, skills, connectors, browser/search access, local files, and public APIs.
3. Build a retrieval plan with a minimum lane and escalation lanes.
4. Retrieve from independent sources where corroboration materially improves accuracy.
5. Normalize identifiers, timestamps, units, symbols, schemas, and source metadata.
6. Detect conflicts, stale data, missing fields, duplicate evidence, leakage, and unsupported inferences.
7. Fuse evidence into a claim graph with confidence and provenance.
8. Execute code or repository work only through the runtime's authorized coding/orchestration tools.
9. Verify the requested outcome before claiming completion.
10. Preserve a compact handoff when the work crosses agents, sessions, or runtimes.
11. Treat unverified provider state as non-ready until the runtime actually proves availability.

## Lazy-load references

Read only the references needed for the task:

- Broad/deep web research, crawling, academic research, search diversification: `references/research-mesh.md`
- Stocks, ETFs, futures, FX, rates, macro, fundamentals, factors, backtesting: `references/finance-quant.md`
- Crypto markets, wallets, contracts, on-chain data: `references/crypto-onchain.md`
- Coding, repositories, multi-agent ownership, handoffs: `references/coding-orchestration.md`
- YouTube, study, teaching, knowledge extraction: `references/learning-media.md`
- NVIDIA/GPU acceleration and skill discovery: `references/nvidia-compute.md`
- Dynamic providers, capability contracts, failover: `references/provider-registry.md`
- Verification, data quality, permissions, provenance: `references/verification-governance.md`
- System-level architecture: `references/architecture.md`
- Source-universe expansion: `references/source-expansion.md`
- Adaptive query compilation: `references/query-planner.md`
- Evidence-family fusion and contradiction handling: `references/evidence-fusion.md`
- Point-in-time and revision-aware research: `references/temporal-data.md`
- Live plugin/tool discovery and optional-provider expansion: `references/plugin-discovery.md`
- Runtime provider readiness, auth/preflight/quota state: `references/runtime-provider-state.md`
- Market-Mover Intelligence Network for public figures/social posts and market-event attribution: `references/market-mover-intelligence.md`
- Current geopolitical market-impact analysis, including Iran/Strait of Hormuz, sanctions, conflict, shipping, and energy transmission: `references/current-geopolitical-market-impact.md`
- Event Fabric for duplicate control, immutable event ledgers, shock graphs, confidence decay, and point-in-time replay: `references/event-fabric.md`

## Capability escalation

Start narrow. Expand only when useful:

`single authoritative source → second independent source → specialist provider → broad search/crawl → primary-source verification → structured synthesis`

For research-heavy tasks, diversify by **source class**, not just query wording: official/primary, specialist database, scholarly, market/structured feed, reputable journalism, community discussion where appropriate, and user/private sources when authorized.

## Market-Mover Intelligence Network

For public figures or executives whose communications may affect markets, use the Market-Mover lane. It is **public-only**: public social posts, official statements, speeches, interviews, press releases, public regulatory/executive actions, company announcements, and public video/transcripts. Never use private location or private communications.

Normalize each event, map it to relevant assets and macro factors, examine pre-event anticipation, measure multi-window reactions, compare with counterfactuals when possible, search for competing events, and produce a conservative attribution tier. Treat temporal association as evidence to investigate, not automatic proof of causation.

## Current geopolitical and social-event lane

For fast-moving public events, prioritize current evidence over historical analogues. Resolve the current officeholder or executive at runtime instead of assuming a stored name is still current. Track only public communications and public actions: official releases, public social posts, speeches, interviews, company announcements, regulatory actions, public defense/diplomatic statements, reputable breaking-news reports, and lawfully accessible public shipping/energy data.

For Iran, the Strait of Hormuz, sanctions, armed conflict, shipping chokepoints, and energy-security events, build an event clock using the earliest verifiable public timestamp, then measure cross-asset responses across energy, gold, USD, rates, volatility, equity indices, sector proxies, and crypto. Explicitly scan for competing macro releases, central-bank decisions, earnings, other geopolitical headlines, and pre-event price movement. Historical Trump/Musk/social-media studies are calibration evidence only; current events drive current attribution.

Never convert a timestamped association into an unqualified causal claim. Use event-study, counterfactual, and confounder evidence to report an association tier.

## Event Fabric and replay discipline

For fast public events, treat duplicate posts, syndicated news stories, mirrors, and crawler copies as one underlying **Event Fabric** cluster whenever canonical entity/text/timestamp evidence supports that conclusion. Preserve the independent source families inside the cluster instead of inflating confidence from duplicates.

Commit canonical events to an append-only **hash-chained ledger** carrying event time, publication time, and retrieval time. Revisions append; they do not rewrite the first-seen record. Build observed cross-asset shock graphs from timestamped market reactions, then decay confidence when evidence becomes stale or unresolved contradictions remain.

When replaying an event for research or backtesting, include only evidence and market observations available on or before the replay cutoff. Persist a deterministic replay bundle hash. This makes the analysis auditable across ChatGPT, Codex, and Claude and prevents later knowledge from leaking backward into the event history.

Market-mover prioritization is based on market relevance only. Never use political ideology, electoral preference, popularity, or persuasion value as a prioritization signal.

## Unified Plugin Mesh

SuperMesh-X v0.6 exposes one provider-independent capability facade across the research, coding/orchestration, finance, crypto, blockchain, study/media and market-event plugins already registered in `config/plugin-universe.json`. Discover actual runtime availability before routing; never require the user to manually restate the individual provider list in every future prompt. Read `references/super-plugin-universe.md` for the full contract.

## Interactive Brokers

When Interactive Brokers connectivity is available and authorized, use it as a high-value source for market data, portfolio/account state and execution records. Keep the brokerage write lane separate: placing, changing or cancelling orders requires explicit user authorization for the concrete action. Support Client Portal Gateway, TWS/IB Gateway, and approved direct/FIX routes according to the runtime/account. Read `references/interactive-brokers.md`.

## Substack

Use Substack as a research/newsletter intelligence lane through the authorized Developer API when available, canonical publication RSS, public post pages, and user-authorized inbox copies. Normalize author/publication/time/citations/entities and preserve claim provenance. Read `references/substack-intelligence.md`.

## Forex Factory

Use Forex Factory calendar data as a macro-event and confounder source when lawfully accessible. Normalize impact, actual/forecast/previous/revisions and exact event timing; join releases into the Event Fabric so macro announcements are not confused with public-figure or geopolitical effects. Read `references/forex-factory.md`.

## Named market movers by activity

Maintain named seed profiles for Donald Trump, Elon Musk, Kevin Warsh, Scott Bessent, Jensen Huang, plus configurable candidate seeds across banking, mega-cap technology, AI, asset management and crypto. Names are monitoring seeds, not permanent truth: verify current roles and public channels at runtime, and prioritize by observed market-relevant activity, recency, topic/asset exposure and evidence coverage.

## Unified Provider & Broker Fabric

SuperMesh-X v0.6.0 treats every previously named plugin/skill plus Interactive Brokers, Forex Factory, Substack, and Finances as entries in one capability registry. Use `config/plugin-aliases.json` to translate user-facing @ names into stable integration IDs and `config/integration-registry.json` to resolve capabilities. Read `references/unified-integration-fabric.md` for the complete routing contract.

Interactive Brokers is both a data source and a separately gated execution surface. Prefer read-only portfolio, positions, trades, scanners, depth, and market-data capabilities when authorized. Live/paper order placement, modification, or cancellation requires explicit action authorization; research conclusions never implicitly authorize a trade. Read `references/ibkr-brokerage.md`.

Forex Factory supplies macro calendar/context through its structured public exports and calendar surface. Normalize event time, currency, impact, actual, forecast, prior, and revisions; use scheduled releases as confounders and event-study anchors, not as automatic trading signals. Read `references/forex-factory-calendar.md`.

Substack supplies public RSS/long-form research and authorized publication content. Prefer public RSS and public archive/post pages, preserve author/publication/time provenance, and never bypass subscriber-only access controls. Read `references/substack-intelligence.md`.

Named market-mover profiles include Donald Trump and Elon Musk plus runtime-verified seeds for central-bank, Treasury, mega-cap technology, semiconductor, bank, and crypto leadership. Stored names are monitoring seeds, not political endorsements or permanent officeholder assumptions; verify current role and source identity at runtime.

## Adaptive Capability Director

SuperMesh-X v0.8.0 adds an **Adaptive Capability Director** above the existing capability router. At runtime, fingerprint the visible tool schemas, diff them against the last known surface, and classify **schema drift** before relying on a changed provider. Added optional parameters or newly added tools may be compatible; removed tools, removed parameters, parameter type changes, and newly required parameters are breaking until an adapter is updated and verified.

For dynamic discovery, emit a compact **discovery receipt** containing the discovery query, candidates exposed to the router, withheld count/top withheld candidates, status, stop reason, and schema/version metadata when available. Never put raw tool arguments, tool outputs, private email/account content, secrets, or provider credentials in discovery receipts.

Provider selection may incorporate capability-specific observed feedback such as success, quality, and latency, but runtime readiness, auth/transport compatibility, circuit-breaker state, privacy boundaries, and action authority remain hard gates. When a surface change is breaking, invoke replacement planning: locate a compatible provider for the same capability, rank it with runtime health and capability-specific feedback, preserve the discovery receipt, and degrade safely if no verified replacement exists. Read `references/adaptive-capability-director.md`.

## Hard boundaries

- Never claim access to a provider that is not actually available and authenticated in the current runtime.
- Never treat search snippets as equivalent to primary-source evidence when primary verification is practical.
- Never merge conflicting observations silently; preserve disagreement and timestamps.
- Never use future-known data in historical backtests or claim point-in-time validity without an availability timestamp.
- Never let one plugin inherit another plugin's permissions.
- Never convert research authority into transaction/deployment/account-change authority.
- Respect provider terms, authentication, rate limits, robots policies, and user-granted permissions.


## Private Intelligence Bus & Portfolio Shock Overlay

SuperMesh-X v0.7.0 integrates **Gmail** as a user-authorized private intelligence bus and **Finances** as a user-authorized portfolio/context layer. Gmail can supply newsletter, alert, broker-notice, research-thread, and supported attachment intelligence. Finances can supply holdings, allocation, watchlist, account, transaction, and sync-state context when connected.

Raw Gmail and Finances payloads stay inside the private boundary. Never send raw private content to public search, crawling, market-data, or research providers. If cross-provider enrichment is necessary, emit only explicitly allowed derived features and mark them `derived_private_feature`. Read `references/email-intelligence-bus.md` and `references/private-source-boundary.md`.

Use the Portfolio Shock Overlay to map measured public market shocks onto authorized holdings. This is descriptive exposure analysis only: never emit an automatic trade instruction or infer proven causation from temporal association. Read `references/portfolio-shock-overlay.md`.

## v0.9 Execution Contract Rule

Before invoking a dynamically selected provider, compile a capability execution plan. The plan MUST preserve the requested capability, selected provider, ordered fallbacks, authority mode, source/privacy class, expected schema fingerprint, observed schema fingerprint when available, and preflight status. Raw `user_authorized_private` content MUST NOT be sent to public providers. `derived_private_feature` values MAY cross that boundary only when every transmitted field is explicitly allowlisted. Transactional brokerage operations and external writes MUST require explicit user authorization and MUST NOT be inferred from research, market analysis, public-figure activity, portfolio context, or strategy signals. Schema-fingerprint mismatch MUST force rediscovery. Runtime credentials/secrets MUST NOT be persisted into plan artifacts or plan digests.

## v1.0 MCP Era Rule

Before executing an MCP-backed capability, classify the provider as modern (`2026-07-28`+) or handshake-era. Modern requests must carry `io.modelcontextprotocol/protocolVersion`; use `server/discover` for discovery and do not silently downgrade on authentication, rate-limit, transport, or server failures. Treat tool annotations as untrusted hints unless the provider is trusted. Missing annotations use conservative defaults. The stricter of annotation-derived authority, capability authority, privacy policy, and explicit user authorization always wins.


## v1.6.0
Adaptive provider health feedback converts freshness, schema-drift, and subscription instability into decaying health penalties, circuit-breaker state, deterministic receipts, and failover ranking.

## v2.4.0 durable execution/isolation rule
Before future computer or multi-agent dispatch, use the durable run-store and isolation-admission contracts: acquire/renew a fenced lease, persist only secret-free checkpoint metadata, require version-aware lifecycle mutations, reserve explicit resource capacity, allow only tier-approved capabilities, and pass credentials only as opaque `secretref://` references. This layer grants no host-shell or brokerage execution authority by itself.

## v2.5 workspace isolation and remote durability
For any future computer/terminal/agent execution, apply `references/workspace-isolation-remote-store.md` after v2.4 admission. Require an explicit workspace mount manifest, network-egress class, argv-only process contract, resource-enforcement hook, vault-broker authority for `secretref://` resolution, watchdog lifecycle, and a fenced durable-store backend. Do not launch an isolated computer or 50+ agent fan-out from this package version.

## v3.0 runtime evidence routing
When a runtime/provider supplies signed launch, heartbeat, termination, or reconciliation evidence, verify the Ed25519 envelope and trust-store state before journal admission. Treat a valid signature as authenticity evidence only; it never grants capabilities or external-write authority.
## v3.1 Trust/Transparency Routing
Use `scripts/trust_transparency.py` for durable public trust roots, dual-threshold sequential key rotation, Merkle inclusion proofs, and signed transparency checkpoints. Signatures authenticate evidence; they do not grant execution authority.

## v3.2–v3.3 Witness/Transparency Rule
Do not migrate or relabel existing v3.2 witness checkpoints silently. Legacy `WitnessedCheckpointLedger` state remains valid on its original tree algorithm. New RFC-compatible witness deployments use `RFC9162WitnessedCheckpointLedger`, compact RFC 9162 consistency evidence, and durable persistence before success is exposed. Public gossip becomes authenticity-bearing only when `GossipReceiptStore` is given a trusted witness registry and all quorum/signature/consistency checks pass. These proofs and cosignatures never create external-write, execution, or brokerage authority.


## v3.6 signed gossip compaction
When durable gossip replay cost becomes material, prefer the additive `DurableGossipJournal.compact()` / `load_compacted()` path. Never truncate the canonical journal merely because a snapshot exists. Snapshots are immutable and create-only; the signed anchor chain selects the latest accepted snapshot. If the threat model includes rollback of every local trusted file, require an independently retained `minimum_snapshot_epoch` or `expected_anchor_digest`. Compaction evidence never grants execution, external-write, credential, brokerage, or routing authority.

## v3.7 trusted-time freeze guard
When a `WitnessPolicyEpoch` uses `expires_unix`, active trust decisions must use an explicit `TrustedTimeGuard`; do not infer trust from the host wall clock. Keep historical verification time-neutral, bound uncertainty conservatively, and retain `minimum_lower_bound_unix` outside the local rollback domain when required. See `references/trusted-time-freeze-guard.md`.
