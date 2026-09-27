# NEXUS Adaptive Market Fabric

NEXUS is the CSV-first, source-agnostic **market-data operating layer** for the Icarus intelligence stack. It converts heterogeneous historical exports and later appendable/live sources into a deterministic, provenance-preserving market fabric, then derives adaptive synthetic tickers, cross-asset topology, OOD/change telemetry, source-health evidence and reproducible lineage without pretending filenames, transformed candles or candle proxies are execution truth.

```text
CSV / ZIP / SQLite / NPY / optional Parquet / later authenticated live feeds
                              |
                              v
                            NEXUS
                    /---------|---------\
                   v          v          v
                AION       ARGUS       ATHENA
              memory       proxy       supervisor
                   \          |          /
                    \---------v---------/
                           DAEDALUS
                           research
                              |
                              v
                     ICARUS only through
                     reviewed downstream contracts
```

NEXUS has **no broker/order authority**, does not certify predictive edge, does not call candle data L2/order flow, does not spend DAEDALUS protected holdouts, and does not create ATHENA WorldState.

## v0.3 capability surface

- forensic corpus/ZIP cataloging with raw + logical hashes, AppleDouble quarantine and schema/cadence diagnostics;
- nanosecond timestamps, repeated timestamps, event/availability/ingestion separation and strict as-of replay;
- reviewed time/event clock policies and native multi-resolution visibility lattice;
- immutable reviewed representation registry with explicit version activation;
- deterministic same-time atomic replay plus generic vector replay;
- hard integrity-gated factor admission while preserving rejected source lineage;
- representation consensus, hierarchical representation->symbol fusion and anti-duplicate universe controls;
- equal/inverse-vol/PCA/robust/shrinkage/cluster-balanced synthetic factors and ensemble uncertainty;
- rolling correlation + partial topology, communities, entropy, centrality, edge survival and lead/lag persistence;
- EWMA/CUSUM change detection, Mahalanobis OOD and kernel shift;
- single-sensor and group/sector/representation-family ablation;
- prefix-invariance future-leakage audit plus immutable causal-transform certification registry;
- dynamic quality/missingness and operational source-health/SLO telemetry;
- hash-chained ledger, NPY partitions, appendable SQLite event storage, optional streaming Parquet partitions, replay/fabric checkpoints;
- tamper-evident derivations, factor genealogy and immutable research-run manifests;
- one-instant sibling-safe routing to AION/ARGUS/ATHENA/DAEDALUS with exact contract validation.

## Verification baseline

At the SOL v0.3 handoff: NEXUS **117/117**, AION **11/11**, ARGUS **4/4**, and ATHENA **3/3** pass fresh; compileall and exact same-instant sibling contract validation pass. DAEDALUS retains a previously verified **45/45** baseline; the newest aggregate rerun exceeded this environment's execution window before completion, so it is not represented as a fresh uninterrupted pass.

The accessible historical archive is still incomplete: **238 usable streams / 1,970,753 rows** are materialized here versus AION's prior **626 usable / ~12.59M-row** checkpoint. Do not claim full ~800+ corpus coverage until reconciled.

## Start

```bash
PYTHONPATH=src python -m pytest -q -o addopts=''
python -m compileall -q src tests
nexus catalog /path/to/csv/root --json artifacts/catalog.json
```

Receiving agents should read `docs/SOL_EXTRA_HIGH_HANDOFF_V3.md`, `docs/CAPABILITY_CROSS_REFERENCE_V3.md`, `docs/VALIDATION_STATUS.md`, and `docs/BLUEPRINT.md` before extending the system.
