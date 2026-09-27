from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class SyntheticTickerDefinition:
    name: str
    components: tuple[str,...]
    method: str = "adaptive_pca"
    window: int = 120
    min_periods: int = 40
    rebalance_every: int = 10
    clip_z: float = 6.0
    max_component_weight: float = 1.0

class AdaptiveTickerEngine:
    """Build synthetic state series using trailing-only estimators."""
    @staticmethod
    def _normalize(w:np.ndarray)->np.ndarray:
        s=float(np.sum(np.abs(w)))
        return w/s if s>1e-15 else np.ones_like(w)/max(1,len(w))

    @classmethod
    def _cap(cls,w:np.ndarray,cap:float)->np.ndarray:
        w=cls._normalize(np.asarray(w,dtype=float))
        if cap>=1.0:return w
        if cap<=0 or cap*len(w)<1-1e-12:raise ValueError("max_component_weight is infeasible for component count")
        # Iterative absolute cap with redistribution across uncapped weights.
        sign=np.where(w<0,-1.0,1.0);a=np.abs(w)
        for _ in range(len(w)+2):
            over=a>cap+1e-15
            if not over.any():break
            excess=float((a[over]-cap).sum());a[over]=cap
            free=~over
            room=np.maximum(0.0,cap-a[free]);den=float(room.sum())
            if excess<=1e-15 or den<=1e-15:break
            a[free]+=excess*room/den
        return cls._normalize(sign*a)

    def _weights(self,hist:pd.DataFrame,method:str,max_component_weight:float=1.0)->np.ndarray:
        arr=hist.to_numpy(dtype=float)
        mu=np.nanmean(arr,axis=0);sd=np.nanstd(arr,axis=0);sd=np.where(sd<1e-12,1.0,sd)
        z=np.nan_to_num((arr-mu)/sd,nan=0.0,posinf=0.0,neginf=0.0)
        if method in {"adaptive_pca","shrinkage_pca","robust_pca"}:
            work=z
            if method=="robust_pca":
                med=np.nanmedian(arr,axis=0);mad=np.nanmedian(np.abs(arr-med),axis=0);scale=np.where(mad>1e-12,1.4826*mad,sd)
                work=np.clip(np.nan_to_num((arr-med)/scale,nan=0.0),-5.0,5.0)
            cov=np.atleast_2d(np.cov(work,rowvar=False))
            if method in {"shrinkage_pca","robust_pca"}:
                alpha=0.25 if method=="shrinkage_pca" else 0.35
                cov=(1-alpha)*cov+alpha*np.diag(np.diag(cov))
            vals,vecs=np.linalg.eigh(cov);w=vecs[:,int(np.argmax(vals))]
            j=int(np.argmax(np.abs(w)))
            if w[j]<0:w=-w
        elif method=="inverse_vol":
            vol=np.nanstd(arr,axis=0);w=1/np.maximum(vol,1e-12)
        elif method=="equal":w=np.ones(arr.shape[1])
        elif method=="cluster_balanced":
            corr=np.nan_to_num(np.corrcoef(z,rowvar=False),nan=0.0);n=arr.shape[1];adj={i:set() for i in range(n)}
            for i in range(n):
                for j in range(i+1,n):
                    if abs(float(corr[i,j]))>=0.70:adj[i].add(j);adj[j].add(i)
            seen=set();groups=[]
            for i in range(n):
                if i in seen:continue
                stack=[i];seen.add(i);g=[]
                while stack:
                    x=stack.pop();g.append(x)
                    for y in adj[x]:
                        if y not in seen:seen.add(y);stack.append(y)
                groups.append(g)
            w=np.zeros(n);cluster_budget=1/max(1,len(groups));vol=np.nanstd(arr,axis=0)
            for g in groups:
                inv=1/np.maximum(vol[g],1e-12);inv=inv/inv.sum();w[g]=cluster_budget*inv
        else:raise ValueError(f"unknown method: {method}")
        return self._cap(w,max_component_weight)

    def build(self, values: pd.DataFrame, definition: SyntheticTickerDefinition) -> pd.DataFrame:
        x=values.loc[:,list(definition.components)].astype(float)
        returns=np.log(x).diff()
        out=[]; last_w=None
        for i in range(len(x)):
            if i < definition.min_periods: continue
            if last_w is None or (i-definition.min_periods)%definition.rebalance_every==0:
                hist=returns.iloc[max(1,i-definition.window):i].dropna(how="all")
                if len(hist)<definition.min_periods: continue
                last_w=self._weights(hist,definition.method,definition.max_component_weight)
            hist=returns.iloc[max(1,i-definition.window):i]
            mu=hist.mean(); sd=hist.std(ddof=0).replace(0,np.nan)
            z=((returns.iloc[i]-mu)/sd).clip(-definition.clip_z,definition.clip_z).fillna(0.0)
            value=float(np.dot(z.to_numpy(),last_w))
            coverage=float(np.isfinite(returns.iloc[i].to_numpy()).mean())
            concentration=float(np.max(np.abs(last_w)))
            confidence=max(0.0,min(1.0,coverage*(1.0-concentration/2.0)))
            out.append((x.index[i],value,confidence,*last_w))
        cols=["time","value","confidence",*[f"w:{c}" for c in definition.components]]
        return pd.DataFrame(out,columns=cols).set_index("time") if out else pd.DataFrame(columns=cols[1:])

@dataclass(frozen=True)
class EnsembleDefinition:
    name:str
    components:tuple[str,...]
    methods:tuple[str,...]=("equal","inverse_vol","adaptive_pca")
    window:int=120
    min_periods:int=40
    rebalance_every:int=10
    clip_z:float=6.0
    max_component_weight:float=1.0

class FactorEnsembleEngine:
    """Run simple factor builders in parallel and expose disagreement/stability instead of hiding it."""
    def build(self,values:pd.DataFrame,definition:EnsembleDefinition)->pd.DataFrame:
        eng=AdaptiveTickerEngine(); parts={}
        for method in definition.methods:
            d=SyntheticTickerDefinition(
                f"{definition.name}:{method}",definition.components,method,definition.window,
                definition.min_periods,definition.rebalance_every,definition.clip_z,definition.max_component_weight,
            )
            parts[method]=eng.build(values,d)
        if not parts:return pd.DataFrame()
        idx=None
        for frame in parts.values(): idx=frame.index if idx is None else idx.intersection(frame.index)
        if idx is None or len(idx)==0:return pd.DataFrame()
        vals=pd.DataFrame({m:f.loc[idx,"value"] for m,f in parts.items()},index=idx)
        conf=pd.DataFrame({m:f.loc[idx,"confidence"] for m,f in parts.items()},index=idx)
        out=pd.DataFrame(index=idx)
        # Confidence-weighted consensus; if all confidences vanish use arithmetic mean.
        denom=conf.sum(axis=1).replace(0,np.nan)
        out["value"]=(vals*conf).sum(axis=1)/denom
        out["value"]=out["value"].fillna(vals.mean(axis=1))
        out["confidence"]=conf.mean(axis=1).clip(0,1)
        out["method_disagreement"]=vals.std(axis=1,ddof=0)
        out["method_range"]=vals.max(axis=1)-vals.min(axis=1)
        for m in definition.methods:
            out[f"value:{m}"]=vals[m]; out[f"confidence:{m}"]=conf[m]
        # Weight-turnover and weight-direction stability from each method.
        turnover=[]; stability=[]
        for t in idx:
            ts=[]; ss=[]
            for frame in parts.values():
                wcols=[c for c in frame.columns if c.startswith("w:")]
                loc=frame.index.get_loc(t)
                if loc<=0 or not wcols: continue
                w=frame.iloc[loc][wcols].to_numpy(float); p=frame.iloc[loc-1][wcols].to_numpy(float)
                ts.append(float(np.abs(w-p).sum()))
                den=np.linalg.norm(w)*np.linalg.norm(p)
                ss.append(float(np.dot(w,p)/den) if den>0 else 0.0)
            turnover.append(float(np.mean(ts)) if ts else np.nan)
            stability.append(float(np.mean(ss)) if ss else np.nan)
        out["weight_turnover"]=turnover; out["weight_stability"]=stability
        return out
