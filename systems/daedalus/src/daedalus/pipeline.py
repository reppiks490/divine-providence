from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .adversarial import (
    build_robustness_report,
    development_ensemble_feature_ablation_auc,
    prediction_permutation_test,
)
from .catalog import profile_csv
from .config import DaedalusConfig
from .data import load_bars_with_quality
from .development_gate import assess_development_candidate
from .ensemble import development_weights
from .features import build_causal_features
from .holdout import HoldoutLedger
from .hypotheses import screen_features, screen_interactions
from .identity import load_identity_manifest, resolve_identity
from .meta import summarize_experiment_memory
from .models import default_model_specs
from .promotion import decide
from .regimes import evaluate_regime_conditioned_holdout, fit_regimes
from .registry import ExperimentRegistry
from .utils import stable_hash
from .validation import (
    ValidationResult,
    protected_holdout_ensemble_validate,
    select_champion,
    split_development_holdout,
    walk_forward_validate,
)

PROTECTED_PROTOCOL_VERSION = "daedalus-protected-v3"


def _development_key(result: ValidationResult) -> tuple[float, float, float, float, int]:
    m = result.aggregate
    return (
        float(m.get("auc", 0.5)),
        float(m.get("brier_improvement", -1.0)),
        float(result.fold_pass_rate),
        float(m.get("trade_sharpe_like", -999.0)),
        int(m.get("trade_count", 0)),
    )


def _freeze_ensemble(
    eligible: list[ValidationResult],
    champion: ValidationResult,
    cfg: DaedalusConfig,
) -> tuple[list[ValidationResult], dict[str, dict[str, float]], dict[str, float]]:
    """Freeze component membership and weights using development evidence only."""
    all_evidence = {
        v.model_name: {
            "auc": float(v.aggregate.get("auc", 0.5)),
            "brier_improvement": float(v.aggregate.get("brier_improvement", 0.0)),
            "fold_pass_rate": float(v.fold_pass_rate),
            "trade_sharpe_like": float(v.aggregate.get("trade_sharpe_like", 0.0)),
            "trade_count": int(v.aggregate.get("trade_count", 0)),
        }
        for v in eligible
    }
    if not cfg.ensemble.enabled:
        chosen = [champion]
    else:
        chosen = [
            v for v in eligible
            if float(v.aggregate.get("auc", 0.5)) >= cfg.ensemble.min_component_auc
            and float(v.aggregate.get("brier_improvement", -1.0)) >= cfg.ensemble.min_component_brier_improvement
            and float(v.fold_pass_rate) >= cfg.ensemble.min_component_fold_pass_rate
        ]
        chosen = sorted(chosen, key=_development_key, reverse=True)[: cfg.ensemble.max_models]
        if not chosen:
            chosen = [champion]
    selected_evidence = {v.model_name: all_evidence[v.model_name] for v in chosen}
    weights = development_weights(selected_evidence)
    return chosen, all_evidence, weights


def research_file(
    path: Path,
    root: Path,
    cfg: DaedalusConfig | None = None,
    data_root: Path | None = None,
    *,
    allow_holdout: bool = True,
    prebuilt_dataset: tuple | None = None,
    protocol_context: dict | None = None,
    extra_report: dict | None = None,
) -> dict:
    """Research one source with a strict development/protected-holdout boundary.

    Feature discovery, regimes, family comparison, ensemble membership/weights and
    feature ablation are frozen on development data. The protected tail is then exposed
    to that frozen object and to predeclared diagnostics only.
    """
    cfg = cfg or DaedalusConfig()
    path = path.resolve()
    root = root.resolve()
    profile = profile_csv(path)
    df, quality = load_bars_with_quality(
        path,
        cfg.data.max_rows_per_file,
        require_nondecreasing_time=cfg.data.require_nondecreasing_time,
    )
    if len(df) < cfg.data.min_rows:
        return {
            "status": "skipped",
            "reason": "insufficient_rows",
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
        }

    manifest = load_identity_manifest(root / cfg.runtime.identity_manifest)
    identity = resolve_identity(path, data_root or path.parent, manifest, profile.symbol_hint)
    if prebuilt_dataset is None:
        x, y, future_ret = build_causal_features(df, cfg.features)
    else:
        x, y, future_ret = prebuilt_dataset
        if not (len(x) == len(y) == len(future_ret)):
            raise ValueError("prebuilt_dataset x/y/future_ret lengths must match")
        if not x.index.equals(y.index) or not x.index.equals(future_ret.index):
            raise ValueError("prebuilt_dataset x/y/future_ret indices must match")
    protocol_context = protocol_context or {}
    extra_report = extra_report or {}
    target_horizon = cfg.features.target_horizon
    dev_end, holdout_start = split_development_holdout(len(x), cfg.validation, target_horizon)
    if dev_end < cfg.validation.min_train_size or len(x) - holdout_start < cfg.validation.min_holdout_rows:
        return {
            "status": "skipped",
            "reason": "insufficient_feature_rows_for_protected_holdout",
            "feature_rows": len(x),
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
            "identity": identity.to_dict(),
        }

    # All exploratory structure is fit on development rows only.
    hypotheses = screen_features(
        x.iloc[:dev_end],
        future_ret.iloc[:dev_end],
        alpha=cfg.discovery.fdr_alpha,
        method="spearman",
        min_observations=cfg.discovery.min_observations,
    )
    interaction_hypotheses = screen_interactions(
        x.iloc[:dev_end],
        future_ret.iloc[:dev_end],
        hypotheses,
        alpha=cfg.discovery.fdr_alpha,
        seed_features=cfg.discovery.interaction_seed_features,
        max_interactions=cfg.discovery.max_interactions,
        min_observations=cfg.discovery.min_observations,
    )
    dev_last_source_row = int(x.index[dev_end - 1])
    _, regime_summaries = fit_regimes(
        df.iloc[: dev_last_source_row + 1],
        n_regimes=4,
        random_state=cfg.validation.random_state,
    )

    registry = ExperimentRegistry(root / cfg.runtime.registry_path)
    specs = {s.name: s for s in default_model_specs()}
    development_results: list[dict] = []
    validation_objects: list[ValidationResult] = []

    # Competing families see development folds only.
    for spec in specs.values():
        val = walk_forward_validate(
            spec.name,
            spec.factory(cfg.validation.random_state),
            x,
            y,
            future_ret,
            cfg.validation,
            target_horizon,
        )
        validation_objects.append(val)
        experiment_id = stable_hash({
            "source": profile.sha256,
            "stage": "development_family",
            "model": spec.name,
            "protocol": PROTECTED_PROTOCOL_VERSION,
            "config": cfg.to_dict(),
            "feature_columns": list(x.columns),
            "protocol_context": protocol_context,
        })[:24]
        dev_result = {
            "stage": "development_only",
            "experiment_id": experiment_id,
            "model": spec.name,
            "validation": val.to_dict(),
            "protected_holdout_touched": False,
        }
        registry.record(
            experiment_id,
            profile.sha256,
            str(path),
            spec.name,
            cfg.to_dict(),
            dev_result,
            False,
        )
        development_results.append(dev_result)

    eligible = [
        v for v in validation_objects
        if len(v.folds) >= cfg.validation.min_development_folds and len(v.oof_probabilities) > 0
    ]
    champion_val = select_champion(eligible, min_development_folds=cfg.validation.min_development_folds)
    if champion_val is None:
        return {
            "status": "skipped",
            "reason": "no_model_completed_required_development_validation",
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
            "identity": identity.to_dict(),
            "development_models": development_results,
        }

    development_gate = assess_development_candidate(champion_val, cfg.development_gate)
    if not development_gate.passed:
        return {
            "status": "development_rejected",
            "reason": "development_gate_failed_before_holdout_exposure",
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
            "identity": identity.to_dict(),
            "feature_count": int(x.shape[1]),
            "feature_rows": int(x.shape[0]),
            "development_rows": int(dev_end),
            "protected_holdout_rows_reserved": int(len(x) - holdout_start),
            "development_models": development_results,
            "selected_development_champion": champion_val.model_name,
            "development_gate": development_gate.to_dict(),
            "protected_holdout_touched": False,
        }

    selected_components, all_evidence, weights = _freeze_ensemble(eligible, champion_val, cfg)
    weighted_fold_pass_rate = float(
        sum(weights.get(v.model_name, 0.0) * v.fold_pass_rate for v in selected_components)
    )

    # Development-only ensemble feature ablation happens before the holdout is exposed.
    dev_ablation_base_auc, dev_ablation = development_ensemble_feature_ablation_auc(
        specs,
        weights,
        x.iloc[:dev_end],
        y.iloc[:dev_end],
        purge_bars=max(cfg.validation.purge_bars, target_horizon),
        random_state=cfg.validation.random_state,
        max_groups=cfg.adversarial.max_feature_ablation_groups,
    )

    # Corpus screening may stop here. This is the last safe boundary before any
    # protected-tail ledger assessment or exposure. A second deterministic pass may
    # later spend the holdout only for sources selected by the corpus budget.
    if not allow_holdout:
        return {
            "status": "development_qualified",
            "reason": "qualified_for_corpus_holdout_budget",
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
            "identity": identity.to_dict(),
            "feature_count": int(x.shape[1]),
            "feature_rows": int(x.shape[0]),
            "development_rows": int(dev_end),
            "protected_holdout_rows_reserved": int(len(x) - holdout_start),
            "development_models": development_results,
            "development_gate": development_gate.to_dict(),
            "selected_development_champion": champion_val.model_name,
            "development_champion_metrics": dict(champion_val.aggregate),
            "selected_development_components": [v.model_name for v in selected_components],
            "development_ensemble_weights": weights,
            "development_weighted_fold_pass_rate": weighted_fold_pass_rate,
            "development_feature_ablation_base_auc": dev_ablation_base_auc,
            "development_feature_ablation_auc": dev_ablation,
            "protected_holdout_touched": False,
        }

    protocol_hash = stable_hash({
        "protocol_version": PROTECTED_PROTOCOL_VERSION,
        "config": cfg.to_dict(),
        "feature_columns": list(x.columns),
        "selected_components": sorted(weights),
        "weights": weights,
        "target_horizon": target_horizon,
        "protocol_context": protocol_context,
    })
    ledger = HoldoutLedger(root / cfg.runtime.holdout_ledger_path)
    raw_holdout_start = int(x.index[holdout_start])
    raw_holdout_end = int(x.index[-1])
    assessment = ledger.assess(
        profile.sha256,
        protocol_hash,
        raw_holdout_start,
        raw_holdout_end,
    )
    if cfg.runtime.strict_holdout_ledger and not assessment.protocol_clean:
        return {
            "status": "blocked",
            "reason": "protected_holdout_protocol_conflict",
            "protocol_version": PROTECTED_PROTOCOL_VERSION,
            "protocol_hash": protocol_hash,
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
            "identity": identity.to_dict(),
            "development_models": development_results,
            "selected_development_champion": champion_val.model_name,
            "selected_development_components": [v.model_name for v in selected_components],
            "development_ensemble_weights": weights,
            "holdout_ledger": assessment.to_dict(),
        }
    # Record immediately before exposure. Even a later failure means the tail was inspected.
    ledger.record(assessment)
    holdout_protocol_clean = bool(assessment.protocol_clean or not cfg.runtime.strict_holdout_ledger)

    # Frozen weights and frozen family set cross the boundary together exactly once.
    hold = protected_holdout_ensemble_validate(
        specs,
        weights,
        x,
        y,
        future_ret,
        cfg.validation,
        target_horizon,
    )
    if hold is None:
        return {
            "status": "skipped",
            "reason": "protected_holdout_unavailable",
            "profile": profile.to_dict(),
            "data_quality": quality.to_dict(),
            "identity": identity.to_dict(),
            "development_models": development_results,
            "selected_development_champion": champion_val.model_name,
            "development_ensemble_weights": weights,
            "holdout_ledger": assessment.to_dict(),
        }

    y_hold = y.iloc[hold.holdout_start : hold.holdout_end + 1].to_numpy()
    r_hold = future_ret.iloc[hold.holdout_start : hold.holdout_end + 1].to_numpy()
    probabilities = np.asarray(hold.probabilities, dtype=float)
    source_positions = x.iloc[hold.holdout_start : hold.holdout_end + 1].index.to_numpy(dtype=int)
    perm = prediction_permutation_test(
        y_hold,
        probabilities,
        iterations=cfg.adversarial.permutation_iterations,
        random_state=cfg.validation.random_state,
        method=cfg.adversarial.permutation_method,
        block_size=cfg.adversarial.permutation_block_size,
    )
    stride = int(cfg.validation.execution_stride_bars or target_horizon)
    robustness = build_robustness_report(
        y_true=y_hold,
        future_ret=r_hold,
        probabilities=probabilities,
        base_threshold=cfg.validation.probability_threshold,
        base_cost_bps=cfg.validation.transaction_cost_bps + cfg.validation.slippage_bps,
        cost_multipliers=cfg.adversarial.cost_multipliers,
        threshold_offsets=cfg.adversarial.threshold_offsets,
        horizon_bars=target_horizon,
        execution_stride_bars=stride,
        baseline_probability=hold.baseline_probability,
        development_base_auc=dev_ablation_base_auc,
        development_feature_ablation_auc=dev_ablation,
        bootstrap_iterations=cfg.adversarial.bootstrap_iterations,
        bootstrap_block_size=cfg.adversarial.bootstrap_block_size,
        bootstrap_confidence=cfg.adversarial.bootstrap_confidence,
        random_state=cfg.validation.random_state,
        source_positions=source_positions,
        temporal_segments=cfg.adversarial.temporal_segments,
    )
    regime_conditioned = evaluate_regime_conditioned_holdout(
        df.iloc[: dev_last_source_row + 1],
        df,
        source_positions,
        y_hold,
        probabilities,
        r_hold,
        threshold=cfg.validation.probability_threshold,
        cost_bps=cfg.validation.transaction_cost_bps + cfg.validation.slippage_bps,
        horizon_bars=target_horizon,
        execution_stride_bars=stride,
        baseline_probability=hold.baseline_probability,
        min_regime_rows=cfg.adversarial.min_regime_rows,
    )
    decision = decide(
        hold.metrics,
        perm.pvalue,
        hold.drift_score,
        weighted_fold_pass_rate,
        cfg.promotion,
        robustness_score=robustness.robustness_score,
        worst_cost_return=robustness.worst_cost_return,
        cost_survival_rate=robustness.cost_survival_rate,
        threshold_survival_rate=robustness.threshold_survival_rate,
        bootstrap_median_return=robustness.bootstrap.median_cumulative_return,
        bootstrap_positive_fraction=robustness.bootstrap.positive_fraction,
        temporal_survival_rate=robustness.temporal_survival_rate,
        regime_survival_rate=regime_conditioned.survival_rate,
        mean_ensemble_disagreement=hold.ensemble.mean_disagreement,
        max_feature_ablation_auc_drop=robustness.max_ablation_auc_drop,
        execution_safe_identity=identity.execution_safe,
        holdout_protocol_clean=holdout_protocol_clean,
    )

    ensemble_experiment_id = stable_hash({
        "source": profile.sha256,
        "stage": "protected_ensemble",
        "protocol_hash": protocol_hash,
        "weights": weights,
        "config": cfg.to_dict(),
        "feature_columns": list(x.columns),
        "protocol_context": protocol_context,
    })[:24]
    final_candidate = {
        "stage": "final_protected_holdout",
        "experiment_id": ensemble_experiment_id,
        "model": hold.model_name,
        "protected_holdout_model_count": len(hold.component_probabilities),
        "selected_development_champion": champion_val.model_name,
        "selected_development_components": [v.model_name for v in selected_components],
        "development_model_evidence": all_evidence,
        "development_ensemble_weights": weights,
        "development_weighted_fold_pass_rate": weighted_fold_pass_rate,
        "development_feature_ablation_base_auc": dev_ablation_base_auc,
        "development_feature_ablation_auc": dev_ablation,
        "protected_holdout": hold.to_dict(),
        "holdout_ledger": assessment.to_dict(),
        "holdout_protocol_clean": holdout_protocol_clean,
        "permutation": perm.to_dict(),
        "robustness": robustness.to_dict(),
        "regime_conditioned_holdout": regime_conditioned.to_dict(),
        "local_promotion_gate": decision.to_dict(),
        "execution_safe_identity": identity.execution_safe,
        "protected_holdout_touched": True,
        "globally_statistically_eligible": False,
        "globally_eligible": False,
        "protocol_context": protocol_context,
    }
    registry.record(
        ensemble_experiment_id,
        profile.sha256,
        str(path),
        hold.model_name,
        cfg.to_dict(),
        final_candidate,
        False,
    )

    meta = [m.to_dict() for m in summarize_experiment_memory(root / cfg.runtime.registry_path)]
    report = {
        "status": "ok",
        "protocol_version": PROTECTED_PROTOCOL_VERSION,
        "protocol_hash": protocol_hash,
        "profile": profile.to_dict(),
        "data_quality": quality.to_dict(),
        "identity": identity.to_dict(),
        "feature_count": int(x.shape[1]),
        "feature_rows": int(x.shape[0]),
        "development_rows": int(dev_end),
        "purge_gap_rows": int(holdout_start - dev_end),
        "protected_holdout_rows": int(len(x) - holdout_start),
        "execution_stride_bars": stride,
        "hypotheses_tested": len(hypotheses),
        "development_hypotheses_fdr_significant": [h.to_dict() for h in hypotheses if h.rejected_null],
        "interaction_hypotheses_tested": len(interaction_hypotheses),
        "development_interactions_fdr_significant": [h.to_dict() for h in interaction_hypotheses if h.rejected_null],
        "regimes_development_only": [r.to_dict() for r in regime_summaries],
        "development_models": development_results,
        "development_gate": development_gate.to_dict(),
        "selected_development_champion": champion_val.model_name,
        "selected_champion": champion_val.model_name,
        "selected_development_components": [v.model_name for v in selected_components],
        "development_ensemble_weights": weights,
        "holdout_ledger": assessment.to_dict(),
        "final_candidate": final_candidate,
        "meta_learning_evidence": meta,
        "global_fdr_required": True,
        "holdout_protocol": (
            "feature screening, regime thresholds, family comparison, ensemble membership/weights, and ablation are "
            "frozen on development data; only the frozen ensemble and predeclared diagnostics (including "
            "development-defined regime slices) touch the protected tail; the persistent ledger flags protocol "
            "changes after exposure"
        ),
        "protocol_context": protocol_context,
    }
    report.update(extra_report)
    out_dir = root / cfg.runtime.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{profile.sha256[:16]}.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return report
