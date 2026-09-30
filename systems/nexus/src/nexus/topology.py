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
        self.window=window; self.min_periods=min_periods; self.edge_floor=edge_floor
        self.partial_edge_floor=partial_edge_floor; self.ridge=ridge

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
        cols=list(partial.columns); adj={c:set() for c in cols}
        for i,a in enumerate(cols):
            for b in cols[i+1:]:
                if abs(float(partial.loc[a,b]))>=self.partial_edge_floor:
                    adj[a].add(b);adj[b].add(a)
        seen=set(); groups=[]
        for c in cols:
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
        cols=list(returns.columns); rows=[]; hist=returns.tail(self.window)
        for a in cols:
            for b in cols:
                if a==b: continue
                best=(0,0.0)
                for lag in range(1,max_lag+1):
                    z=pd.concat([hist[a],hist[b].shift(-lag)],axis=1).dropna()
                    if len(z)<min_overlap: continue
                    c=float(z.iloc[:,0].corr(z.iloc[:,1]))
                    if np.isfinite(c) and abs(c)>abs(best[1]): best=(lag,c)
                rows.append({"leader":a,"follower":b,"lag_bars":best[0],"corr":best[1]})
        return pd.DataFrame(rows).sort_values("corr",key=lambda s:s.abs(),ascending=False)

    def lead_lag_stability(self,returns:pd.DataFrame,max_lag:int=8,min_overlap:int=40,step:int=20)->pd.DataFrame:
        """Measure persistence of descriptive lead/lag candidates across trailing windows.

        This is stability telemetry only; it is not a causal or predictive claim.
        """
        records=[];step=max(1,int(step))
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
        counts={}; total=0
        for at in range(self.min_periods,len(returns)+1,max(1,step)):
            snap=self.snapshot(returns,at); total+=1
            for a,b,w in snap.strongest_edges:
                k=tuple(sorted((a,b))); counts.setdefault(k,[0,[]]); counts[k][0]+=1; counts[k][1].append(w)
        rows=[]
        for (a,b),(n,ws) in counts.items():
            rows.append({"a":a,"b":b,"survival":n/max(1,total),"mean_corr":float(np.mean(ws)),"observations":n})
        return pd.DataFrame(rows).sort_values("survival",ascending=False) if rows else pd.DataFrame(columns=["a","b","survival","mean_corr","observations"])
