# Public-Figure Market Impact Workflow

Use this workflow to test whether a public communication or action is associated with a measurable market reaction.

1. Resolve the entity and canonical public source.
2. Normalize the event using `scripts/public_signal.py`.
3. Select a public-only acquisition plan with `scripts/social_watch_plan.py`.
4. Build the cross-asset study with `scripts/market_mover_network.py`.
5. Use one-minute data where available for intraday events and preserve exchange/session timestamps.
6. Evaluate pre-event windows for anticipation and post-event windows from 1 to 60 minutes; add multi-day windows for swing analysis.
7. Compute raw returns plus counterfactual/abnormal returns, realized volatility, volume anomalies, liquidity/spread changes where available, and cross-asset confirmation.
8. Search for competing news and scheduled releases in the same event window.
9. Feed normalized features into `scripts/attribution_score.py`.
10. Report direction, magnitude, peak reaction window, decay, affected assets, source lineage, confounders, and attribution tier.
11. Store learned event fingerprints by entity/topic without assuming future events will behave identically.

The output language must distinguish observation from inference: "market moved after", "consistent with", or "supported association" are acceptable when justified; unqualified causal language requires stronger identification than this workflow alone provides.

12. Update a point-in-time-safe impact fingerprint only after the event record is finalized. Use fingerprints to allocate monitoring attention, never as a standalone trading signal or causal forecast.
