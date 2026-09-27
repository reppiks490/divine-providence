SuperMesh-X v0.8.0 — Adaptive Capability Director

# SuperMesh-X

**Candidate package version: 3.7.0**  
**Protected stable rollback baseline: v3.1.0 until independent MASTER LOOP GOVERNOR promotion.**

A cross-runtime capability mesh for ChatGPT, Codex, and Claude. SuperMesh-X treats plugins/providers as replaceable adapters, not as the architecture.


## v0.8.0 — Adaptive Capability Director

v0.8.0 adds runtime tool-surface fingerprints, compatibility-aware schema drift detection, compact discovery receipts, capability-specific provider feedback, and automatic replacement planning. The mesh can compare a provider's current tool surface with its last known snapshot, distinguish compatible additions from breaking removals or required-parameter changes, preserve an audit receipt of what discovery exposed or withheld, and reroute a capability when the active provider becomes incompatible or unhealthy.

The adaptive layer never treats newly discovered tools as automatically trusted. Runtime state, transport/auth compatibility, circuit-breaker state, private-source boundaries, and write-authority rules are still enforced before a provider can be selected. Provider feedback is learned per capability rather than as one global score so a source may be strong for one task and weak for another.

## v0.7.0 — Unified Provider & Broker Fabric

v0.7.0 consolidates the previously named plugin/skill ecosystem into one capability registry and adds portable integrations for Interactive Brokers, Forex Factory, Substack, and Finances. Future prompts can invoke SuperMesh-X as the orchestration surface; it resolves whichever providers are actually installed/authenticated in that runtime instead of requiring the prompt to enumerate every plugin again.

The IBKR layer covers portfolio, balances, positions, trades, contract lookup, market data, scanners, and market depth when authorized, while order-changing actions remain explicitly gated. Forex Factory adds normalized macro events, impact classes, actual/forecast/previous/revisions and structured export ingestion. Substack adds public RSS and public/authorized long-form research ingestion. The market-mover registry also expands named seeds while preserving runtime role verification and neutral market-impact analysis.

This does **not** bundle external provider credentials or silently install third-party plugins. It bundles the routing contracts, capability aliases, fallbacks, schemas, policies, and portable adapters so one SuperMesh-X invocation can coordinate the available surfaces.

## v0.5.0 — Event Fabric & Shock Graph

v0.5.0 adds a replayable event-intelligence fabric above the v0.4 market-mover layer. Public posts, official statements, breaking reports, and other authorized public signals can now be clustered into one underlying event family, committed to a hash-chained ledger, measured across assets, confidence-decayed, and reconstructed later from a strict point-in-time cutoff.

New executable capabilities include canonical event deduplication, independent-source-family counting, append-only event ledgers, cross-asset shock graphs, market-relevance-only mover prioritization, confidence decay under age/conflict, deterministic point-in-time replay bundles, and one integrated event-fabric pipeline.

## v0.4.0 — Current Event & Market-Mover Intelligence

v0.4.0 carries forward the runtime-truth, dynamic-discovery, provenance, and provider-benchmarking layers and adds a public-only event intelligence system for fast-moving market catalysts.

New executable capabilities include:
- multi-horizon event-study primitives and pre-event placebo checks
- conservative public-event attribution scoring
- strong recency weighting so breaking/current evidence outranks old analogues
- neutral geopolitical event classification and cross-asset transmission mapping
- public social/official-source watch planning for Donald Trump, Elon Musk, and dynamically resolved market-moving roles
- an Iran/Strait of Hormuz lane covering conflict, sanctions, shipping chokepoints, energy supply, diplomacy, rates, FX, volatility, equity indices, commodities, and crypto
- runtime-resolved role buckets so central-bank, Treasury/economic, energy/geopolitical, mega-cap tech, semiconductor, bank, and crypto leadership do not become stale hard-coded identities

## Core principle

Search widely, but attribute narrowly. A public post or announcement followed by a price move is not automatically causal. SuperMesh-X records the event clock, looks for pre-event movement, builds counterfactuals when possible, checks competing news, and reports an association tier instead of an unsupported causal claim.

## Public-source boundary

The market-mover system uses public social posts, official government/company/regulatory statements, public speeches/interviews/video, reputable news, public market data, and lawfully accessible public operational data. It does not track private physical location, private messages, or non-public account content.

## Existing mesh capabilities

SuperMesh-X also includes federated search/crawl/extraction, academic retrieval, market/fundamental/factor/macro normalization, crypto/on-chain fusion, dynamic MCP/provider discovery, circuit-breaker routing, provenance graphs, point-in-time guards, provider benchmarking, code/repository orchestration, GPU/NVIDIA routing, evidence fusion, and cross-runtime handoff.

The package never bypasses provider installation, authentication, subscriptions, rate limits, or permissions. It discovers and combines what the current runtime is actually authorized to use.


## Verification

Run `pytest -q`, `python scripts/validate_package.py`, `python -m compileall -q scripts`, and `python scripts/smoke_check.py` before packaging or handing off a modified build.


## v0.6 unified integrations
SuperMesh-X now includes one integration registry for the previously accumulated research/search, market/quant, crypto/on-chain, orchestration, study/media and skill-discovery providers, plus dedicated external adapters for Interactive Brokers, Substack and Forex Factory. Runtime availability is always checked before use. IBKR read-only market/account access is separated from explicit-confirmation order actions.


## v0.7.0 Private Intelligence Bus & Portfolio Shock Overlay
Adds Gmail private email/newsletter/attachment ingestion, Finances private portfolio/account context, strict private-to-public routing guards, and descriptive portfolio shock overlays.

## v0.9 Adaptive Execution Contracts

SuperMesh-X now inserts an execution-contract stage between adaptive discovery/routing and actual provider invocation. A compiled plan pins the provider and schema fingerprint, preserves ordered fallbacks, classifies authority, validates private-data routing, and records a deterministic audit digest. Read-only plans may be eligible for automatic execution after preflight; external writes and brokerage transactions always require explicit authorization. If a provider's observed schema differs from the planned fingerprint, execution stops and the provider must be rediscovered before a new plan is compiled.

## v1.0 Protocol-Era Safety & Tool Observability

SuperMesh-X now distinguishes modern MCP `2026-07-28` providers from handshake-era providers before execution. Modern requests require canonical per-request protocol metadata; legacy providers retain `initialize` compatibility. Tool annotations are normalized conservatively and are never trusted as authority unless the provider itself is trusted. Every execution contract can emit a secret-redacted `execute_tool` trace tied to its deterministic plan digest.


## v1.6.0
Adaptive provider health feedback converts freshness, schema-drift, and subscription instability into decaying health penalties, circuit-breaker state, deterministic receipts, and failover ranking.


## v1.8.0 cross-SDK conformance
Before routing through an MCP SDK, validate its protocol era/discovery behavior with `scripts.cross_sdk_conformance`. Modern 2026-07-28 requests require `server/discover` and per-request protocol metadata; legacy runtimes retain `initialize`. SDK feature assumptions (including tasks-extension support) fail closed and never grant write authority.

## v1.9.0 quota-aware half-open probes
`quota_probe_guard.py` normalizes heterogeneous provider quota signals and gates half-open circuit probes using bounded deterministic jitter, minimum quota headroom, and concurrency limits. It cannot grant write or brokerage authority.


## v2.3.0 execution-domain foundation

Before SuperMesh-X can safely scale to multiple isolated computers or a 50+ logical-agent swarm, every worker must execute inside an explicit domain contract. `scripts/execution_domain_kernel.py` adds lease/fencing ownership, resource budgets, exact capability grants, deterministic idempotency keys, content-addressed secret-free checkpoint receipts, rollback receipts, and privacy-safe trace propagation. This layer does **not** launch agents or grant external write/trading authority; it is the prerequisite safety substrate for those future runtimes.

## v2.4.0 durable execution store & isolation admission

`scripts/durable_execution_store.py` persists execution ownership, monotonic fencing, lifecycle state, CAS-protected operator actions, and secret-free checkpoint receipts across process restarts. `scripts/isolation_admission.py` adds transactional shared-capacity reservations plus capability allowlisting and opaque credential-reference enforcement. The release remains a control-plane foundation: it does not launch computers, agents, unrestricted shells, or brokerage orders.

## v2.5.0 sandbox/workspace isolation & remote-store boundary

`scripts/workspace_isolation.py` defines deny-by-default mount and network policies, argv-only terminal/process specifications, secret-redacted execution receipts, reservation-to-runtime enforcement hooks, opaque vault-broker requests, and watchdog/orphan-cleanup planning. `scripts/remote_store_adapter.py` defines a backend-neutral atomic-CAS durable-store boundary that preserves leases/fencing and refuses split-brain local fallback during remote-store failure. The release still does **not** launch computers or the 50+ agent swarm.

## v3.0 Signed Runtime Evidence
Runtime evidence may now be authenticated with provider-neutral Ed25519 envelopes before journal admission. Trust-store rotation/revocation, replay/fencing guards, and capability non-escalation preserve the separation between evidence authenticity and execution authority. See `references/signed-runtime-evidence.md`.
## v3.1 Trust/Transparency Routing
Use `scripts/trust_transparency.py` for durable public trust roots, dual-threshold sequential key rotation, Merkle inclusion proofs, and signed transparency checkpoints. Signatures authenticate evidence; they do not grant execution authority.

## v3.2 Witnessed Transparency
`WitnessedCheckpointLedger` adds independent Ed25519 witness quorum receipts, append-only legacy-tree checks, rollback/split-view rejection, witness revocation handling, and capability non-escalation. It is retained as a backward-compatible legacy surface.

## v3.3 RFC 9162 Witness Durability + Gossip
For new transparency deployments, use `scripts.witnessed_transparency.RFC9162WitnessedCheckpointLedger`. It adds RFC 9162 SHA-256 Merkle Tree Hash semantics, compact consistency paths, atomic restartable witness snapshots, and partition-recoverable gossip receipts. `GossipReceiptStore(registry=...)` authenticates witness quorum/signatures plus compact-proof digest binding before admission. The v3.2 witness API remains unchanged. See `references/rfc9162-witness-gossip.md`.


### Signed gossip replay compaction (v3.6)
For large durable gossip journals, `DurableGossipJournal.compact()` creates an immutable witness-signed snapshot plus a signed monotonic anchor entry without truncating the original journal. Use `load_compacted()` to authenticate the snapshot/anchor, verify the exact journal prefix, and replay only the suffix. For rollback detection across restoration of all local files, retain `minimum_snapshot_epoch` or `expected_anchor_digest` outside the local rollback domain. Concurrent compaction is serialized with a fail-closed per-anchor lock and stale-head check. A stale lock requires operator verification before removal. See `references/gossip-compaction.md`.

### Trusted-time witness-policy freeze guard (v3.7)
Expiring witness policies can now declare `expires_unix`. Active trust decisions use an explicit caller-supplied `TrustedTimeGuard`; SuperMesh never silently treats the host wall clock as authoritative. `DurableTrustedTimeFloor` persists a monotonic lower-bound floor, uncertainty overlapping policy expiry fails closed, and an optional external minimum detects rollback beyond the local state domain. Historical signature verification and strict forensic journal replay remain available after expiry, while new checkpoints, active gossip admission, compaction, and compacted loading require a fresh current policy. See `references/trusted-time-freeze-guard.md`.
