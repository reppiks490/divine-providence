from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .config import EnsembleConfig


@dataclass(frozen=True)
class EnsembleDiagnostics:
    weights: dict[str, float]
    mean_disagreement: float
    max_disagreement: float
    mean_entropy: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentPlan:
    """A holdout-blind model plan frozen entirely from development evidence."""

    mode: str
    champion: str
    selected_models: tuple[str, ...]
    weights: dict[str, float]
    evidence: dict[str, dict[str, float]]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def development_weights(evidence: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    """Create frozen model weights using development evidence only.

    The score rewards development out-of-sample discrimination, calibration improvement,
    and fold stability. Protected-holdout outcomes are never inputs.
    """
    if not evidence:
        return {}
    raw: dict[str, float] = {}
    for name, item in evidence.items():
        auc = float(item.get("auc", 0.5))
        brier = float(item.get("brier_improvement", 0.0))
        pass_rate = float(item.get("fold_pass_rate", 0.0))
        discrimination = max(auc - 0.5, 0.0)
        calibration = 1.0 + max(brier, 0.0) * 20.0
        raw[name] = max(discrimination * max(pass_rate, 0.0) * calibration, 0.0)
    total = float(sum(raw.values()))
    if total <= 0.0:
        equal = 1.0 / len(raw)
        return {name: equal for name in sorted(raw)}
    return {name: raw[name] / total for name in sorted(raw)}


def _selection_key(result: Any) -> tuple[float, float, float, float, int]:
    m = result.aggregate
    return (
        float(m.get("auc", 0.5)),
        float(m.get("brier_improvement", -1.0)),
        float(result.fold_pass_rate),
        float(m.get("trade_sharpe_like", -999.0)),
        int(m.get("trade_count", 0)),
    )


def build_development_plan(
    results: Sequence[Any],
    cfg: EnsembleConfig,
    *,
    min_development_folds: int,
) -> DevelopmentPlan | None:
    """Freeze either a development-weighted ensemble or a single champion.

    Complexity must earn its place. Only component models meeting predeclared development
    thresholds can enter the ensemble, and at most ``max_models`` are retained. If too
    few models qualify, the best validated development model becomes a one-model plan.
    """
    eligible = [
        r for r in results
        if len(r.folds) >= int(min_development_folds) and len(r.oof_probabilities) > 0
    ]
    if not eligible:
        return None

    champion = max(eligible, key=_selection_key)
    qualifying = [
        r for r in eligible
        if float(r.aggregate.get("auc", 0.5)) >= cfg.min_component_auc
        and float(r.aggregate.get("brier_improvement", -1.0)) >= cfg.min_component_brier_improvement
        and float(r.fold_pass_rate) >= cfg.min_component_fold_pass_rate
    ]
    qualifying = sorted(qualifying, key=_selection_key, reverse=True)[: int(cfg.max_models)]

    if cfg.enabled and len(qualifying) >= int(cfg.min_models_for_ensemble):
        selected = qualifying
        mode = "development_weighted_ensemble"
        reason = "multiple development-qualified model families"
    else:
        selected = [champion]
        mode = "single_development_champion"
        reason = (
            "ensemble disabled" if not cfg.enabled
            else "insufficient development-qualified components; fell back to champion"
        )

    evidence = {
        r.model_name: {
            "auc": float(r.aggregate.get("auc", 0.5)),
            "brier_improvement": float(r.aggregate.get("brier_improvement", 0.0)),
            "fold_pass_rate": float(r.fold_pass_rate),
            "trade_sharpe_like": float(r.aggregate.get("trade_sharpe_like", 0.0)),
            "trade_count": float(r.aggregate.get("trade_count", 0)),
        }
        for r in selected
    }
    weights = development_weights(evidence)
    if mode == "single_development_champion":
        weights = {champion.model_name: 1.0}

    return DevelopmentPlan(
        mode=mode,
        champion=champion.model_name,
        selected_models=tuple(r.model_name for r in selected),
        weights=weights,
        evidence=evidence,
        reason=reason,
    )


def combine_probabilities(
    probability_map: Mapping[str, np.ndarray],
    weights: Mapping[str, float],
) -> tuple[np.ndarray, EnsembleDiagnostics]:
    names = [name for name in sorted(weights) if name in probability_map and weights[name] > 0]
    if not names:
        raise ValueError("No weighted probability vectors were provided")
    lengths = {len(np.asarray(probability_map[name])) for name in names}
    if len(lengths) != 1:
        raise ValueError("Ensemble probability vectors must have equal length")
    matrix = np.column_stack([np.asarray(probability_map[name], dtype=float) for name in names])
    w = np.asarray([float(weights[name]) for name in names], dtype=float)
    if not np.isfinite(w).all() or w.sum() <= 0:
        raise ValueError("Ensemble weights must be finite and sum to a positive value")
    w = w / w.sum()
    mean_p = np.clip(matrix @ w, 1e-9, 1 - 1e-9)
    disagreement = np.std(matrix, axis=1) if len(names) > 1 else np.zeros(len(mean_p), dtype=float)
    entropy = -(mean_p * np.log(mean_p) + (1.0 - mean_p) * np.log(1.0 - mean_p)) / np.log(2.0)
    diag = EnsembleDiagnostics(
        weights={name: float(weight) for name, weight in zip(names, w)},
        mean_disagreement=float(np.mean(disagreement)) if len(disagreement) else 0.0,
        max_disagreement=float(np.max(disagreement)) if len(disagreement) else 0.0,
        mean_entropy=float(np.mean(entropy)) if len(entropy) else 0.0,
    )
    return mean_p, diag
