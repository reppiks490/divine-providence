from __future__ import annotations

from dataclasses import asdict, dataclass

from .config import PromotionConfig


@dataclass(frozen=True)
class PromotionDecision:
    promoted: bool
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    execution_identity_safe: bool

    def to_dict(self) -> dict:
        return asdict(self)


def decide(
    metrics: dict,
    permutation_pvalue: float,
    drift_score: float,
    fold_pass_rate: float,
    cfg: PromotionConfig,
    *,
    robustness_score: float = 1.0,
    worst_cost_return: float = 0.0,
    cost_survival_rate: float = 1.0,
    threshold_survival_rate: float = 1.0,
    bootstrap_median_return: float = 0.0,
    bootstrap_positive_fraction: float = 1.0,
    temporal_survival_rate: float = 1.0,
    regime_survival_rate: float | None = None,
    mean_ensemble_disagreement: float = 0.0,
    max_feature_ablation_auc_drop: float = 0.0,
    execution_safe_identity: bool = True,
    holdout_protocol_clean: bool = True,
) -> PromotionDecision:
    sharpe = metrics.get("trade_sharpe_like", metrics.get("sharpe", -999.0))
    checks = {
        "auc": metrics.get("auc", 0.0) >= cfg.min_auc,
        "brier_improvement": metrics.get("brier_improvement", -1.0) >= cfg.min_brier_improvement,
        "trade_sharpe_like": sharpe >= cfg.min_trade_sharpe_like,
        "max_drawdown": metrics.get("max_drawdown", 999.0) <= cfg.max_drawdown,
        "profit_factor": metrics.get("profit_factor", 0.0) >= cfg.min_profit_factor,
        "trade_count": metrics.get("trade_count", 0) >= cfg.min_trade_count,
        "permutation_pvalue": permutation_pvalue <= cfg.max_permutation_pvalue,
        "drift": drift_score <= cfg.max_drift_score,
        "fold_pass_rate": fold_pass_rate >= cfg.min_fold_pass_rate,
        "robustness_score": robustness_score >= cfg.min_robustness_score,
        "cost_survival_rate": cost_survival_rate >= cfg.min_cost_survival_rate,
        "threshold_survival_rate": threshold_survival_rate >= cfg.min_threshold_survival_rate,
        "bootstrap_positive_fraction": bootstrap_positive_fraction >= cfg.min_bootstrap_positive_fraction,
        "temporal_survival_rate": temporal_survival_rate >= cfg.min_temporal_survival_rate,
        "ensemble_disagreement": mean_ensemble_disagreement <= cfg.max_mean_ensemble_disagreement,
        "feature_ablation_auc_drop": max_feature_ablation_auc_drop <= cfg.max_feature_ablation_auc_drop,
        "holdout_protocol_clean": bool(holdout_protocol_clean),
    }
    if regime_survival_rate is not None:
        checks["regime_survival_rate"] = regime_survival_rate >= cfg.min_regime_survival_rate
    if cfg.require_positive_worst_cost_return:
        checks["worst_cost_return"] = worst_cost_return > 0.0
    if cfg.require_positive_bootstrap_median:
        checks["bootstrap_median_return"] = bootstrap_median_return > 0.0
    if cfg.require_execution_safe_identity:
        checks["execution_safe_identity"] = bool(execution_safe_identity)
    passed = tuple(k for k, v in checks.items() if v)
    failed = tuple(k for k, v in checks.items() if not v)
    return PromotionDecision(
        promoted=not failed,
        passed=passed,
        failed=failed,
        execution_identity_safe=bool(execution_safe_identity),
    )
