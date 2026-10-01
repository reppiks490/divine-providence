# ARGUS causal liquidity dynamics

`argus.bookmap.depth_dynamics` adds a deterministic TRUE_DEPTH feature layer
over an already causal, ordered history of market-by-price snapshots.

## Why distance-to-touch

Absolute price coordinates drift as the market moves. ARGUS therefore buckets
depth by integer tick distance from each snapshot's own best bid/best ask. A
book that translates in price without changing shape produces the same depth
tensor.

The output records:

- bid/ask depth by tick distance;
- per-bucket persistence over the supplied history;
- bounded replenishment and cancellation rates across transitions;
- depth centroid in ticks from the touch;
- latest centroid migration (toward/away from touch);
- normalized depth concentration;
- spread in ticks;
- exact event time and source-local sequence of the latest snapshot.

## Causal boundary

The function does not fetch history or decide which observations were available.
The caller must provide only snapshots available by the decision instant.
ARGUS then fails closed if the supplied history is not strictly ordered by
`(event_time_ns, sequence)`.

It also rejects:

- crossed/locked books;
- empty one-sided books;
- duplicate price levels;
- non-finite or non-positive depth;
- off-tick level geometry;
- off-tick spread geometry;
- invalid tick size or bucket count.

Every output is explicitly `EvidenceTier.TRUE_DEPTH`. Candle or inferred trade
proxies cannot enter this API by type convention alone; upstream source
capability and receipt-time causality remain the responsibility of the
authenticated ARGUS journal.

## Interpretation

Positive centroid migration means displayed liquidity moved farther from the
touch. Negative migration means it moved toward the touch.

Per-transition replenishment/cancellation uses
`abs(change) / max(previous_depth, current_depth)` for the applicable
direction and averages across transitions, so each rate remains in `[0, 1]`.

Concentration is the Herfindahl sum of normalized bucket depth. It approaches
1 when one distance bucket dominates and falls as displayed liquidity is spread
more evenly across the configured depth window.

These are descriptive research features, not fill guarantees, alpha proof, or
execution authority.
