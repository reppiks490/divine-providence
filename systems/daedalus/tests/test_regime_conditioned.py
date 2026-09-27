import numpy as np
import pandas as pd

from daedalus.regimes import evaluate_regime_conditioned_holdout, fit_regime_thresholds


def _bars(n: int = 420) -> pd.DataFrame:
    rng = np.random.default_rng(4)
    ret = np.r_[rng.normal(0, 0.001, 280), rng.normal(0, 0.003, n - 280)]
    close = 100 * np.exp(np.cumsum(ret))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.maximum(0.02, close * 0.0007)
    return pd.DataFrame({
        "time": 1_700_000_000 + np.arange(n) * 60,
        "open": open_,
        "high": np.maximum(open_, close) + spread,
        "low": np.minimum(open_, close) - spread,
        "close": close,
    })


def test_regime_thresholds_are_fit_only_on_development_rows():
    df = _bars()
    dev = df.iloc[:280]
    before = fit_regime_thresholds(dev)
    mutated = df.copy()
    mutated.loc[280:, "close"] *= np.linspace(1.0, 4.0, len(mutated) - 280)
    after = fit_regime_thresholds(mutated.iloc[:280])
    assert before == after


def test_regime_conditioned_holdout_uses_frozen_predictions():
    df = _bars()
    dev = df.iloc[:280]
    pos = np.arange(300, 420)
    rng = np.random.default_rng(9)
    y = rng.integers(0, 2, len(pos))
    p = np.where(y == 1, 0.62, 0.38)
    future_ret = np.where(y == 1, 0.002, -0.002)
    report = evaluate_regime_conditioned_holdout(
        dev, df, pos, y, p, future_ret,
        threshold=0.55,
        cost_bps=1.5,
        horizon_bars=3,
        execution_stride_bars=3,
        baseline_probability=0.5,
        min_regime_rows=5,
    )
    assert report.thresholds is not None
    assert report.eligible_regimes >= 1
    assert report.survival_rate is not None
    assert all(e.regime in {"high_vol_trend", "high_vol_chop", "low_vol_trend", "low_vol_chop"} for e in report.evidence)
