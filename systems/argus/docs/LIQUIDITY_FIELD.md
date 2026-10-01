# ARGUS TRUE_DEPTH liquidity field

ARGUS now derives an explainable liquidity-field descriptor from the causal
DepthDynamics tensor.

The field summarizes displayed depth only. It does not claim hidden liquidity,
queue position, spoofing intent, or fill probability.

## Shape

For bid and ask depth inside the configured tensor it reports:

- total displayed depth;
- total and near-touch bid/ask imbalance;
- each side's fraction of displayed depth located inside the near-touch window;
- the difference between bid and ask near-touch shares;
- weighted depth dispersion in ticks;
- distance/depth correlation, bounded in [-1, 1].

Distance/depth correlation is descriptive:

- negative means displayed size tends to be heavier nearer the touch;
- positive means displayed size tends to grow farther from the touch;
- zero means no linear distance/depth association, including a uniform tensor.

It is not labelled convexity because that would require a separately defined
model and calibration convention.

## Temporal resilience

Using the causal replenishment/cancellation tensors already produced by
DepthDynamics, the field reports near-touch:

- persistence;
- replenishment;
- cancellation;
- resilience = replenishment - cancellation.

Resilience is bounded in [-1, 1]. Positive values mean replenishment dominated
cancellation in the selected near-touch buckets over the supplied history;
negative values mean cancellation dominated.

The field also carries the existing depth centroid, migration, and concentration
with consistency checks against the underlying depth tensor.

## Integrity

liquidity_field fails closed if:

- evidence is not TRUE_DEPTH;
- tensor lengths do not match the declared level count;
- depth is negative, non-finite, or empty on either side;
- persistence/replenishment/cancellation values fall outside [0, 1];
- stored centroid or concentration no longer matches the depth tensor;
- near-touch configuration is invalid.

These checks make a manually corrupted or incorrectly reconstructed
DepthDynamics object unsuitable for downstream use rather than silently
normalizing it.

## Causal integration

CausalMicrostructureSnapshot now contains:

- FlowDynamics;
- DepthDynamics;
- LiquidityField;
- exact trade/depth journal row hashes;
- latest source receipt timestamps;
- source staleness at the decision instant;
- execution_authorized=false;
- production_decision_authorized=false.

The default near-touch window is min(3, depth_levels) and can be overridden
explicitly.

This remains a research and observability surface. No field value grants trade,
promotion, broker, or execution authority.
