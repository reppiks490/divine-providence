from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

_METHODS=frozenset({
    "equal","inverse_vol","adaptive_pca","shrinkage_pca","robust_pca","cluster_balanced"
})


def _validate_common_definition(
    *,
    name:str,
    components:tuple[str,...],
    window:int,
    min_periods:int,
    rebalance_every:int,
    clip_z:float,
    max_component_weight:float,
)->None:
    if not isinstance(name,str) or not name.strip() or name != name.strip():
        raise ValueError("name must be a non-empty trimmed string")
    if not isinstance(components,tuple) or not components:
        raise ValueError("components must be a non-empty tuple")
    if any(not isinstance(x,str) or not x.strip() or x != x.strip() for x in components):
        raise ValueError("component names must be non-empty trimmed strings")
    if len(set(components)) != len(components):
        raise ValueError("components must be unique")
    if type(window) is not int or type(min_periods) is not int:
        raise TypeError("window and min_periods must be integers")
    if min_periods < 1 or window < min_periods:
        raise ValueError("require window >= min_periods >= 1")
    if type(rebalance_every) is not int or rebalance_every < 1:
        raise ValueError("rebalance_every must be a positive integer")
    if not math.isfinite(float(clip_z)) or float(clip_z) <= 0:
        raise ValueError("clip_z must be finite and positive")
    cap=float(max_component_weight)
    if not math.isfinite(cap) or not 0.0 < cap <= 1.0:
        raise ValueError("max_component_weight must be finite and in (0,1]")
    if cap*len(components) < 1.0-1e-12:
        raise ValueError("max_component_weight is infeasible for component count")


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

    def __post_init__(self)->None:
        _validate_common_definition(
            name=self.name,
            components=self.components,
            window=self.window,
            min_periods=self.min_periods,
            rebalance_every=self.rebalance_every,
            clip_z=self.clip_z,
            max_component_weight=self.max_component_weight,
        )
        if self.method not in _METHODS:
            raise ValueError(f"unknown method: {self.method}")

class AdaptiveTickerEngine:
    """Build synthetic state series using trailing-only estimators."""
    @staticmethod
    def _normalize(w:np.ndarray)->np.ndarray:
        w=np.asarray(w,dtype=float)
        w=np.where(np.isfinite(w),w,0.0)
        s=float(np.sum(np.abs(w)))
        return w/s if s>1e-15 else np.zeros_like(w,dtype=float)

    @classmethod
    def _cap(
        cls,
        w:np.ndarray,
        cap:float,
        *,
        eligible:np.ndarray|None=None,
    )->np.ndarray:
        w=np.asarray(w,dtype=float)
        n=len(w)
        if cap<=0 or cap*n<1-1e-12:
            raise ValueError("max_component_weight is infeasible for component count")
        eligible=np.ones(n,dtype=bool) if eligible is None else np.asarray(eligible,dtype=bool)
        if len(eligible)!=n:
            raise ValueError("eligible mask length mismatch")
        w=np.where(eligible,w,0.0)
        w=cls._normalize(w)
        active=int(eligible.sum())
        if active==0 or not np.any(np.abs(w)>1e-15):
            return np.zeros_like(w)
        if cap>=1.0:
            return w
        # Missing/unevidenced components are not eligible recipients of cap
        # redistribution. If the surviving evidence cannot satisfy the cap,
        # fail closed for this fit rather than assigning weight to missing data.
        if cap*active<1-1e-12:
            return np.zeros_like(w)

        sign=np.where(w<0,-1.0,1.0)
        a=np.abs(w)
        for _ in range(n+2):
            over=eligible & (a>cap+1e-15)
            if not over.any():
                break
            excess=float((a[over]-cap).sum())
            a[over]=cap
            free=eligible & ~over
            room=np.maximum(0.0,cap-a[free])
            den=float(room.sum())
            if excess<=1e-15 or den<=1e-15:
                break
            a[free]+=excess*room/den
        a[~eligible]=0.0
        out=cls._normalize(sign*a)
        if np.any(np.abs(out[eligible])>cap+1e-10):
            return np.zeros_like(out)
        return out

    def _weights(self,hist:pd.DataFrame,method:str,max_component_weight:float=1.0)->np.ndarray:
        arr=hist.to_numpy(dtype=float)
        n=arr.shape[1]
        if max_component_weight<=0 or max_component_weight*n<1-1e-12:
            raise ValueError("max_component_weight is infeasible for component count")

        counts=np.isfinite(arr).sum(axis=0)
        sd_all=hist.std(axis=0,ddof=0,skipna=True).to_numpy(dtype=float)
        eligible=(counts>=2) & np.isfinite(sd_all) & (sd_all>1e-12)
        w=np.zeros(n,dtype=float)

        if method=="equal":
            w[eligible]=1.0
            return self._cap(w,max_component_weight,eligible=eligible)

        if method=="inverse_vol":
            w[eligible]=1.0/sd_all[eligible]
            return self._cap(w,max_component_weight,eligible=eligible)

        active_idx=np.flatnonzero(eligible)
        if active_idx.size==0:
            return w
        if method in {"adaptive_pca","shrinkage_pca","robust_pca"} and active_idx.size<2:
            # PCA-family estimators are inherently multivariate. Do not silently
            # turn a missing-component episode into a one-component factor.
            return w

        # Multivariate methods require actual joint observations. Missing values
        # are never replaced by zero/mean z-scores.
        joint=arr[:,active_idx]
        joint=joint[np.isfinite(joint).all(axis=1)]
        if len(joint)<2:
            return w

        mu=joint.mean(axis=0)
        sd=joint.std(axis=0)
        varying=np.isfinite(sd) & (sd>1e-12)
        active_idx=active_idx[varying]
        joint=joint[:,varying]
        sd=sd[varying]
        mu=mu[varying]
        if active_idx.size==0:
            return w
        active_mask=np.zeros(n,dtype=bool)
        active_mask[active_idx]=True
        if active_idx.size==1:
            if method=="cluster_balanced":
                w[active_idx[0]]=1.0
                return self._cap(w,max_component_weight,eligible=active_mask)
            return w

        z=(joint-mu)/sd

        if method in {"adaptive_pca","shrinkage_pca","robust_pca"}:
            work=z
            if method=="robust_pca":
                med=np.median(joint,axis=0)
                mad=np.median(np.abs(joint-med),axis=0)
                scale=np.where(mad>1e-12,1.4826*mad,sd)
                work=np.clip((joint-med)/scale,-5.0,5.0)
            cov=np.atleast_2d(np.cov(work,rowvar=False))
            if not np.isfinite(cov).all():
                return np.zeros(n,dtype=float)
            if method in {"shrinkage_pca","robust_pca"}:
                alpha=0.25 if method=="shrinkage_pca" else 0.35
                cov=(1-alpha)*cov+alpha*np.diag(np.diag(cov))
            vals,vecs=np.linalg.eigh(cov)
            local=vecs[:,int(np.argmax(vals))]
            j=int(np.argmax(np.abs(local)))
            if local[j]<0:
                local=-local
            w[active_idx]=local
        elif method=="cluster_balanced":
            corr=np.corrcoef(z,rowvar=False)
            if not np.isfinite(corr).all():
                return np.zeros(n,dtype=float)
            k=len(active_idx)
            adj={i:set() for i in range(k)}
            for i in range(k):
                for j in range(i+1,k):
                    if abs(float(corr[i,j]))>=0.70:
                        adj[i].add(j);adj[j].add(i)
            seen=set();groups=[]
            for i in range(k):
                if i in seen:
                    continue
                stack=[i];seen.add(i);g=[]
                while stack:
                    x=stack.pop();g.append(x)
                    for y in sorted(adj[x]):
                        if y not in seen:
                            seen.add(y);stack.append(y)
                groups.append(g)
            local=np.zeros(k,dtype=float)
            cluster_budget=1/max(1,len(groups))
            vol=joint.std(axis=0)
            for g in groups:
                inv=1/vol[g]
                inv=inv/inv.sum()
                local[g]=cluster_budget*inv
            w[active_idx]=local
        else:
            raise ValueError(f"unknown method: {method}")

        return self._cap(w,max_component_weight,eligible=active_mask)

    def build(self, values: pd.DataFrame, definition: SyntheticTickerDefinition) -> pd.DataFrame:
        if not isinstance(values,pd.DataFrame):
            raise TypeError("values must be a pandas DataFrame")
        missing=[x for x in definition.components if x not in values.columns]
        if missing:
            raise ValueError(f"missing synthetic components: {missing}")
        x=values.loc[:,list(definition.components)].astype(float)
        arr=x.to_numpy(dtype=float,copy=False)
        if np.isinf(arr).any():
            raise ValueError("synthetic level inputs contain infinite values")
        observed=np.isfinite(arr)
        if np.any(arr[observed] <= 0):
            raise ValueError(
                "synthetic log-return levels must be strictly positive when observed"
            )
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
            z=((returns.iloc[i]-mu)/sd).clip(-definition.clip_z,definition.clip_z)
            z_arr=z.to_numpy(dtype=float)
            finite=np.isfinite(z_arr) & np.isfinite(last_w)
            coverage=float(finite.mean())
            effective_w=np.zeros_like(last_w,dtype=float)
            if finite.any():
                effective_w[finite]=last_w[finite]
                den=float(np.sum(np.abs(effective_w)))
                if den>1e-15:
                    effective_w/=den
                    # Current missingness must not bypass the configured
                    # component cap by renormalizing the surviving weight to 1.
                    if np.max(np.abs(effective_w))>definition.max_component_weight+1e-10:
                        effective_w[:]=0.0
                        value=float("nan"); confidence=0.0
                    else:
                        value=float(np.dot(z_arr[finite],effective_w[finite]))
                        concentration=float(np.max(np.abs(effective_w)))
                        confidence=max(0.0,min(1.0,coverage*(1.0-concentration/2.0)))
                else:
                    value=float("nan"); confidence=0.0
            else:
                value=float("nan"); confidence=0.0
            out.append((x.index[i],value,confidence,*effective_w))
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

    def __post_init__(self)->None:
        _validate_common_definition(
            name=self.name,
            components=self.components,
            window=self.window,
            min_periods=self.min_periods,
            rebalance_every=self.rebalance_every,
            clip_z=self.clip_z,
            max_component_weight=self.max_component_weight,
        )
        if not isinstance(self.methods,tuple) or not self.methods:
            raise ValueError("methods must be a non-empty tuple")
        if len(set(self.methods)) != len(self.methods):
            raise ValueError("methods must be unique")
        unknown=[m for m in self.methods if m not in _METHODS]
        if unknown:
            raise ValueError(f"unknown methods: {unknown}")

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
        # Confidence-weighted consensus. If all methods have zero confidence,
        # keep the factor value missing rather than fabricating a neutral/mean value.
        valid_vals=vals.where(conf>0)
        denom=conf.where(valid_vals.notna(),0.0).sum(axis=1).replace(0,np.nan)
        out["value"]=(valid_vals*conf).sum(axis=1,min_count=1)/denom
        active=(valid_vals.notna() & (conf>0))
        active_count=active.sum(axis=1)
        out["confidence"]=conf.where(active).fillna(0.0).mean(axis=1).clip(0,1)
        out["active_method_count"]=active_count.astype(int)
        out["method_disagreement"]=vals.where(active).std(axis=1,ddof=0).where(active_count>=2)
        out["method_range"]=(vals.where(active).max(axis=1)-vals.where(active).min(axis=1)).where(active_count>=2)
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
