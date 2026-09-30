from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class TopologySnapshot:
    timestamp: object
    correlation: pd.DataFrame
    centrality: dict[str,float]
    strongest_edges: tuple[tuple[str,str,float], ...]
    entropy: float
    partial_correlation: pd.DataFrame | None=None
    communities: tuple[tuple[str,...], ...]=()

class RollingTopology:
    def __init__(self, window: int=120, min_periods: int=40, edge_floor: float=0.25, partial_edge_floor:float=0.15, ridge:float=1e-3):
        if int(min_periods)<2 or int(window)<int(min_periods):
            raise ValueError("require window >= min_periods >= 2")
        if not (0.0 <= float(edge_floor) <= 1.0):
            raise ValueError("edge_floor must be in [0,1]")
        if not (0.0 <= float(partial_edge_floor) <= 1.0):
            raise ValueError("partial_edge_floor must be in [0,1]")
        if float(ridge)<=0.0:
            raise ValueError("ridge must be positive")
        self.window=int(window); self.min_periods=int(min_periods); self.edge_floor=float(edge_floor)
        self.partial_edge_floor=float(partial_edge_floor); self.ridge=float(ridge)

    def _partial(self,hist:pd.DataFrame)->pd.DataFrame:
        cols=list(hist.columns)
        out=pd.DataFrame(np.nan,index=cols,columns=cols,dtype=float)
        for col in cols:
            out.loc[col,col]=1.0
        if len(cols)<2:
            return out

        # Partial correlation requires joint observations. Missing values are
        # never replaced with zero z-scores because that fabricates covariance.
        complete=hist.loc[:,cols].dropna(how="any")
        if len(complete)<self.min_periods:
            return out
        sd=complete.std(ddof=0)
        usable=[col for col in cols if np.isfinite(sd[col]) and float(sd[col])>1e-12]
        if len(usable)<2:
            return out
        z=(complete[usable]-complete[usable].mean())/complete[usable].std(ddof=0)
        cov=np.cov(z.to_numpy(float),rowvar=False)
        if not np.isfinite(cov).all():
            return out
        cov=np.atleast_2d(cov)+np.eye(len(usable))*self.ridge
        precision=np.linalg.pinv(cov)
        d=np.sqrt(np.maximum(np.diag(precision),1e-12))
        p=-precision/np.outer(d,d); np.fill_diagonal(p,1.0)
        out.loc[usable,usable]=p
        return out

    def _communities(self,partial:pd.DataFrame)->tuple[tuple[str,...],...]:
        cols=list(partial.columns)
        # A completely unestimated column is unknown, not a proven singleton
        # community. Keep only nodes with at least one finite off-diagonal link.
        active=[
            c for c in cols
            if any(
                other!=c and np.isfinite(float(partial.loc[c,other]))
                for other in cols
            )
        ]
        if len(cols)==1 and cols:
            active=cols
        adj={c:set() for c in active}
        for i,a in enumerate(active):
            for b in active[i+1:]:
                w=float(partial.loc[a,b])
                if np.isfinite(w) and abs(w)>=self.partial_edge_floor:
                    adj[a].add(b);adj[b].add(a)
        seen=set(); groups=[]
        for c in active:
            if c in seen:continue
            stack=[c]; comp=[];seen.add(c)
            while stack:
                x=stack.pop();comp.append(x)
                for n in sorted(adj[x]):
                    if n not in seen:seen.add(n);stack.append(n)
            groups.append(tuple(sorted(comp)))
        return tuple(sorted(groups,key=lambda g:(-len(g),g)))

    def snapshot(self, returns: pd.DataFrame, at: int | None=None) -> TopologySnapshot:
        hist=returns.iloc[:at] if at is not None else returns
        hist=hist.tail(self.window)
        corr=hist.corr(min_periods=self.min_periods)
        syms=list(corr.columns); centrality={s:0.0 for s in syms}; observed={s:0 for s in syms}; edges=[]
        for i,a in enumerate(syms):
            for b in syms[i+1:]:
                w=float(corr.loc[a,b])
                if not np.isfinite(w):
                    continue
                observed[a]+=1; observed[b]+=1
                if abs(w)>=self.edge_floor:
                    edges.append((a,b,w)); centrality[a]+=abs(w); centrality[b]+=abs(w)
        centrality={k:(v/observed[k] if observed[k] else 0.0) for k,v in centrality.items()}
        vals=np.array([abs(w) for _,_,w in edges],dtype=float)
        if vals.size and vals.sum()>0:
            p=vals/vals.sum(); entropy=float(-(p*np.log(p+1e-12)).sum()/np.log(max(2,len(p))))
        else: entropy=0.0
        ts=hist.index[-1] if len(hist) else None
        edges=tuple(sorted(edges,key=lambda e:abs(e[2]),reverse=True))
        partial=self._partial(hist); communities=self._communities(partial)
        return TopologySnapshot(ts,corr,centrality,edges,entropy,partial,communities)

    def lead_lag(self, returns: pd.DataFrame, max_lag: int=8, min_overlap: int=40) -> pd.DataFrame:
        if type(max_lag) is not int or max_lag < 1:
            raise ValueError("max_lag must be a positive integer")
        if type(min_overlap) is not int or min_overlap < 2:
            raise ValueError("min_overlap must be an integer >= 2")
        cols=list(returns.columns); rows=[]; hist=returns.tail(self.window)
        for a in cols:
            for b in cols:
                if a==b: continue
                best_lag=0;best_corr=float("nan")
                for lag in range(1,max_lag+1):
                    z=pd.concat([hist[a],hist[b].shift(-lag)],axis=1).dropna()
                    if len(z)<min_overlap: continue
                    corr_value=float(z.iloc[:,0].corr(z.iloc[:,1]))
                    if np.isfinite(corr_value) and (not np.isfinite(best_corr) or abs(corr_value)>abs(best_corr)):
                        best_lag=lag;best_corr=corr_value
                rows.append({"leader":a,"follower":b,"lag_bars":best_lag,"corr":best_corr})
        return pd.DataFrame(rows).sort_values("corr",key=lambda s:s.abs(),ascending=False)

    def lead_lag_stability(self,returns:pd.DataFrame,max_lag:int=8,min_overlap:int=40,step:int=20)->pd.DataFrame:
        """Measure persistence of descriptive lead/lag candidates across trailing windows.

        This is stability telemetry only; it is not a causal or predictive claim.
        """
        if type(step) is not int or step < 1:
            raise ValueError("step must be a positive integer")
        records=[];step=step
        for at in range(self.min_periods,len(returns)+1,step):
            hist=returns.iloc[:at].tail(self.window)
            ll=self.lead_lag(hist,max_lag=max_lag,min_overlap=min_overlap)
            ll=ll[ll.lag_bars>0]
            for _,r in ll.iterrows():records.append((r.leader,r.follower,int(r.lag_bars),float(r["corr"])))
        if not records:return pd.DataFrame(columns=["leader","follower","observations","presence","lag_mode","lag_consistency","sign_consistency","mean_abs_corr"])
        total=max(1,len(range(self.min_periods,len(returns)+1,step)));rows=[]
        frame=pd.DataFrame(records,columns=["leader","follower","lag","corr"])
        for (a,b),g in frame.groupby(["leader","follower"]):
            mode=int(g.lag.value_counts().sort_index().idxmax());sign=float(max((g['corr']>0).mean(),(g['corr']<0).mean()))
            rows.append({"leader":a,"follower":b,"observations":len(g),"presence":len(g)/total,"lag_mode":mode,"lag_consistency":float((g.lag==mode).mean()),"sign_consistency":sign,"mean_abs_corr":float(g['corr'].abs().mean())})
        return pd.DataFrame(rows).sort_values(["presence","lag_consistency","mean_abs_corr"],ascending=False)

    def edge_survival(self,returns:pd.DataFrame,step:int=20)->pd.DataFrame:
        """Describe how often pairwise correlation edges survive across trailing snapshots."""
        if type(step) is not int or step < 1:
            raise ValueError("step must be a positive integer")
        counts={}; total=0
        for at in range(self.min_periods,len(returns)+1,step):
            snap=self.snapshot(returns,at); total+=1
            for a,b,w in snap.strongest_edges:
                k=tuple(sorted((a,b))); counts.setdefault(k,[0,[]]); counts[k][0]+=1; counts[k][1].append(w)
        rows=[]
        for (a,b),(n,ws) in counts.items():
            rows.append({"a":a,"b":b,"survival":n/max(1,total),"mean_corr":float(np.mean(ws)),"observations":n})
        return pd.DataFrame(rows).sort_values("survival",ascending=False) if rows else pd.DataFrame(columns=["a","b","survival","mean_corr","observations"])
