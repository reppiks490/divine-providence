from __future__ import annotations
import numpy as np
import pandas as pd

class TrailingNovelty:
    """Causal ridge-Mahalanobis novelty against trailing states; emits no supervisory verdict."""
    def __init__(self,window:int=250,min_periods:int=60,ridge:float=1e-3):
        if int(min_periods)<2 or int(window)<int(min_periods):
            raise ValueError("require window >= min_periods >= 2")
        if float(ridge)<=0:
            raise ValueError("ridge must be positive")
        self.window=int(window); self.min_periods=int(min_periods); self.ridge=float(ridge)

    def score(self,states:pd.DataFrame)->pd.Series:
        vals=[]
        for i in range(len(states)):
            if i<self.min_periods:
                vals.append(np.nan); continue
            hist=states.iloc[max(0,i-self.window):i].dropna()
            cur=states.iloc[i]
            if len(hist)<self.min_periods or cur.isna().any(): vals.append(np.nan); continue
            mu=hist.mean().to_numpy(float); x=cur.to_numpy(float)-mu
            cov=np.cov(hist.to_numpy(float),rowvar=False)
            if np.ndim(cov)==0: cov=np.array([[float(cov)]])
            scale=float(np.trace(cov)/max(1,cov.shape[0]))
            inv=np.linalg.pinv(cov+np.eye(cov.shape[0])*max(self.ridge*scale,1e-12))
            vals.append(float(np.sqrt(max(0.0,x@inv@x))))
        return pd.Series(vals,index=states.index,name='novelty')
