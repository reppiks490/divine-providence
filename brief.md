# ICARUS research brief

Latest cycle: **complete** at 2026-11-12T15:10:22.837414Z

Memory holds 68 source/protocol experiments: 63 rejected, 3 development watch, 2 unsuitable sources, 0 interrupted computations.

This cycle tested 2 sources; 346 remain queued. 60 exact-context sources were remembered.

99 official announcements retained with first-observation times. Their market effects remain untested.

34 cross-source alignment diagnostics retained. Only exact shared unique timestamps and past row lags are allowed; missing alignment is recorded.

## Challenges and competing explanations

Lagged bar features compete against training prevalence and four existing model families. A circular-shift control challenges alignment; moving-block uncertainty challenges sampling luck; higher costs challenge friction assumptions; time slices challenge stability; fixed feature ablation challenges dependence on the return family. All reuse development evidence.

- **NASDAQ_DLY_NDX, 100T 2.csv** — rejected; selected development model: logistic. Reasons: brier_improvement, fold_pass_rate, development_block_uncertainty_includes_loss, five_times_cost_stress_failed, development_time_slice_loss. Source SHA256 `ed4c5a603efebef99da76475150708cccf8cf9f3cd4396a312cc8dc5f0247bdd`.
- **BATS_AAPL, 10.csv** — rejected; selected development model: logistic. Reasons: auc, brier_improvement, fold_pass_rate, selected_model_negative_control_failed, development_block_uncertainty_includes_loss, five_times_cost_stress_failed, development_time_slice_loss, fixed_feature_family_ablation_failed. Source SHA256 `870bdefa269f253972c5b122f8e4f529e5b75fef74d7816a601d082ce8c62dc9`.

## Authority and limits

Historical development paper proxy only. Filename symbol identity is unverified; chart prices are not execution fills. The protected tail is reserved, with no validation, promotion or broker orders. No event-price causality or live engine state is observed. A watch entry is a research lead, not a confirmed edge.

[Cycle evidence](https://github.com/reppiks490/divine-providence/actions/runs/43244472077)
