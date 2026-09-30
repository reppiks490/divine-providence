from __future__ import annotations
import numpy as np
import pandas as pd

def causal_bar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features at t use completed rows through t only; targets belong elsewhere."""
    if not isinstance(df,pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    required={"open","high","low","close"}
    missing=required-set(df.columns)
    if missing:
        raise ValueError(f"missing required OHLC columns: {sorted(missing)}")
    x=df.copy()
    try:
        c=pd.to_numeric(x["close"],errors="raise").astype(float)
        h=pd.to_numeric(x["high"],errors="raise").astype(float)
        l=pd.to_numeric(x["low"],errors="raise").astype(float)
        o=pd.to_numeric(x["open"],errors="raise").astype(float)
    except (TypeError,ValueError) as exc:
        raise ValueError("OHLC feature inputs must be numeric") from exc
    raw=np.column_stack([o.to_numpy(),h.to_numpy(),l.to_numpy(),c.to_numpy()])
    if np.isinf(raw).any():
        raise ValueError("OHLC feature inputs contain infinite values")
    observed_close=np.isfinite(c.to_numpy())
    if np.any(c.to_numpy()[observed_close] <= 0):
        raise ValueError("log-return features require strictly positive observed close prices")
    ret=np.log(c).diff()
    out=pd.DataFrame(index=x.index)
    out["ret_1"]=ret
    out["range_pct"]=(h-l)/c.replace(0,np.nan)
    out["body_pct"]=(c-o)/o.replace(0,np.nan)
    out["rv_20"]=ret.rolling(20,min_periods=10).std(ddof=0)*np.sqrt(20)
    out["mom_5"]=np.log(c/c.shift(5))
    out["mom_20"]=np.log(c/c.shift(20))
    true_range=pd.concat([(h-l).abs(),(h-c.shift(1)).abs(),(l-c.shift(1)).abs()],axis=1).max(axis=1)
    out["atr_pct_14"]=true_range.rolling(14,min_periods=7).mean()/c.replace(0,np.nan)
    out["eff_20"]=(c-c.shift(20)).abs()/c.diff().abs().rolling(20,min_periods=10).sum().replace(0,np.nan)
    if "volume" in {str(v).lower() for v in x.columns}:
        col=next(v for v in x.columns if str(v).lower()=="volume")
        try:
            v=pd.to_numeric(x[col],errors="raise").astype(float)
        except (TypeError,ValueError) as exc:
            raise ValueError("volume feature input must be numeric when present") from exc
        if np.isinf(v.to_numpy()).any():
            raise ValueError("volume feature input contains infinite values")
        if np.any(v.to_numpy()[np.isfinite(v.to_numpy())] < 0):
            raise ValueError("volume feature input must be non-negative when observed")
        out["volume_z_50"]=(v-v.rolling(50,min_periods=20).mean())/v.rolling(50,min_periods=20).std(ddof=0).replace(0,np.nan)
    return out
