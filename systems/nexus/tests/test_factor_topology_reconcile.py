import numpy as np,pandas as pd
from nexus.synthetic import AdaptiveTickerEngine,SyntheticTickerDefinition
from nexus.topology import RollingTopology
from nexus.reconcile import reconcile_catalogs,compare_declared_checkpoint
from nexus.contracts import StreamIdentity,StreamManifest

def test_robust_factor_methods_and_component_cap():
    rng=np.random.default_rng(4);n=260;base=np.cumsum(rng.normal(0,.01,n));x=pd.DataFrame({
        'a':100*np.exp(base+rng.normal(0,.003,n)),'b':100*np.exp(base+rng.normal(0,.004,n)),
        'c':100*np.exp(.5*base+rng.normal(0,.01,n)),'d':100*np.exp(-.2*base+rng.normal(0,.02,n))})
    for method in ('robust_pca','shrinkage_pca','cluster_balanced'):
        out=AdaptiveTickerEngine().build(x,SyntheticTickerDefinition('N:X',tuple(x.columns),method,80,40,10,6.0,.55))
        assert len(out)>0
        assert max(out.filter(like='w:').abs().max())<=.5500001

def test_lead_lag_stability_reports_persistence():
    rng=np.random.default_rng(5);a=rng.normal(size=300);b=np.roll(a,2)+rng.normal(0,.1,300);b[:2]=0
    r=pd.DataFrame({'a':a,'b':b,'c':rng.normal(size=300)})
    out=RollingTopology(window=100,min_periods=40).lead_lag_stability(r,max_lag=4,min_overlap=30,step=20)
    assert {'presence','lag_consistency','sign_consistency','mean_abs_corr'}.issubset(out.columns)
    assert len(out)>0

def _m(path,raw,logical,symbol='NQ'):
    x=StreamManifest(StreamIdentity('csv','CME',symbol,'1','csv',path,raw),1,['time','open','high','low','close'],1,1,1,1,0,0,0)
    x.metadata['logical_sha256']=logical;return x

def test_corpus_reconciliation_is_hash_first():
    a=[_m('a.csv','a'*64,'1'*64),_m('b.csv','b'*64,'2'*64,'ES')]
    b=[_m('renamed.csv','a'*64,'1'*64),_m('c.csv','c'*64,'3'*64,'VIX')]
    r=reconcile_catalogs(a,b);assert r.common_byte_hashes==1 and r.common_logical_hashes==1
    g=compare_declared_checkpoint(a,declared_usable_entries=626,declared_rows=12_588_290)
    assert g.unresolved_entry_gap==624 and not g.coverage_claim_allowed
