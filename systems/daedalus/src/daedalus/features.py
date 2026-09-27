from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig


def _safe_log_return(s: pd.Series, n: int = 1) -> pd.Series:
    s = s.astype(float).where(lambda x: x > 0)
    return np.log(s / s.shift(n))


def _utc_calendar_features(t: pd.Series) -> pd.DataFrame:
    values = pd.to_numeric(t, errors="coerce").astype(float)
    finite = values[np.isfinite(values)]
    if finite.empty:
        return pd.DataFrame(index=t.index)
    scale = float(np.nanmedian(np.abs(finite)))
    unit = "s"
    if scale > 1e17:
        unit = "ns"
    elif scale > 1e14:
        unit = "us"
    elif scale > 1e11:
        unit = "ms"
    dt = pd.to_datetime(values, unit=unit, utc=True, errors="coerce")
    out = pd.DataFrame(index=t.index)
    years = dt.dt.year.dropna()
    # Do not invent calendar structure for row counters or synthetic non-epoch timestamps.
    if years.empty or float(years.median()) < 1990 or float(years.median()) > 2100:
        return out
    hour = dt.dt.hour + dt.dt.minute / 60.0 + dt.dt.second / 3600.0
    dow = dt.dt.dayofweek.astype(float)
    out["utc_hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["utc_hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    out["utc_dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    out["utc_dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    return out


def build_predictor_features(
    df: pd.DataFrame,
    cfg: FeatureConfig,
    *,
    drop_incomplete: bool = True,
) -> pd.DataFrame:
    """Build causal predictors without constructing a target.

    This is the representation-fusion primitive: every predictor row is shifted by
    ``feature_lag_bars`` so it only contains completed source bars/events.  No future
    target is needed, which means the last rows of an auxiliary representation remain
    available for backward-only alignment to an execution stream.
    """
    if cfg.feature_lag_bars < 1:
        raise ValueError("feature_lag_bars must be >= 1 for the conservative causal contract")

    x = pd.DataFrame(index=df.index)
    close, high, low, open_ = (df[c].astype(float) for c in ("close", "high", "low", "open"))
    ret1 = _safe_log_return(close, 1)

    for w in cfg.return_windows:
        x[f"ret_{w}"] = _safe_log_return(close, w)
        x[f"mom_sign_{w}"] = np.sign(close - close.shift(w))

    true_range = pd.concat(
        [(high - low).abs(), (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1
    ).max(axis=1)
    bar_range = (high - low).replace(0, np.nan)
    x["body_frac"] = ((close - open_) / bar_range).fillna(0.0)
    x["body_abs_frac"] = ((close - open_).abs() / bar_range).fillna(0.0)
    x["upper_wick_frac"] = ((high - pd.concat([open_, close], axis=1).max(axis=1)) / bar_range).fillna(0.0)
    x["lower_wick_frac"] = ((pd.concat([open_, close], axis=1).min(axis=1) - low) / bar_range).fillna(0.0)
    x["close_location"] = ((close - low) / bar_range).fillna(0.5)
    x["gap_ret"] = np.log(open_.where(open_ > 0) / close.shift(1).where(close.shift(1) > 0))

    for w in cfg.vol_windows:
        rolling_mean = ret1.rolling(w, min_periods=w).mean()
        rolling_std = ret1.rolling(w, min_periods=w).std().replace(0, np.nan)
        x[f"rv_{w}"] = rolling_std
        x[f"atr_bps_{w}"] = true_range.rolling(w, min_periods=w).mean() / close.abs() * 10_000
        path = close.diff().abs().rolling(w, min_periods=w).sum().replace(0, np.nan)
        x[f"efficiency_{w}"] = ((close - close.shift(w)).abs() / path).fillna(0.0)
        x[f"ret_z_{w}"] = ((ret1 - rolling_mean) / rolling_std).fillna(0.0)

    for w in cfg.range_windows:
        hh = high.rolling(w, min_periods=w).max()
        ll = low.rolling(w, min_periods=w).min()
        x[f"range_pos_{w}"] = ((close - ll) / (hh - ll).replace(0, np.nan)).fillna(0.5)
        x[f"breakout_up_{w}"] = (close >= hh.shift(1)).astype(float)
        x[f"breakout_dn_{w}"] = (close <= ll.shift(1)).astype(float)

    if "volume" in df.columns:
        vol = df["volume"].astype(float)
        finite_ratio = float(vol.notna().mean()) if len(vol) else 0.0
        if finite_ratio >= 0.95 and vol.nunique(dropna=True) > 1:
            safe_log_vol = np.log1p(vol.clip(lower=0))
            for w in cfg.volume_windows:
                mu = vol.rolling(w, min_periods=w).mean()
                sd = vol.rolling(w, min_periods=w).std().replace(0, np.nan)
                x[f"volume_z_{w}"] = ((vol - mu) / sd).fillna(0.0)
                x[f"volume_change_{w}"] = safe_log_vol - safe_log_vol.shift(w)

    if cfg.include_bar_mechanics:
        t = df["time"].astype(float)
        dt = t.diff()
        rolling_dt = dt.where(dt > 0).rolling(20, min_periods=5).median()
        x["time_delta"] = dt
        x["repeat_timestamp"] = (dt == 0).astype(float)
        x["backward_timestamp"] = (dt < 0).astype(float)
        x["fractional_timestamp"] = (np.abs(t - np.round(t)) > 1e-9).astype(float)
        x["cadence_ratio_20"] = dt / rolling_dt.replace(0, np.nan)

    if cfg.include_utc_calendar:
        cal = _utc_calendar_features(df["time"])
        for c in cal.columns:
            x[c] = cal[c]

    x = x.shift(cfg.feature_lag_bars).replace([np.inf, -np.inf], np.nan)
    if not drop_incomplete:
        return x
    coverage = x.notna().mean(axis=1) if x.shape[1] else pd.Series(0.0, index=x.index)
    return x.loc[coverage >= cfg.min_row_feature_coverage].astype(float)


def build_causal_features(df: pd.DataFrame, cfg: FeatureConfig) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Build predictors and a directional close-to-close research target.

    Repeated timestamps are preserved. This single-source target is intentionally a
    research diagnostic. For execution-grade evaluation across alternate chart types,
    use ``daedalus.fusion.build_fused_dataset`` so PnL comes from an explicitly chosen
    execution-safe source.
    """
    x = build_predictor_features(df, cfg, drop_incomplete=False)
    close = df["close"].astype(float)
    future_log_return = np.log(close.shift(-cfg.target_horizon) / close)
    threshold = cfg.target_threshold_bps / 10_000.0
    if threshold > 0:
        y = pd.Series(
            np.where(
                future_log_return > threshold,
                1.0,
                np.where(future_log_return < -threshold, 0.0, np.nan),
            ),
            index=df.index,
        )
    else:
        y = (future_log_return > 0.0).astype(float)
        y[future_log_return.isna()] = np.nan
    coverage = x.notna().mean(axis=1) if x.shape[1] else pd.Series(0.0, index=x.index)
    valid = (coverage >= cfg.min_row_feature_coverage) & y.notna() & future_log_return.notna()
    return x.loc[valid].astype(float), y.loc[valid].astype(int), future_log_return.loc[valid].astype(float)
