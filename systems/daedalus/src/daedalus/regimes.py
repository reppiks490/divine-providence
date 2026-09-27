from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


@dataclass(frozen=True)
class RegimeSummary:
    regime_id: int
    count: int
    mean_return: float
    volatility: float
    mean_range_bps: float
    trend_efficiency: float

    def to_dict(self) -> dict:
        return asdict(self)


def regime_frame(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    ret = np.log(close / close.shift(1))
    out = pd.DataFrame(index=df.index)
    out["ret_mean_20"] = ret.rolling(20).mean()
    out["ret_vol_20"] = ret.rolling(20).std()
    out["range_bps_20"] = ((high - low).abs() / close.abs() * 10_000).rolling(20).mean()
    out["efficiency_20"] = (close - close.shift(20)).abs() / close.diff().abs().rolling(20).sum().replace(0, np.nan)
    return out.replace([np.inf, -np.inf], np.nan).dropna()


def fit_regimes(df: pd.DataFrame, n_regimes: int = 4, random_state: int = 42) -> tuple[pd.Series, list[RegimeSummary]]:
    rf = regime_frame(df)
    if len(rf) < max(100, n_regimes * 20):
        return pd.Series(dtype=int), []
    scaler = StandardScaler()
    z = scaler.fit_transform(rf)
    k = min(n_regimes, max(2, len(rf) // 50))
    model = KMeans(n_clusters=k, random_state=random_state, n_init=20)
    labels = model.fit_predict(z)
    s = pd.Series(labels, index=rf.index, name="regime")
    close = df.loc[rf.index, "close"].astype(float)
    ret = np.log(close / close.shift(1))
    summaries: list[RegimeSummary] = []
    for rid in sorted(np.unique(labels)):
        idx = s.index[s == rid]
        sub = rf.loc[idx]
        rr = ret.loc[idx].dropna()
        summaries.append(RegimeSummary(
            regime_id=int(rid), count=int(len(idx)),
            mean_return=float(rr.mean()) if len(rr) else 0.0,
            volatility=float(rr.std()) if len(rr) else 0.0,
            mean_range_bps=float(sub["range_bps_20"].mean()),
            trend_efficiency=float(sub["efficiency_20"].mean()),
        ))
    return s, summaries

@dataclass(frozen=True)
class RegimeThresholds:
    volatility_median: float
    efficiency_median: float
    fitted_rows: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RegimeHoldoutEvidence:
    regime: str
    rows: int
    metrics: dict
    survived: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RegimeConditionedReport:
    thresholds: RegimeThresholds | None
    evidence: tuple[RegimeHoldoutEvidence, ...]
    eligible_regimes: int
    survival_rate: float | None

    def to_dict(self) -> dict:
        return {
            "thresholds": None if self.thresholds is None else self.thresholds.to_dict(),
            "evidence": [x.to_dict() for x in self.evidence],
            "eligible_regimes": self.eligible_regimes,
            "survival_rate": self.survival_rate,
        }


def fit_regime_thresholds(df: pd.DataFrame) -> RegimeThresholds | None:
    """Freeze simple market-state thresholds on development data only."""
    rf = regime_frame(df)
    if len(rf) < 40:
        return None
    return RegimeThresholds(
        volatility_median=float(rf["ret_vol_20"].median()),
        efficiency_median=float(rf["efficiency_20"].median()),
        fitted_rows=int(len(rf)),
    )


def label_regime_frame(df: pd.DataFrame, thresholds: RegimeThresholds) -> pd.Series:
    """Label rows using thresholds learned elsewhere; never refits on evaluated rows."""
    rf = regime_frame(df)
    vol = np.where(rf["ret_vol_20"].to_numpy() >= thresholds.volatility_median, "high_vol", "low_vol")
    structure = np.where(rf["efficiency_20"].to_numpy() >= thresholds.efficiency_median, "trend", "chop")
    return pd.Series(np.char.add(np.char.add(vol.astype(str), "_"), structure.astype(str)), index=rf.index, name="regime_state")


def evaluate_regime_conditioned_holdout(
    development_df: pd.DataFrame,
    full_df: pd.DataFrame,
    source_positions: np.ndarray,
    y_true: np.ndarray,
    probabilities: np.ndarray,
    future_ret: np.ndarray,
    *,
    threshold: float,
    cost_bps: float,
    horizon_bars: int,
    execution_stride_bars: int,
    baseline_probability: float,
    min_regime_rows: int = 20,
) -> RegimeConditionedReport:
    """Evaluate one frozen holdout prediction vector across development-defined regimes.

    Regime boundaries are fit exclusively on development rows. Holdout states are then
    labelled without refitting, and the already-frozen prediction vector is sliced for
    diagnostics. This cannot alter model selection or ensemble weights.
    """
    from .metrics import evaluate_predictions

    thresholds = fit_regime_thresholds(development_df)
    if thresholds is None:
        return RegimeConditionedReport(None, tuple(), 0, None)
    labels = label_regime_frame(full_df, thresholds).reindex(np.asarray(source_positions, dtype=int))
    y = np.asarray(y_true, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    r = np.asarray(future_ret, dtype=float)
    pos = np.asarray(source_positions, dtype=int)
    n = min(len(labels), len(y), len(p), len(r), len(pos))
    labels = labels.iloc[:n]
    y, p, r, pos = y[:n], p[:n], r[:n], pos[:n]

    evidence: list[RegimeHoldoutEvidence] = []
    eligible_survival: list[bool] = []
    for regime in sorted(x for x in labels.dropna().unique()):
        mask = labels.to_numpy() == regime
        rows = int(mask.sum())
        metrics = evaluate_predictions(
            y[mask], p[mask], r[mask], threshold, cost_bps,
            horizon_bars=horizon_bars,
            execution_stride_bars=execution_stride_bars,
            baseline_probability=baseline_probability,
            source_positions=pos[mask],
        ).to_dict()
        eligible = rows >= int(min_regime_rows)
        survived = bool(
            eligible
            and metrics["trade_count"] > 0
            and metrics["cumulative_return"] > 0.0
            and metrics["profit_factor"] > 1.0
        )
        evidence.append(RegimeHoldoutEvidence(str(regime), rows, metrics, survived))
        if eligible:
            eligible_survival.append(survived)
    survival_rate = float(np.mean(eligible_survival)) if eligible_survival else None
    return RegimeConditionedReport(thresholds, tuple(evidence), len(eligible_survival), survival_rate)
