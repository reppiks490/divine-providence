# ARGUS TRUE_DEPTH impact and capacity curves

ARGUS now includes a deterministic displayed-depth impact model in
`argus.impact.depth_impact_curve`.

The model answers a deliberately narrow question:

> If the currently displayed opposite-side book remained unchanged while a
> hypothetical market order walked it, what displayed size, VWAP, marginal
> price and static implementation shortfall would that snapshot imply?

It does **not** claim to predict an actual future fill.

## Outputs

For each strictly increasing requested size, the model records:

- requested size;
- displayed filled size and fill fraction;
- displayed-depth VWAP;
- marginal displayed price reached;
- number of consumed price levels;
- average slippage in ticks from the best executable price;
- marginal displacement in ticks from the best price;
- implementation shortfall in ticks from midprice;
- implementation shortfall in ticks from microprice;
- whether the displayed opposite-side book was exhausted.

The curve also reports:

- best bid / ask;
- spread in ticks;
- midprice;
- top-size-weighted microprice;
- total displayed opposite-side size;
- displayed capacity available inside configured marginal-price thresholds.

`capacity_at_marginal_ticks` is intentionally a **marginal price capacity**
measure. For example, capacity at 2 ticks means displayed size available at
prices no worse than 2 ticks from the current best. It is not an average
slippage guarantee.

## Evidence and integrity boundary

The model requires a valid two-sided `BookSnapshot` and emits
`EvidenceTier.TRUE_DEPTH`.

It fails closed on:

- empty depth;
- crossed or locked books;
- duplicate price levels;
- non-finite or non-positive price/size;
- off-tick prices;
- off-tick spreads;
- invalid event time or sequence;
- invalid side;
- non-positive or non-monotone size grids;
- negative or non-monotone marginal-capacity thresholds.

## Static-book assumption

The result carries:

`assumption = "static_visible_depth_only"`

That assumption is material.

The model does **not** include:

- queue priority;
- hidden/iceberg liquidity;
- latency;
- cancellations after the snapshot;
- replenishment after the snapshot;
- adverse selection;
- temporary or permanent market impact;
- venue routing;
- fees/rebates;
- actual Icarus fills.

Displayed capacity is therefore a research feature and risk envelope, not a fill
promise.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Calibration against realized Icarus fills remains a separate later phase. Any
future calibrated execution model must preserve the raw TRUE_DEPTH snapshot,
the model revision, and realized-fill lineage rather than treating historical
candle fills as execution evidence.
