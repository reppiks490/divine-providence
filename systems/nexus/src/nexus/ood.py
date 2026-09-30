from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class OODPoint:
    timestamp:object
    score:float
    dimension:int
    threshold:float
    ood:bool

class RollingMahalanobisOOD:
    """Trailing-only multivariate OOD sensor with ridge-stabilized covariance.

    Score at row i is computed from rows strictly before i. This is state telemetry,
    not a calibrated trading probability.
    """
    def __init__(self,window:int=250,min_periods:int=80,ridge:float=1e-3,threshold:float=4.0):
        if int(min_periods)<2 or int(window)<int(min_periods):
            raise ValueError("require window >= min_periods >= 2")
        if float(ridge)<=0:
            raise ValueError("ridge must be positive")
        if float(threshold)<=0:
            raise ValueError("threshold must be positive")
        self.window=int(window);self.min_periods=int(min_periods);self.ridge=float(ridge);self.threshold=float(threshold)

    def score(self,frame:pd.DataFrame)->pd.DataFrame:
        x=frame.astype(float); rows=[]
        for i in range(len(x)):
            if i<self.min_periods:continue
            hist=x.iloc[max(0,i-self.window):i].dropna(how="all")
            cur=x.iloc[i]
            common=[c for c in x.columns if cur.get(c)==cur.get(c) and hist[c].notna().sum()>=self.min_periods]
            if not common:continue
            h=hist[common].dropna()
            if len(h)<self.min_periods:continue
            mu=h.mean().to_numpy(float); arr=h.to_numpy(float)
            cov=np.cov(arr,rowvar=False);cov=np.atleast_2d(cov)
            scale=np.diag(cov).copy(); scale=np.where(scale>1e-12,scale,1.0)
            cov=cov+np.diag(scale*self.ridge)
            inv=np.linalg.pinv(cov); d=cur[common].to_numpy(float)-mu
            md2=float(d@inv@d); score=math.sqrt(max(0.0,md2)/max(1,len(common)))
            rows.append((x.index[i],score,len(common),self.threshold,score>=self.threshold))
        return pd.DataFrame(rows,columns=["time","ood_score","dimension","threshold","ood"]).set_index("time") if rows else pd.DataFrame(columns=["ood_score","dimension","threshold","ood"])

class KernelShiftSensor:
    """Small deterministic RBF-MMD-style two-window drift sensor."""
    def __init__(self,window:int=80,min_periods:int=40,gamma:float|None=None):
        if int(min_periods)<2 or int(window)<int(min_periods):
            raise ValueError("require window >= min_periods >= 2")
        if gamma is not None and float(gamma)<=0:
            raise ValueError("gamma must be positive or None")
        self.window=int(window);self.min_periods=int(min_periods);self.gamma=None if gamma is None else float(gamma)

    @staticmethod
    def _rbf(a,b,gamma):
        d=((a[:,None,:]-b[None,:,:])**2).sum(axis=2)
        return np.exp(-gamma*d)

    def score_at_end(self,frame:pd.DataFrame)->float:
        x=frame.astype(float).dropna()
        if len(x)<2*self.min_periods:return float("nan")
        b=x.tail(self.window).to_numpy(float);a=x.iloc[-2*self.window:-self.window].to_numpy(float)
        if len(a)<self.min_periods or len(b)<self.min_periods:return float("nan")
        z=np.vstack([a,b]); sd=np.std(z,axis=0); sd=np.where(sd>1e-12,sd,1.0)
        a=(a-np.mean(z,axis=0))/sd;b=(b-np.mean(z,axis=0))/sd
        gamma=self.gamma if self.gamma is not None else 1/max(1,a.shape[1])
        kaa=self._rbf(a,a,gamma);kbb=self._rbf(b,b,gamma);kab=self._rbf(a,b,gamma)
        return float(max(0.0,kaa.mean()+kbb.mean()-2*kab.mean()))
