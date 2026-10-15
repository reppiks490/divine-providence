# ICARUS research brief

Latest cycle: **complete** at 2026-10-15T11:26:04.912121Z

Memory holds 10 source/protocol experiments: 8 rejected, 2 development watch, 0 unsuitable sources, 0 interrupted computations.

This cycle tested 2 sources; 404 remain queued. 2 exact-context sources were remembered.

61 official announcements retained with first-observation times. Their market effects remain untested.

5 cross-source alignment diagnostics retained. Only exact shared unique timestamps and past row lags are allowed; missing alignment is recorded.

## Challenges and competing explanations

Lagged bar features compete against training prevalence and four existing model families. A circular-shift control challenges alignment; moving-block uncertainty challenges sampling luck; higher costs challenge friction assumptions; time slices challenge stability; fixed feature ablation challenges dependence on the return family. All reuse development evidence.

- **BITSTAMP_BTCUSD, 1D.csv** — rejected; selected development model: extra_trees. Reasons: fold_pass_rate, selected_model_negative_control_failed, development_block_uncertainty_includes_loss, development_time_slice_loss. Source SHA256 `3db876cb1ab63d0b2ab7b754c64c9f1adf7b120a836c3ff117465ae702e62c47`.
- **LSE_DLY_MAG7, 60.csv** — rejected; selected development model: hist_gradient_boosting. Reasons: brier_improvement, fold_pass_rate, selected_model_negative_control_failed, development_block_uncertainty_includes_loss, five_times_cost_stress_failed, development_time_slice_loss, fixed_feature_family_ablation_failed. Source SHA256 `794e98517f58c44533b80957e60fd8f2b9baac0ff90fd36366989810ca9e7873`.

## Authority and limits

Historical development paper proxy only. Filename symbol identity is unverified; chart prices are not execution fills. The protected tail is reserved, with no validation, promotion or broker orders. No event-price causality or live engine state is observed. A watch entry is a research lead, not a confirmed edge.

[Cycle evidence](https://github.com/reppiks490/divine-providence/actions/runs/38727062352)
