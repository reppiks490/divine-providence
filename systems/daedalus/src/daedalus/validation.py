from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

import numpy as np
import pandas as pd
from sklearn.base import clone

from .config import ValidationConfig
from .drift import feature_drift_score
from .ensemble import EnsembleDiagnostics, combine_probabilities
from .metrics import evaluate_predictions
from .splits import PurgedWalkForwardSplit


@dataclass(frozen=True)
class FoldResult:
    fold: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    drift_score: float
    baseline_probability: float
    metrics: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    model_name: str
    folds: tuple[FoldResult, ...]
    aggregate: dict
    fold_pass_rate: float
    dev_end: int
    oof_positions: np.ndarray
    oof_y: np.ndarray
    oof_probabilities: np.ndarray
    oof_future_returns: np.ndarray

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "folds": [f.to_dict() for f in self.folds],
            "aggregate": self.aggregate,
            "fold_pass_rate": self.fold_pass_rate,
            "dev_end": self.dev_end,
            "oof_observations": int(len(self.oof_probabilities)),
        }


@dataclass(frozen=True)
class ProtectedHoldoutResult:
    model_name: str
    train_end: int
    holdout_start: int
    holdout_end: int
    baseline_probability: float
    drift_score: float
    drift_by_feature: dict[str, float]
    metrics: dict
    ensemble: EnsembleDiagnostics
    probabilities: np.ndarray
    component_probabilities: dict[str, np.ndarray]

    def to_dict(self, include_probabilities: bool = False) -> dict:
        d = {
            "model_name": self.model_name,
            "train_end": self.train_end,
            "holdout_start": self.holdout_start,
            "holdout_end": self.holdout_end,
            "baseline_probability": self.baseline_probability,
            "drift_score": self.drift_score,
            "drift_by_feature": self.drift_by_feature,
            "metrics": self.metrics,
            "ensemble": self.ensemble.to_dict(),
        }
        if include_probabilities:
            d["probabilities"] = self.probabilities.tolist()
            d["component_probabilities"] = {
                k: np.asarray(v, dtype=float).tolist() for k, v in self.component_probabilities.items()
            }
        return d


def resolve_protected_holdout_size(n_samples: int, cfg: ValidationConfig) -> int:
    if n_samples <= 0:
        return 0
    if cfg.protected_holdout_size is not None:
        size = int(cfg.protected_holdout_size)
    else:
        size = int(round(n_samples * cfg.protected_holdout_fraction))
        size = max(cfg.protected_holdout_min, size)
        size = min(cfg.protected_holdout_max, size)
    return max(cfg.min_holdout_rows, size)


def split_development_holdout(
    n_samples: int,
    cfg: ValidationConfig,
    target_horizon: int,
) -> tuple[int, int]:
    """Return exclusive development end and inclusive protected-holdout start."""
    holdout = min(n_samples, resolve_protected_holdout_size(n_samples, cfg))
    gap = max(cfg.purge_bars, target_horizon)
    holdout_start = max(0, n_samples - holdout)
    dev_end = max(0, holdout_start - gap)
    return dev_end, holdout_start


def walk_forward_validate(
    model_name: str,
    model,
    x: pd.DataFrame,
    y: pd.Series,
    future_ret: pd.Series,
    cfg: ValidationConfig,
    target_horizon: int,
) -> ValidationResult:
    """Development-only purged walk-forward validation with source-position-aware PnL."""
    dev_end, _ = split_development_holdout(len(x), cfg, target_horizon)
    x_dev, y_dev, r_dev = x.iloc[:dev_end], y.iloc[:dev_end], future_ret.iloc[:dev_end]
    splitter = PurgedWalkForwardSplit(
        cfg.n_splits,
        cfg.min_train_size,
        cfg.test_size,
        max(cfg.purge_bars, target_horizon),
        cfg.embargo_bars,
    )
    out: list[FoldResult] = []
    all_y: list[np.ndarray] = []
    all_p: list[np.ndarray] = []
    all_r: list[np.ndarray] = []
    all_pos: list[np.ndarray] = []
    all_base: list[np.ndarray] = []
    stride = int(cfg.execution_stride_bars or target_horizon)

    for i, fold in enumerate(splitter.split(len(x_dev))):
        # Enforce the purge in original source-row coordinates as well as compressed
        # feature-row coordinates. This matters when a target deadband removes rows.
        raw_test_positions = x_dev.iloc[fold.test_idx].index.to_numpy(dtype=int)
        if len(raw_test_positions) == 0:
            continue
        raw_cutoff = int(raw_test_positions[0]) - max(cfg.purge_bars, target_horizon)
        raw_train_positions = x_dev.iloc[fold.train_idx].index.to_numpy(dtype=int)
        safe_train_idx = fold.train_idx[raw_train_positions <= raw_cutoff]
        if len(safe_train_idx) < cfg.min_train_size:
            continue
        xt, xv = x_dev.iloc[safe_train_idx], x_dev.iloc[fold.test_idx]
        yt, yv = y_dev.iloc[safe_train_idx], y_dev.iloc[fold.test_idx]
        rv = r_dev.iloc[fold.test_idx]
        if yt.nunique() < 2 or yv.nunique() < 2:
            continue
        fitted = clone(model).fit(xt, yt)
        p = np.asarray(fitted.predict_proba(xv)[:, 1], dtype=float)
        baseline = float(yt.mean())
        metrics = evaluate_predictions(
            yv.to_numpy(),
            p,
            rv.to_numpy(),
            cfg.probability_threshold,
            cfg.transaction_cost_bps + cfg.slippage_bps,
            horizon_bars=target_horizon,
            execution_stride_bars=stride,
            baseline_probability=baseline,
            source_positions=x_dev.index.to_numpy(dtype=int)[fold.test_idx],
        ).to_dict()
        drift, _ = feature_drift_score(xt, xv)
        out.append(FoldResult(
            fold=i,
            train_start=int(xt.index[0]),
            train_end=int(xt.index[-1]),
            test_start=int(xv.index[0]),
            test_end=int(xv.index[-1]),
            drift_score=float(drift),
            baseline_probability=baseline,
            metrics=metrics,
        ))
        all_y.append(yv.to_numpy())
        all_p.append(p)
        all_r.append(rv.to_numpy())
        all_pos.append(x_dev.index.to_numpy(dtype=int)[fold.test_idx].copy())
        all_base.append(np.full(len(yv), baseline, dtype=float))

    yy = np.concatenate(all_y) if all_y else np.array([], dtype=int)
    pp = np.concatenate(all_p) if all_p else np.array([], dtype=float)
    rr = np.concatenate(all_r) if all_r else np.array([], dtype=float)
    positions = np.concatenate(all_pos) if all_pos else np.array([], dtype=int)
    baselines = np.concatenate(all_base) if all_base else np.array([], dtype=float)
    aggregate = evaluate_predictions(
        yy,
        pp,
        rr,
        cfg.probability_threshold,
        cfg.transaction_cost_bps + cfg.slippage_bps,
        horizon_bars=target_horizon,
        execution_stride_bars=stride,
        baseline_probability=baselines if len(baselines) else None,
        source_positions=positions,
    ).to_dict()
    pass_rate = float(np.mean([
        f.metrics["auc"] >= 0.5 and f.metrics["brier_improvement"] >= 0.0 for f in out
    ])) if out else 0.0
    return ValidationResult(model_name, tuple(out), aggregate, pass_rate, dev_end, positions, yy, pp, rr)


def development_selection_key(result: ValidationResult) -> tuple[float, float, float, float, int]:
    m = result.aggregate
    return (
        float(m.get("auc", 0.5)),
        float(m.get("brier_improvement", -1.0)),
        float(result.fold_pass_rate),
        float(m.get("trade_sharpe_like", -999.0)),
        int(m.get("trade_count", 0)),
    )


def eligible_development_results(
    results: list[ValidationResult] | tuple[ValidationResult, ...],
    min_development_folds: int,
) -> list[ValidationResult]:
    return [
        r for r in results
        if len(r.folds) >= int(min_development_folds) and len(r.oof_probabilities) > 0
    ]


def select_champion(
    results: list[ValidationResult] | tuple[ValidationResult, ...],
    min_development_folds: int = 1,
    **kwargs,
) -> ValidationResult | None:
    # `min_folds` is accepted only as a compatibility alias for interrupted checkpoints.
    if "min_folds" in kwargs:
        min_development_folds = int(kwargs["min_folds"])
    eligible = eligible_development_results(results, min_development_folds)
    return max(eligible, key=development_selection_key) if eligible else None


def protected_holdout_ensemble_validate(
    model_specs: Mapping[str, object],
    weights: Mapping[str, float],
    x: pd.DataFrame,
    y: pd.Series,
    future_ret: pd.Series,
    cfg: ValidationConfig,
    target_horizon: int,
) -> ProtectedHoldoutResult | None:
    """Expose the protected tail once to a development-frozen ensemble definition."""
    dev_end, holdout_start = split_development_holdout(len(x), cfg, target_horizon)
    if dev_end < cfg.min_train_size or len(x) - holdout_start < cfg.min_holdout_rows:
        return None
    x_train, y_train = x.iloc[:dev_end], y.iloc[:dev_end]
    x_test, y_test = x.iloc[holdout_start:], y.iloc[holdout_start:]
    r_test = future_ret.iloc[holdout_start:]
    if y_train.nunique() < 2 or y_test.nunique() < 2:
        return None

    component_probabilities: dict[str, np.ndarray] = {}
    for name, weight in sorted(weights.items()):
        if weight <= 0.0 or name not in model_specs:
            continue
        spec = model_specs[name]
        model = spec.factory(cfg.random_state)
        fitted = clone(model).fit(x_train, y_train)
        component_probabilities[name] = np.asarray(fitted.predict_proba(x_test)[:, 1], dtype=float)
    if not component_probabilities:
        return None

    probabilities, diagnostics = combine_probabilities(component_probabilities, weights)
    baseline = float(y_train.mean())
    source_positions = x_test.index.to_numpy(dtype=int)
    metrics = evaluate_predictions(
        y_test.to_numpy(),
        probabilities,
        r_test.to_numpy(),
        cfg.probability_threshold,
        cfg.transaction_cost_bps + cfg.slippage_bps,
        horizon_bars=target_horizon,
        execution_stride_bars=cfg.execution_stride_bars or target_horizon,
        baseline_probability=baseline,
        source_positions=source_positions,
    ).to_dict()
    drift, per_feature = feature_drift_score(x_train, x_test)
    return ProtectedHoldoutResult(
        model_name="development_weighted_ensemble",
        train_end=dev_end - 1,
        holdout_start=holdout_start,
        holdout_end=len(x) - 1,
        baseline_probability=baseline,
        drift_score=float(drift),
        drift_by_feature=per_feature,
        metrics=metrics,
        ensemble=diagnostics,
        probabilities=probabilities,
        component_probabilities=component_probabilities,
    )
