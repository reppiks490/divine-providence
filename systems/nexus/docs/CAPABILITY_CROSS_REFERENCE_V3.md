# NEXUS v0.3 Capability Cross-Reference

NEXUS remains the market-data operating layer. It does not absorb ARGUS, ATHENA, AION, DAEDALUS, or Icarus authority.

| Capability | Owner / authority | NEXUS v0.3 state | Remaining gap |
|---|---|---|---|
| Raw corpus forensics | NEXUS | implemented: ZIP-native + extracted profiling, raw/logical hashes, schema/header positions, OHLC integrity, AppleDouble quarantine, cadence diagnostics | recover/reconcile authoritative 626/800+ corpus |
| Reviewed representation semantics | NEXUS | immutable versioned registry implemented; activation explicit; event bars cannot receive fictional fixed cadence | populate registry for every recovered stream from review evidence |
| Representation review operations | NEXUS | deterministic evidence-required review queue implemented; current 238-stream catalog yields 92 P0 and 146 P2 review candidates without inferring timestamp semantics | perform human/source-evidence review and activate immutable records |
| Stream identity | NEXUS | raw identity separated from canonical reviewed identity | enrich live venue IDs, aliases, futures rolls |
| Causal availability | NEXUS + AION semantics | event / availability / ingestion separated; unknown availability can fail closed | source-specific live/macro attestations |
| Native representation clocks | NEXUS | time/event policies + native multi-resolution lattice | full-corpus reviewed clock coverage |
| Deterministic replay | NEXUS | same-time atomic replay, vector replay, checkpoints, strict as-of state | distributed large-corpus benchmark |
| Same-instant sibling routing | NEXUS boundary | implemented: one atomic frame routes to AION/ARGUS/ATHENA/DAEDALUS with exact contract validation | production integration harness against live sibling services |
| Sibling contract drift sentinel | NEXUS boundary | raw + AST-normalized boundary fingerprints implemented; formatting-only drift separated from semantic drift | run in CI/deployment before accepting sibling contract changes |
| Persistent event fabric | NEXUS | SQLite hash ledger, NPY partitions, appendable SQLite store, streaming partitioned Parquet implementation when Arrow is installed | benchmark 12M+ rows; compaction/time-bucket policy; Arrow runtime not present here |
| Dynamic source health / SLOs | NEXUS supplies, ATHENA interprets | receive lag, gaps, reconnects, revisions, nonmonotone sequence, clock uncertainty, impossible-time evidence, fleet health plane | live feed calibration and reviewed per-source thresholds |
| Hard factor admission | NEXUS | preservation separated from modeling eligibility | source-class calibration over full corpus |
| Duplicate/representation bias control | NEXUS | byte/logical duplicates, per-symbol caps, hierarchical representation->symbol fusion | populate reviewed representation families across full corpus |
| Synthetic tickers | NEXUS | equal/inv-vol/PCA/robust/shrinkage/cluster-balanced, caps and ensembles | DAEDALUS evidence for which methods add value |
| Dynamic topology | NEXUS | correlation, ridge partial, communities, entropy, centrality, edge survival, lead/lag persistence | nonlinear/causal-network candidates remain DAEDALUS research |
| Drift/OOD | NEXUS supplies, ATHENA interprets | EWMA/CUSUM, Mahalanobis OOD, kernel shift | calibration / multivariate online families |
| Ablation / fragility | NEXUS | single-sensor and arbitrary group/sector/representation-family ablation | empirical grouping policy on full corpus |
| Future-leakage defense | NEXUS + DAEDALUS | availability checks + prefix-invariance audit + immutable causal-transform certification gate | run registry certification in CI for every promoted transform |
| Derivation lineage | NEXUS + AION | tamper-evident derivation records, factor genealogy, AION derivation observations | durable AION write-through in deployed service |
| Research-run reproducibility | NEXUS | immutable run manifest binds corpus, reviewed registry, genealogy, inputs, outputs, code, params, derivations; production authority false | wire into every DAEDALUS experiment runner |
| Historical evidence memory | AION | exact NEXUS SourceSpec/Observation/context routing validated | do not duplicate |
| True trade/depth microstructure | ARGUS | CSV/derived factors hard-limited to CANDLE_PROXY | authenticated L1/L2/trade adapters belong at ARGUS boundary |
| Supervisory world state/routing | ATHENA | provenance + quality/topology/OOD ingredients routed; advisory ownership preserved | do not duplicate |
| Scientific validation/promotion | DAEDALUS | research-candidate bridge + causal-transform engineering gate | DAEDALUS owns statistical promotion |
| Broker/execution authority | Icarus | explicitly absent | remains absent by design |

## Highest-value unresolved dependency

The dominant constraint is still **authoritative corpus recovery plus reviewed representation population**, not another modeling algorithm. Current accessible materialization is only 238 usable streams / 1,970,753 rows; AION records a prior 626-stream / ~12.59M-row checkpoint and the owner expects roughly 800+ files. NEXUS must not claim full coverage until those sources are recovered and reconciled.
