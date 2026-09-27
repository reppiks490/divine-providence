from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import roc_auc_score

from .ensemble import combine_probabilities
from .metrics import evaluate_predictions, non_overlapping_trade_pnl


@dataclass(frozen=True)
class PermutationTestResult:
    observed_auc: float
    null_mean_auc: float
    null_std_auc: float
    pvalue: float
    iterations: int
    method: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BootstrapEvidence:
    iterations: int
    confidence: float
    block_size: int
    median_cumulative_return: float
    lower_cumulative_return: float
    upper_cumulative_return: float
    positive_fraction: float
    trade_count: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class StressPoint:
    parameter: float
    metrics: dict

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TemporalSegmentEvidence:
    segment: int
    start: int
    end: int
    metrics: dict
    survived: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RobustnessReport:
    cost_surface: tuple[StressPoint, ...]
    threshold_surface: tuple[StressPoint, ...]
    development_feature_ablation_auc: dict[str, float]
    development_base_auc: float
    bootstrap: BootstrapEvidence
    temporal_segments: tuple[TemporalSegmentEvidence, ...]
    robustness_score: float
    worst_cost_return: float
    worst_threshold_sharpe_like: float
    max_development_ablation_auc_drop: float
    cost_survival_rate: float
    threshold_survival_rate: float
    temporal_survival_rate: float

    @property
    def feature_ablation_auc(self) -> dict[str, float]:
        return self.development_feature_ablation_auc

    @property
    def max_ablation_auc_drop(self) -> float:
        return self.max_development_ablation_auc_drop

    def to_dict(self) -> dict:
        return {
            "cost_surface": [x.to_dict() for x in self.cost_surface],
            "threshold_surface": [x.to_dict() for x in self.threshold_surface],
            "development_feature_ablation_auc": self.development_feature_ablation_auc,
            "development_base_auc": self.development_base_auc,
            "bootstrap": self.bootstrap.to_dict(),
            "temporal_segments": [x.to_dict() for x in self.temporal_segments],
            "robustness_score": self.robustness_score,
            "worst_cost_return": self.worst_cost_return,
            "worst_threshold_sharpe_like": self.worst_threshold_sharpe_like,
            "max_development_ablation_auc_drop": self.max_development_ablation_auc_drop,
            "cost_survival_rate": self.cost_survival_rate,
            "threshold_survival_rate": self.threshold_survival_rate,
            "temporal_survival_rate": self.temporal_survival_rate,
        }


def prediction_permutation_test(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    iterations: int = 999,
    random_state: int = 42,
    method: str = "circular_shift",
    block_size: int | None = None,
) -> PermutationTestResult:
    """Frozen-prediction significance test for a protected-holdout probability vector.

    Circular shifts preserve serial structure in the labels while breaking alignment to
    the frozen predictions. IID permutation remains available as a deliberately weaker
    diagnostic, but is not the default for market series.
    """
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    finite = np.isfinite(p)
    y, p = y[finite], p[finite]
    if len(y) < 3:
        return PermutationTestResult(0.5, 0.5, 0.0, 1.0, 0, method)
    observed = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else 0.5
    rng = np.random.default_rng(random_state)
    n_iter = max(1, int(iterations))
    null = np.empty(n_iter, dtype=float)
    for i in range(n_iter):
        if method == "circular_shift":
            step = max(1, int(block_size or 1))
            candidates = np.arange(step, len(y), step, dtype=int)
            shift = int(rng.choice(candidates)) if len(candidates) else int(rng.integers(1, len(y)))
            yp = np.roll(y, shift)
        elif method in {"iid_permutation", "frozen_prediction"}:
            yp = rng.permutation(y)
        else:
            raise ValueError(f"Unsupported permutation method: {method}")
        null[i] = float(roc_auc_score(yp, p)) if len(np.unique(yp)) > 1 else 0.5
    pvalue = float((1 + np.sum(null >= observed)) / (len(null) + 1))
    return PermutationTestResult(
        observed_auc=observed,
        null_mean_auc=float(null.mean()),
        null_std_auc=float(null.std(ddof=1)) if len(null) > 1 else 0.0,
        pvalue=pvalue,
        iterations=len(null),
        method=method,
    )


def moving_block_bootstrap_evidence(
    probabilities: np.ndarray,
    future_ret: np.ndarray,
    threshold: float,
    cost_bps: float,
    horizon_bars: int,
    iterations: int,
    confidence: float,
    random_state: int,
    *,
    block_size: int | None = None,
    execution_stride_bars: int | None = None,
    source_positions: np.ndarray | None = None,
) -> BootstrapEvidence:
    _, pnl = non_overlapping_trade_pnl(
        probabilities,
        future_ret,
        threshold,
        cost_bps,
        horizon_bars=horizon_bars,
        execution_stride_bars=execution_stride_bars,
        source_positions=source_positions,
    )
    n = len(pnl)
    if n == 0:
        return BootstrapEvidence(max(1, int(iterations)), confidence, 0, 0.0, 0.0, 0.0, 0.0, 0)
    rng = np.random.default_rng(random_state)
    block = int(block_size or round(np.sqrt(n)))
    block = max(1, min(n, block))
    vals = np.empty(max(1, int(iterations)), dtype=float)
    for i in range(len(vals)):
        sample: list[float] = []
        while len(sample) < n:
            start = int(rng.integers(0, n))
            for j in range(block):
                sample.append(float(pnl[(start + j) % n]))
                if len(sample) >= n:
                    break
        vals[i] = float(np.exp(np.sum(sample)) - 1.0)
    alpha = (1.0 - confidence) / 2.0
    return BootstrapEvidence(
        iterations=len(vals),
        confidence=float(confidence),
        block_size=block,
        median_cumulative_return=float(np.median(vals)),
        lower_cumulative_return=float(np.quantile(vals, alpha)),
        upper_cumulative_return=float(np.quantile(vals, 1.0 - alpha)),
        positive_fraction=float(np.mean(vals > 0.0)),
        trade_count=n,
    )


def cost_stress_surface(
    y_true,
    prob_up,
    future_ret,
    threshold: float,
    base_cost_bps: float,
    multipliers: Iterable[float],
    horizon_bars: int,
    execution_stride_bars: int | None = None,
    baseline_probability: float | np.ndarray | None = None,
    source_positions: np.ndarray | None = None,
) -> tuple[StressPoint, ...]:
    return tuple(
        StressPoint(
            float(mult),
            evaluate_predictions(
                y_true,
                prob_up,
                future_ret,
                threshold,
                base_cost_bps * float(mult),
                horizon_bars=horizon_bars,
                execution_stride_bars=execution_stride_bars,
                baseline_probability=baseline_probability,
                source_positions=source_positions,
            ).to_dict(),
        )
        for mult in multipliers
    )


def threshold_stress_surface(
    y_true,
    prob_up,
    future_ret,
    base_threshold: float,
    cost_bps: float,
    offsets: Iterable[float],
    horizon_bars: int,
    execution_stride_bars: int | None = None,
    baseline_probability: float | np.ndarray | None = None,
    source_positions: np.ndarray | None = None,
) -> tuple[StressPoint, ...]:
    out: list[StressPoint] = []
    for offset in offsets:
        threshold = float(np.clip(base_threshold + float(offset), 0.5001, 0.95))
        out.append(StressPoint(
            threshold,
            evaluate_predictions(
                y_true,
                prob_up,
                future_ret,
                threshold,
                cost_bps,
                horizon_bars=horizon_bars,
                execution_stride_bars=execution_stride_bars,
                baseline_probability=baseline_probability,
                source_positions=source_positions,
            ).to_dict(),
        ))
    return tuple(out)


def feature_groups(columns: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for c in columns:
        if c.startswith(("ret_", "mom_sign_", "ret_z_")):
            key = "returns_momentum"
        elif c.startswith(("rv_", "atr_bps_", "efficiency_")):
            key = "volatility_efficiency"
        elif c.startswith(("range_pos_", "breakout_")):
            key = "range_breakout"
        elif c.startswith("volume_"):
            key = "volume"
        elif c.startswith("utc_"):
            key = "calendar"
        elif c in {"time_delta", "repeat_timestamp", "backward_timestamp", "fractional_timestamp", "cadence_ratio_20"}:
            key = "bar_mechanics"
        else:
            key = "bar_geometry"
        groups.setdefault(key, []).append(c)
    return groups


def development_feature_ablation_auc(
    model,
    x_dev: pd.DataFrame,
    y_dev: pd.Series,
    *,
    purge_bars: int,
    max_groups: int,
) -> dict[str, float]:
    """Development-only feature-group ablation; never touches the protected tail."""
    n = len(x_dev)
    if n < 160 or y_dev.nunique() < 2:
        return {}
    val_size = max(80, min(500, n // 5))
    val_start = n - val_size
    train_end = max(0, val_start - max(1, int(purge_bars)))
    if train_end < 80:
        return {}
    xt, yt = x_dev.iloc[:train_end], y_dev.iloc[:train_end]
    xv, yv = x_dev.iloc[val_start:], y_dev.iloc[val_start:]
    if yt.nunique() < 2 or yv.nunique() < 2:
        return {}
    groups = list(feature_groups(list(x_dev.columns)).items())[: max(0, int(max_groups))]
    out: dict[str, float] = {}
    for name, cols in groups:
        blocked = set(cols)
        keep = [c for c in x_dev.columns if c not in blocked]
        if not keep:
            continue
        fitted = clone(model).fit(xt[keep], yt)
        p = np.asarray(fitted.predict_proba(xv[keep])[:, 1], dtype=float)
        out[name] = float(roc_auc_score(yv, p)) if yv.nunique() > 1 else 0.5
    return out


def development_ensemble_feature_ablation_auc(
    model_specs: Mapping[str, object],
    weights: Mapping[str, float],
    x_dev: pd.DataFrame,
    y_dev: pd.Series,
    *,
    purge_bars: int,
    random_state: int,
    max_groups: int,
) -> tuple[float, dict[str, float]]:
    """Development-only feature-group ablation for the frozen ensemble definition.

    A final internal validation slice is carved out of development data with a purge gap.
    The same pre-frozen component weights are used for the base and every ablation so the
    diagnostic cannot opportunistically reweight models after seeing ablation outcomes.
    """
    n = len(x_dev)
    if n < 160 or y_dev.nunique() < 2 or not weights:
        return 0.5, {}
    val_size = max(80, min(500, n // 5))
    val_start = n - val_size
    train_end = max(0, val_start - max(1, int(purge_bars)))
    if train_end < 80:
        return 0.5, {}
    xt, yt = x_dev.iloc[:train_end], y_dev.iloc[:train_end]
    xv, yv = x_dev.iloc[val_start:], y_dev.iloc[val_start:]
    if yt.nunique() < 2 or yv.nunique() < 2:
        return 0.5, {}

    selected = [name for name, w in sorted(weights.items()) if w > 0 and name in model_specs]
    if not selected:
        return 0.5, {}

    def predict(columns: list[str]) -> np.ndarray:
        probability_map: dict[str, np.ndarray] = {}
        for name in selected:
            spec = model_specs[name]
            model = spec.factory(random_state)
            fitted = clone(model).fit(xt[columns], yt)
            probability_map[name] = np.asarray(fitted.predict_proba(xv[columns])[:, 1], dtype=float)
        combined, _ = combine_probabilities(probability_map, weights)
        return combined

    full_columns = list(x_dev.columns)
    base_probabilities = predict(full_columns)
    base_auc = float(roc_auc_score(yv, base_probabilities))

    out: dict[str, float] = {}
    groups = list(feature_groups(full_columns).items())[: max(0, int(max_groups))]
    for name, blocked_columns in groups:
        blocked = set(blocked_columns)
        keep = [c for c in full_columns if c not in blocked]
        if not keep:
            continue
        probabilities = predict(keep)
        out[name] = float(roc_auc_score(yv, probabilities))
    return base_auc, out


def temporal_segment_evidence(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    future_ret: np.ndarray,
    base_threshold: float,
    base_cost_bps: float,
    horizon_bars: int,
    execution_stride_bars: int | None,
    baseline_probability: float,
    source_positions: np.ndarray,
    segments: int = 3,
) -> tuple[TemporalSegmentEvidence, ...]:
    n = min(len(y_true), len(probabilities), len(future_ret), len(source_positions))
    if n < max(60, segments * 20):
        return ()
    cuts = np.linspace(0, n, segments + 1, dtype=int)
    out: list[TemporalSegmentEvidence] = []
    for i in range(segments):
        a, b = int(cuts[i]), int(cuts[i + 1])
        if b - a < 20:
            continue
        m = evaluate_predictions(
            np.asarray(y_true)[a:b],
            np.asarray(probabilities)[a:b],
            np.asarray(future_ret)[a:b],
            base_threshold,
            base_cost_bps,
            horizon_bars=horizon_bars,
            execution_stride_bars=execution_stride_bars,
            baseline_probability=baseline_probability,
            source_positions=np.asarray(source_positions)[a:b],
        ).to_dict()
        survived = bool(m["auc"] >= 0.5 and m["brier_improvement"] >= 0.0)
        out.append(TemporalSegmentEvidence(i, a, b - 1, m, survived))
    return tuple(out)


def build_robustness_report(
    *,
    y_true: np.ndarray,
    future_ret: np.ndarray,
    probabilities: np.ndarray,
    base_threshold: float,
    base_cost_bps: float,
    cost_multipliers: Iterable[float],
    threshold_offsets: Iterable[float],
    horizon_bars: int,
    development_feature_ablation_auc: dict[str, float] | None = None,
    development_base_auc: float | None = None,
    feature_ablation_auc: dict[str, float] | None = None,
    bootstrap_iterations: int,
    bootstrap_confidence: float,
    random_state: int,
    bootstrap_block_size: int | None = None,
    execution_stride_bars: int | None = None,
    baseline_probability: float = 0.5,
    source_positions: np.ndarray | None = None,
    temporal_segments: int = 3,
) -> RobustnessReport:
    """Predeclared robustness battery over one frozen holdout prediction vector."""
    if development_feature_ablation_auc is None:
        development_feature_ablation_auc = feature_ablation_auc
    positions = np.arange(len(probabilities), dtype=int) if source_positions is None else np.asarray(source_positions, dtype=int)
    cost_surface = cost_stress_surface(
        y_true,
        probabilities,
        future_ret,
        base_threshold,
        base_cost_bps,
        cost_multipliers,
        horizon_bars,
        execution_stride_bars,
        baseline_probability,
        positions,
    )
    threshold_surface = threshold_stress_surface(
        y_true,
        probabilities,
        future_ret,
        base_threshold,
        base_cost_bps,
        threshold_offsets,
        horizon_bars,
        execution_stride_bars,
        baseline_probability,
        positions,
    )
    ablations = dict(development_feature_ablation_auc or {})
    base_auc = float(development_base_auc) if development_base_auc is not None else 0.5
    worst_cost_return = min((p.metrics["cumulative_return"] for p in cost_surface), default=0.0)
    worst_threshold_sharpe = min((p.metrics["trade_sharpe_like"] for p in threshold_surface), default=0.0)
    max_auc_drop = max((max(0.0, base_auc - auc) for auc in ablations.values()), default=0.0)
    cost_survival = float(np.mean([
        p.metrics["trade_count"] > 0 and p.metrics["cumulative_return"] > 0.0 and p.metrics["profit_factor"] > 1.0
        for p in cost_surface
    ])) if cost_surface else 0.0
    threshold_survival = float(np.mean([
        p.metrics["trade_count"] > 0 and p.metrics["cumulative_return"] > 0.0 and p.metrics["profit_factor"] > 1.0
        for p in threshold_surface
    ])) if threshold_surface else 0.0
    ablation_stability = float(np.clip(1.0 - max_auc_drop / 0.15, 0.0, 1.0))
    bootstrap = moving_block_bootstrap_evidence(
        probabilities,
        future_ret,
        base_threshold,
        base_cost_bps,
        horizon_bars,
        bootstrap_iterations,
        bootstrap_confidence,
        random_state,
        block_size=bootstrap_block_size,
        execution_stride_bars=execution_stride_bars,
        source_positions=positions,
    )
    temporal = temporal_segment_evidence(
        y_true,
        probabilities,
        future_ret,
        base_threshold,
        base_cost_bps,
        horizon_bars,
        execution_stride_bars,
        baseline_probability,
        positions,
        segments=max(1, int(temporal_segments)),
    )
    temporal_survival = float(np.mean([s.survived for s in temporal])) if temporal else 0.5
    robustness = float(np.mean([
        cost_survival,
        threshold_survival,
        ablation_stability,
        bootstrap.positive_fraction,
        temporal_survival,
    ]))
    return RobustnessReport(
        cost_surface=cost_surface,
        threshold_surface=threshold_surface,
        development_feature_ablation_auc=ablations,
        development_base_auc=base_auc,
        bootstrap=bootstrap,
        temporal_segments=temporal,
        robustness_score=robustness,
        worst_cost_return=float(worst_cost_return),
        worst_threshold_sharpe_like=float(worst_threshold_sharpe),
        max_development_ablation_auc_drop=float(max_auc_drop),
        cost_survival_rate=cost_survival,
        threshold_survival_rate=threshold_survival,
        temporal_survival_rate=temporal_survival,
    )
