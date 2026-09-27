# ARGUS MICROSTRUCTURE INTELLIGENCE OS — BLUEPRINT

## Mission
ARGUS is the microstructure truth layer beside DAEDALUS, ATHENA and Icarus. Its purpose is not merely to draw a heatmap or label candles. It constructs a time-causal, evidence-tiered representation of **who is crossing the spread, where liquidity actually resides, how it changes, where auctions accept/reject price, where price displaced from institutional-scale imbalance, and what execution would plausibly cost**.

The central purity rule is absolute: **true trade/depth evidence and candle-derived proxies are different data products**. Candle-only history can still be useful, but ARGUS must never call it L2/order-book evidence.

## Capability stack

### 1. Event-normalized microstructure tape
Canonicalize trades, quotes, depth snapshots/deltas, venue IDs, exchange sequence, event time, receive time, source-local sequence and quality flags. Detect gaps, out-of-order packets, crossed/locked books and resets. Preserve same-timestamp events.

### 2. Aggressor/order-flow engine
Compute signed volume/CVD, trade imbalance, burst intensity, sweep sequences, large-print concentration, inter-arrival dynamics, trade-through behavior, absorption/exhaustion, volume-synchronized toxicity (VPIN-like research metric), and flow change-points. If aggressor side is inferred rather than supplied, downgrade the evidence tier.

### 3. Book-map / liquidity-field engine
Maintain reconstructed depth, not just snapshots. Track depth by distance from touch, queue imbalance, microprice, depth-weighted fair price, convexity/slope, liquidity walls, persistence half-life, replenishment, pulling/cancel bursts, voids, migration, and liquidity-pressure gradients.

Add **ephemeral-liquidity diagnostics** rather than definitive manipulation labels: detect displayed size that appears/disappears unusually quickly relative to historical baseline, but never assert spoofing intent from data alone.

### 4. Iceberg / replenishment research
Estimate latent replenishment when executed volume repeatedly consumes visible size while the displayed queue refreshes at a level. Require event-quality and venue semantics; output probability/evidence, not certainty.

### 5. Auction-market engine
Build session/rolling volume profiles, POC/value areas, HVN/LVN, acceptance/rejection, excess tails, single-print/low-volume traversals, balance/imbalance states, failed auctions, opening type, and migration of value.

### 6. Empirical order-block lifecycle
Replace subjective boxes with scored candidates. A candidate should incorporate:
- pre-origin compression/balance
- departure displacement normalized by volatility
- signed flow alignment / aggressive participation
- depth vacuum or liquidity migration after departure
- structural break and follow-through
- revisit timing and penetration
- rejection/absorption on mitigation
- survival/invalidation state
- cross-timeframe/representation agreement

Order blocks are **hypotheses with lifecycle state**, not permanent rectangles. Track CREATED -> CONFIRMED -> TESTED -> WEAKENED -> INVALIDATED/EXPIRED.

### 7. Liquidity-event engine
Detect stop-run/sweep-like events descriptively: penetration of prior liquidity, aggressive burst, rapid rejection or acceptance, depth depletion/replenishment, and subsequent auction behavior. Avoid claims about trader intent.

### 8. Impact / execution simulator
Use real depth to walk the book, model spread crossing, queue position, partial fills, latency, replenishment uncertainty, temporary/permanent impact, and size-dependent slippage. Historical candle fills are never a substitute for depth-aware execution evidence.

### 9. Multi-venue / synthetic-book layer
When data permit, normalize tick sizes and timestamps across venues, distinguish lit vs synthetic liquidity, detect venue fragmentation and lead/lag, and estimate executable consolidated depth. Keep venue provenance.

### 10. Cross-representation fusion
ARGUS can consume your alternate chart constructions as additional context, but their evidence tier remains separate. Use DAEDALUS-style identity/provenance. Never align repeated timestamps ambiguously; require sequence/order metadata or an explicit causal alignment rule.

### 11. Change-point and anomaly layer
Detect shifts in spread, depth, cancellation rate, trade intensity, toxicity, price impact, book shape and queue imbalance. Feed these to ATHENA as state/OOD inputs.

### 12. Microstructure expert outputs
Export explainable feature packets rather than direct live orders:
```text
flow_pressure
book_pressure
liquidity_void_risk
absorption_probability
replenishment_probability
auction_state
order_block_state + score
impact_curve
expected_slippage
execution_quality
evidence_tier + quality flags + lineage
```

## Advanced build roadmap

- **Phase 0 (included starter):** evidence-tier contracts, true trade stats, true-depth book stats/microprice, candle proxy firewall, auction profile primitive, order-block scoring primitive, simple book-walk execution estimate.
- **Phase 1:** event journal + order-book reconstruction from deltas; deterministic replay and gap handling.
- **Phase 2:** persistent heatmap tensors, depth decay/persistence, cancellation/replenishment, queue models.
- **Phase 3:** order-flow burst/sweep/absorption/exhaustion and toxicity suite.
- **Phase 4:** empirical order-block lifecycle with survival analysis and event-study validation.
- **Phase 5:** calibrated impact/queue/fill simulator and latency scenarios.
- **Phase 6:** cross-venue + cross-representation fusion; feed ARGUS state into ATHENA and validated features into DAEDALUS research.
- **Phase 7:** shadow integration with Icarus. No broker authority; compare forecasted vs realized slippage, liquidity and block reactions.

## Validation doctrine

1. Event replay must be deterministic.
2. No future depth/trades can leak into a feature timestamp.
3. Every feature records evidence tier and source lineage.
4. Proxy-only runs can never pass true-depth capability tests.
5. Order-block thresholds are selected on development data and evaluated on later untouched events.
6. Impact models are validated against realized fills, not just mid-price movement.
7. Cross-venue clocks need explicit synchronization/error budgets.
8. Same-timestamp event ordering uses exchange/source sequence; never arbitrary sorting.
9. Missing/gapped book state triggers uncertainty/invalidity, not silent forward filling.
10. ARGUS exports advisories/features only; Icarus owns order placement.
