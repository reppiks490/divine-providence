from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .hypotheses import benjamini_hochberg


@dataclass(frozen=True)
class LeadLagResult:
    lag: int
    correlation: float
    pvalue: float
    qvalue: float
    n: int

    def to_dict(self) -> dict:
        return asdict(self)


def _unique_time_returns(df: pd.DataFrame) -> pd.Series:
    if df["time"].duplicated().any():
        raise ValueError(
            "Cross-source alignment requires unique timestamps. "
            "DAEDALUS will not silently aggregate repeated-timestamp chart constructions."
        )
    close = df["close"].astype(float)
    t = df["time"].astype(float)
    s = pd.Series(close.to_numpy(), index=pd.Index(t.to_numpy(), name="time"))
    s = s.where(s > 0).dropna()
    return np.log(s / s.shift(1)).dropna()


def lead_lag_screen(
    left: pd.DataFrame,
    right: pd.DataFrame,
    max_lag: int = 10,
    alpha: float = 0.05,
) -> list[LeadLagResult]:
    """Test past right returns against current left returns on exact shared timestamps.

    Lag 0 is contemporaneous. Positive lag L means right(t-L) versus left(t).
    Negative/future lags are intentionally not computed.
    """
    l = _unique_time_returns(left).rename("left")
    r = _unique_time_returns(right).rename("right")
    joined = pd.concat([l, r], axis=1, join="inner").dropna()
    raw: list[tuple[int, float, float, int]] = []
    for lag in range(0, max_lag + 1):
        pair = pd.concat([joined["left"], joined["right"].shift(lag)], axis=1).dropna()
        if len(pair) < 50:
            continue
        stat, p = spearmanr(pair.iloc[:, 0], pair.iloc[:, 1])
        if np.isfinite(stat) and np.isfinite(p):
            raw.append((lag, float(stat), float(p), len(pair)))
    qvalues = benjamini_hochberg([x[2] for x in raw])
    return [
        LeadLagResult(lag, stat, p, q, n)
        for (lag, stat, p, n), q in zip(raw, qvalues)
        if q <= alpha
    ]


# Explicit alias retained for callers that used the earlier diagnostic name.
def aligned_lead_lag(a: pd.DataFrame, b: pd.DataFrame, max_lag: int = 10, alpha: float = 0.05) -> list[LeadLagResult]:
    return lead_lag_screen(a, b, max_lag=max_lag, alpha=alpha)
