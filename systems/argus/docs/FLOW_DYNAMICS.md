# ARGUS causal trade-flow dynamics

The `argus.flow_dynamics.flow_dynamics` layer summarizes an already causal,
ordered sequence of trade prints without granting execution authority.

## Evidence discipline

ARGUS keeps explicit aggressor-side evidence separate from inference:

- if every print carries side = +1/-1, the result is `TRUE_TRADE`;
- if any side is missing and the tick rule is used, the entire result is
  downgraded to `INFERRED_TRADE`;
- callers may set `allow_inferred=False` to fail closed instead.

This prevents inferred print direction from being silently upgraded to
authenticated trade evidence.

## Metrics

The output includes:

- buy/sell/unresolved counts and volume;
- signed volume and normalized imbalance;
- print-size concentration;
- price range, net displacement and total path length in ticks;
- directional efficiency = abs(net displacement) / total path length;
- flow/price alignment, signed by realized price direction;
- pressure-without-displacement, a descriptive bounded proxy for strong
  one-sided flow that produced little net directional efficiency;
- aggressor-side flip rate;
- maximum same-side run volume fraction;
- buy/sell VWAP and their tick gap when both sides exist;
- window duration, print rate, and volume rate.

These are descriptive microstructure features. In particular,
`pressure_without_displacement` is not labelled true absorption because a
trade-print sequence alone does not prove hidden liquidity or queue-level
absorption.

## Causal and integrity boundary

The caller must supply only prints available by the decision instant. ARGUS then
requires:

- nondecreasing event time;
- strictly increasing positive sequence identifiers when present;
- finite positive prices and sizes;
- prices aligned to the declared tick size;
- side values restricted to -1, +1, or missing.

Zero sequence means unspecified sequence and therefore does not falsely claim a
venue/source ordering guarantee.

The feature layer does not place orders, approve production promotion, or infer
broker authority.
