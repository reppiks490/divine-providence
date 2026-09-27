# NEXUS ADAPTIVE MARKET FABRIC — BLUEPRINT v0.1

## 1. Mission

NEXUS is the missing market-data substrate beneath the existing intelligence stack. Its purpose is to turn hundreds or thousands of imperfect, overlapping, transformed, differently timed market exports into a **causal market fabric** that can be replayed deterministically and queried as though it were a synthetic exchange.

The design principle is: **preserve first, infer second, adapt third, predict nowhere by default**.

NEXUS is optimized for the CSV corpus but its contracts are transport-agnostic so later adapters can accept WebSocket, database, Parquet, broker, exchange, macro-release, real trade and depth feeds.

## 2. Non-negotiable invariants

1. Never infer data identity solely from a filename.
2. Never silently sort, deduplicate, aggregate or forward-fill raw streams to make modeling easier.
3. Preserve repeated timestamps and source-local order.
4. Source event time, availability time and ingestion time are distinct concepts whenever the source provides them.
5. A synthetic ticker at time `t` may use only observations and fitted weights available before or at `t`; model fitting for the emitted row excludes that row where feasible.
6. Candle-derived products are never labeled true trade/depth/order book evidence.
7. Exact-byte duplicates may share compute but never lose lineage.
8. Quality/confidence is explicit and cannot be substituted for predictive probability.
9. NEXUS outputs data products, factors and topology; DAEDALUS owns empirical validation and promotion.
10. NEXUS never places an order and every current cross-system packet is `production_authorized=false`.

## 3. Core architecture

### Layer A — Forensic Corpus Catalog

Scans raw CSVs recursively and records physical entry identity, SHA-256, original path, header positions, row count, timestamp anomalies, coverage, exact-byte duplicates, filename claims, inferred cadence and quality flags. macOS AppleDouble/resource-fork files are quarantined, not counted as usable streams.

Future additions: ZIP-member native cataloging without extraction, schema fingerprints, near-duplicate similarity, source-rights metadata, contract-roll metadata and authoritative identity registry.

### Layer B — Canonical Stream Identity

Every stream receives an immutable identity separate from its marketing/filename label. `venue`, `symbol`, `representation`, `claim`, `raw hash`, and source path remain distinct fields. A later reviewed registry may enrich identity without rewriting raw provenance.

### Layer C — Causal Time Kernel

Normalizes epoch precision to nanoseconds and preserves source sequence. The deterministic merge key is `(event_ns, stream_id, source_sequence)`. This is not a claim that two venues with equal clock time have a known physical ordering; it is a stable replay convention. True cross-venue ordering requires verified receive/exchange clocks and is a future adapter concern.

### Layer D — As-of State Fabric

At each replay event, NEXUS can emit an as-of state containing latest completed values, age of each stream, missing/stale sources, source sequences and lineage. Future availability-aware sources must add `available_ns`; no scheduled/revised macro outcome may be visible before its known release availability.

### Layer E — Causal Feature Plane

Produces completed-bar descriptors such as return, range, body, realized volatility, ATR percentage, efficiency, momentum and volume normalization. Features are infrastructure, not evidence of edge.

### Layer F — Adaptive Synthetic Ticker Factory

Creates internal namespace series such as:

- `NEXUS:RISK_IMPULSE`
- `NEXUS:TECH_LEADERSHIP`
- `NEXUS:VOL_COMPRESSION`
- `NEXUS:CORRELATION_BREAK`
- `NEXUS:MOMENTUM_TRANSFER`
- `NEXUS:REGIME_ENTROPY`
- `NEXUS:MARKET_STATE`

v0.1 supports trailing-only adaptive PCA, inverse-volatility and equal weighting. Weight history is itself data and must be retained. Future engines may add dynamic factor models, robust PCA, ICA, graph embeddings, Kalman filters and learned encoders **only if DAEDALUS validates incremental utility against simple baselines**.

### Layer G — Dynamic Cross-Asset Topology

Treats instruments/views as a time-varying network. v0.1 computes rolling correlation edges, absolute-weight centrality, network entropy and pairwise lag scans. Future work adds partial correlation, graphical lasso, transfer entropy candidates, Granger-style research candidates, lead/lag stability, community detection and edge survival. These are descriptive until tested forward.

### Layer H — Change / Drift Sensors

Online EWMA and CUSUM identify distributional changes in any NEXUS metric. Future expansion adds multivariate energy distance, MMD, covariance shift, Page-Hinkley, Bayesian online change-point detection and representation-level drift.

### Layer I — Quality / Missingness Intelligence

Quality is treated as a dynamic input rather than an ingestion footnote. NEXUS tracks cadence confidence, stale age, source gaps, repeated/backward time, schema integrity and later cross-source clock uncertainty. Missingness patterns can themselves become state features but never be silently imputed into truth.

### Layer J — Interoperability Contracts

NEXUS exports read-only packets:

- **AION**: observation/replay products and synthetic factor histories.
- **ARGUS**: candle-proxy context only unless authenticated trade/depth data are later routed through ARGUS evidence contracts.
- **ATHENA**: factor state, topology, quality, change/OOD ingredients. ATHENA retains supervisory interpretation/routing.
- **DAEDALUS**: research feature candidates and exact lineage. DAEDALUS retains validation, protected evidence and promotion.
- **Icarus**: no direct production execution path in v0.1.

## 4. Advanced target architecture

### 4.1 Market Fabric Ledger
Append-only event journal stored in partitioned Parquet/Arrow with content-addressed manifests. Raw CSVs remain immutable. The ledger permits replay checkpoints and exact frame hashes.

### 4.2 Multi-resolution clock lattice
Represent each stream on its native event schedule while exposing safe comparison boundaries. Do not resample non-time charts into fictional minute bars. Build synchronization policies by representation class: time bars, variable-cadence price transforms, tick/volume-like exports, macro observations, true event feeds.

### 4.3 Adaptive factor ensemble
Maintain multiple factor builders simultaneously rather than trusting one PCA. Compare stability, reconstruction, turnover, missingness sensitivity and regime persistence. Emit factor disagreement as uncertainty.

### 4.4 Causal lead/lag laboratory boundary
NEXUS can discover candidate temporal relationships, but DAEDALUS must validate them with embargo/purge, costs where relevant, stability and global false-discovery control. A lag correlation is not a causal mechanism.

### 4.5 Synthetic exchange replay
Expose a stream bus where each raw and synthetic ticker advances one event at a time. Deterministic checkpoints allow AION/ATHENA/ARGUS shadow replays against the same market instant.

### 4.6 Sensor-ablation engine
For every composite factor, rerun without one source/asset cluster and measure displacement. This directly supports AION/PARALLAX dissent and ATHENA uncertainty.

### 4.7 Data-adapter frontier
Add plugins for Parquet, Arrow, SQLite, Kafka/Redpanda, WebSocket, broker feeds, economic calendars, L1/trades and depth. True microstructure packets should be handed to ARGUS; NEXUS remains the transport/time/identity substrate.

## 5. Accuracy doctrine

“Accuracy” has four separate meanings and must not be blurred:

- **data accuracy**: identity, timestamps, values, schema, lineage
- **causal accuracy**: no future observation leaks into an as-of state
- **statistical accuracy**: calibrated out-of-sample estimates, owned by DAEDALUS/ATHENA validation protocols
- **execution accuracy**: slippage/fill/queue realism, owned by ARGUS/Icarus with real execution evidence

NEXUS v0.1 primarily improves the first two.

## 6. Scaling plan

v0.1 intentionally favors correctness and inspectability. The next implementation stage should convert catalog and stream loading to chunked/columnar processing, add persistent manifests and parallel profiling, then benchmark 10M+ rows. Optimization must preserve deterministic output hashes.
