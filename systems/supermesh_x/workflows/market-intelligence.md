# Market intelligence workflow

1. Resolve instrument + venue + asset class.
2. Pull live/current market state from the strongest structured provider(s).
3. Pull historical context and corporate-action-adjusted data where needed.
4. Add fundamentals/research, factors/regime, rates/macro, and news only when relevant.
5. Cross-check timestamps, units, and symbol mappings.
6. For backtests, enforce point-in-time and leakage checks.
7. Report evidence and uncertainty; do not turn the workflow into automatic financial advice.
