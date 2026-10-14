"""Isolated scientific worker using DAEDALUS and ORACLE, never protected validation."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys
import time
import warnings

from .common import AUTHORITY, PROTOCOL, write_json


def research(path, root):
    # This interpreter loads just the two actual department owners; no shared
    # cross-system import path or external plugin capability is invented.
    for name in ("daedalus", "oracle"):
        sys.path.insert(0, str(Path(root) / "systems" / name / "src"))
    import numpy as np
    from daedalus.config import DaedalusConfig
    from daedalus.data import load_bars_with_quality
    from daedalus.features import build_causal_features
    from daedalus.hypotheses import screen_features
    from daedalus.models import default_model_specs
    from daedalus.validation import split_development_holdout, walk_forward_validate, select_champion
    from daedalus.development_gate import assess_development_candidate
    from daedalus.adversarial import (prediction_permutation_test, moving_block_bootstrap_evidence,
                                      cost_stress_surface, temporal_segment_evidence)
    from oracle.hypothesis_factory import Trigger, from_anomaly
    from threadpoolctl import threadpool_limits

    cfg = DaedalusConfig()
    try:
        bars, quality = load_bars_with_quality(Path(path), max_rows=None, require_nondecreasing_time=True)
    except ValueError as exc:
        return {**AUTHORITY, "outcome": "source_rejected", "reasons": [str(exc)[-1200:]],
                "models": [], "hypotheses": [], "champion": None}
    if not PROTOCOL["source_rows"][0] <= len(bars) <= PROTOCOL["source_rows"][1]:
        raise ValueError("Whole-file source exceeds registered row budget")
    x, y, ret = build_causal_features(bars, cfg.features)
    dev_end, holdout_start = split_development_holdout(len(x), cfg.validation, cfg.features.target_horizon)
    # Labels before the boundary may span five bars. Reserve that additional
    # gap exactly as the existing DAEDALUS validator does.
    screens = screen_features(x.iloc[:dev_end], ret.iloc[:dev_end])
    hypotheses = []
    stamp = time.time_ns()
    for screen in sorted(screens, key=lambda s: s.qvalue)[:12]:
        hyp = from_anomaly(Trigger("lagged_" + screen.feature, stamp, "source_bound_bar_stream",
                                   screen.statistic, 0.0, {"qvalue": screen.qvalue, "observations": screen.n}),
                           horizon="5 source bars")
        hypotheses.append({**asdict(hyp), "screen": screen.to_dict(), "stage": "exploratory_association",
                           "interpretation": "Spearman/BH screen with serial dependence; not confirmation"})
    results = []
    with threadpool_limits(limits=2):
        for spec in default_model_specs():
            model = spec.factory(cfg.validation.random_state)
            # Parallelism is a resource setting, not a scientific model change.
            if spec.name in {"random_forest", "extra_trees"}:
                model.set_params(model__n_jobs=2)
            results.append(walk_forward_validate(spec.name, model, x, y, ret,
                                                  cfg.validation, cfg.features.target_horizon))
        champion = select_champion(results, cfg.validation.min_development_folds)
        record = {**AUTHORITY, "config": cfg.to_dict(), "quality": quality.to_dict(),
                  "rows": len(bars), "feature_rows": len(x), "development_end": dev_end,
                  "holdout_start": holdout_start, "holdout_rows_reserved": len(x) - holdout_start,
                  "development_last_source_position": int(x.iloc[dev_end - 1].name) if dev_end else None,
                  "protected_first_source_position": int(x.iloc[holdout_start].name) if holdout_start < len(x) else None,
                  "hypotheses": hypotheses, "models": [r.to_dict() for r in results],
                  "stage": PROTOCOL["stage"], "price_basis": "CANDLE_PROXY"}
        if champion is None:
            return {**record, "outcome": "rejected", "reasons": ["insufficient_development_folds"], "champion": None}
        gate = assess_development_candidate(champion, cfg.development_gate).to_dict()
        h, threshold, cost = cfg.features.target_horizon, cfg.validation.probability_threshold, 1.5
        p, yy, rr, pos = (champion.oof_probabilities, champion.oof_y,
                          champion.oof_future_returns, champion.oof_positions)
        baselines = np.full(len(p), .5)
        for fold in champion.folds:
            baselines[(pos >= fold.test_start) & (pos <= fold.test_end)] = fold.baseline_probability
        permutation = prediction_permutation_test(yy, p, PROTOCOL["permutation_iterations"], block_size=h).to_dict()
        bootstrap = moving_block_bootstrap_evidence(p, rr, threshold, cost, h,
                       PROTOCOL["bootstrap_iterations"], .95, 42, source_positions=pos).to_dict()
        stress = [s.to_dict() for s in cost_stress_surface(yy, p, rr, threshold, cost,
                               PROTOCOL["cost_multipliers"], h, baseline_probability=baselines, source_positions=pos)]
        # Use per-fold training baselines when computing temporal diagnostics.
        # Calendar-regime causality is not inferred from these three time slices.
        temporal = []
        for segment in np.array_split(np.arange(len(p)), 3):
            if len(segment) < 20:
                continue
            from daedalus.metrics import evaluate_predictions
            metrics = evaluate_predictions(yy[segment], p[segment], rr[segment], threshold, cost,
                          horizon_bars=h, baseline_probability=baselines[segment], source_positions=pos[segment]).to_dict()
            temporal.append({"segment": len(temporal), "start_source_position": int(pos[segment[0]]),
                             "end_source_position": int(pos[segment[-1]]), "metrics": metrics})
        logistic = default_model_specs()[0].factory(42)
        columns = [c for c in x.columns if not c.startswith(("ret_", "mom_sign_", "ret_z_"))]
        ablation = walk_forward_validate("logistic_without_return_family", logistic, x[columns], y, ret, cfg.validation, h)
        reasons = list(gate["failed_checks"])
        # The selected family's p-value is selection biased. Bonferroni is an
        # additional conservative warning gate, not a claim of confirmation.
        if permutation["pvalue"] > .05 / len(results):
            reasons.append("selected_model_negative_control_failed")
        if bootstrap["lower_cumulative_return"] <= 0:
            reasons.append("development_block_uncertainty_includes_loss")
        if stress[-1]["metrics"]["cumulative_return"] <= 0:
            reasons.append("five_times_cost_stress_failed")
        if any(s["metrics"]["cumulative_return"] <= 0 for s in temporal):
            reasons.append("development_time_slice_loss")
        if ablation.aggregate["auc"] < .5:
            reasons.append("fixed_feature_family_ablation_failed")
        return {**record, "outcome": "rejected" if reasons else "watch", "reasons": reasons,
                "champion": champion.model_name, "development_gate": gate,
                "diagnostics": {"circular_shift": permutation, "block_bootstrap": bootstrap,
                                "cost_stress": stress, "time_slices": temporal,
                                "fixed_ablation": ablation.to_dict(),
                                "selection_bias": "same development evidence reused; unconfirmed"}}


def cross_market(left_path, right_path, root):
    sys.path.insert(0, str(root / "systems/daedalus/src"))
    from daedalus.config import DaedalusConfig
    from daedalus.data import load_bars_with_quality
    from daedalus.features import build_causal_features
    from daedalus.validation import split_development_holdout
    from daedalus.cross_asset import lead_lag_screen
    cfg = DaedalusConfig()
    streams = []
    boundaries = []
    try:
        for path in (left_path, right_path):
            bars, _ = load_bars_with_quality(path, max_rows=None)
            x, _, _ = build_causal_features(bars, cfg.features)
            dev_end, _ = split_development_holdout(len(x), cfg.validation, cfg.features.target_horizon)
            end = int(x.iloc[dev_end - 1].name) if dev_end else 0
            streams.append(bars.iloc[:end + 1])
            boundaries.append(end)
        aligned = len(set(streams[0]["time"]) & set(streams[1]["time"]))
        associations = [v.to_dict() for v in lead_lag_screen(*streams, max_lag=3)]
        return {**AUTHORITY, "state": "observed" if aligned >= 50 else "insufficient_alignment",
                "exact_shared_timestamps": aligned, "development_last_source_positions": boundaries,
                "associations": associations, "stage": "exploratory_cross_source_association",
                "interpretation": "Shared-timestamp row lags, not seconds; unverified instrument identity; no causality"}
    except ValueError as exc:
        return {**AUTHORITY, "state": "unavailable", "associations": [],
                "reason": str(exc)[-1200:], "stage": "exploratory_cross_source_association"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--peer", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        result = cross_market(args.source, args.peer, args.root) if args.peer else research(args.source, args.root)
    write_json(args.output, result)


if __name__ == "__main__":
    main()
