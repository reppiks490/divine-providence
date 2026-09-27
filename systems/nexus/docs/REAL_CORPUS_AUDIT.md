# Real Corpus Audit — Current Materialized Checkpoint

This audit is against the materialized `Full csv candles only.zip` available in this session. It is **not** the authoritative full corpus.

- Physical `.csv` entries: **476**
- Usable market CSVs: **238**
- AppleDouble/resource-fork sidecars: **238**
- Usable parsed rows: **1,970,753**
- Exact-byte duplicate entries: **7** (compute may be shared; lineage is retained)
- Fractional-timestamp streams: **12**
- Cadence-ambiguous usable streams: **64**

## Most represented symbols

- `NQ1!`: 25 streams
- `ES1!`: 24 streams
- `YM1!`: 23 streams
- `SI1!`: 20 streams
- `PL1!`: 20 streams
- `GC1!`: 19 streams
- `PA1!`: 18 streams
- `VIX`: 14 streams
- `MAG7`: 11 streams
- `BTCUSD`: 10 streams
- `DXY`: 10 streams
- `VXN`: 9 streams
- `TNX`: 9 streams
- `BTC1!`: 8 streams
- `META`: 6 streams
- `NVDA`: 5 streams
- `MSFT`: 4 streams
- `GOOGL`: 2 streams
- `SPX`: 1 streams

## Most common inferred positive cadences

- `1m`: 63 streams
- `1s`: 42 streams
- `1h`: 32 streams
- `4h`: 27 streams
- `30s`: 18 streams
- `10s`: 13 streams
- `1000000`: 12 streams
- `20m`: 11 streams
- `2h`: 9 streams
- `15s`: 5 streams
- `1d`: 4 streams
- `7d`: 1 streams
- `5s`: 1 streams

## Cross-check against sibling handoffs

AION/PARALLAX documentation from the accessible handoff reports a prior GitHub checkpoint containing 626 usable CSV entries across nine ZIPs after filtering 626 resource-fork sidecars, with 513 distinct byte contents. DAEDALUS handoff notes that the user's authoritative Work corpus is expected to exceed 800 real CSV files. Therefore NEXUS **must not claim full-corpus completion from this 238-stream materialized ZIP**. The next agent must reconcile the GitHub/Work corpus before any corpus-wide scientific claim.

## Real-data smoke

`artifacts/real_smoke.json` demonstrates NQ/ES/VIX/DXY/VXN causal alignment, adaptive factor ensemble, rolling topology, novelty and sensor-ablation on actual CSVs. It is engineering evidence only; it does not establish predictive edge.
