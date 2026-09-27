from __future__ import annotations
import numpy as np
import pandas as pd

def causal_bar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features at t use completed rows through t only; targets belong elsewhere."""
    x=df.copy()
    c=x["close"].astype(float)
    h=x["high"].astype(float); l=x["low"].astype(float); o=x["open"].astype(float)
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
        v=pd.to_numeric(x[col],errors="coerce")
        out["volume_z_50"]=(v-v.rolling(50,min_periods=20).mean())/v.rolling(50,min_periods=20).std(ddof=0).replace(0,np.nan)
    return out
