import numpy as np
import pandas as pd
import pytest
from nexus.align import CausalAligner, AlignmentError
from nexus.ensemble import AdaptiveFactorEnsemble, EnsembleDefinition
from nexus.novelty import TrailingNovelty


def test_alignment_is_backward_only():
    driver=pd.DataFrame({'event_ns':[10,20,30],'source_sequence':[0,1,2],'close':[1.,2.,3.]})
    other=pd.DataFrame({'event_ns':[15,25],'source_sequence':[0,1],'close':[100.,200.]})
    z=CausalAligner().align(driver,{'B':other})
    assert np.isnan(z.loc[0,'B'])
    assert z.loc[1,'B']==100 and z.loc[2,'B']==200


def test_alignment_rejects_backward_source():
    d=pd.DataFrame({'event_ns':[10,20],'source_sequence':[0,1],'close':[1.,2.]})
    bad=pd.DataFrame({'event_ns':[20,10],'source_sequence':[0,1],'close':[1.,2.]})
    with pytest.raises(AlignmentError): CausalAligner().align(d,{'B':bad})


def test_factor_ensemble_and_novelty_are_future_stable():
    rng=np.random.default_rng(8); n=180
    rets=rng.normal(0,.01,(n,3)); px=100*np.exp(np.cumsum(rets,axis=0))
    x=pd.DataFrame(px,columns=['A','B','C'])
    d=EnsembleDefinition('NEXUS:M',('A','B','C'),window=60,min_periods=25,rebalance_every=5)
    e=AdaptiveFactorEnsemble()
    early=e.build(x.iloc[:120],d); full=e.build(x,d)
    common=early.index.intersection(full.index)
    pd.testing.assert_series_equal(early.loc[common,'value'],full.loc[common,'value'])
    states=pd.DataFrame({'f':full['value'],'d':full['method_disagreement']}).dropna()
    nov=TrailingNovelty(window=50,min_periods=20).score(states)
    assert nov.notna().sum()>0
