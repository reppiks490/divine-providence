import numpy as np
import pandas as pd

from daedalus.hypotheses import HypothesisResult, screen_interactions


def test_interaction_screen_is_bounded_and_fdr_corrected():
    rng=np.random.default_rng(1)
    n=300
    a=rng.normal(size=n); b=rng.normal(size=n); c=rng.normal(size=n)
    future=a*b + rng.normal(scale=.2,size=n)
    x=pd.DataFrame({'a':a,'b':b,'c':c})
    base=[
        HypothesisResult('a','spearman',0,.1,.1,False,n),
        HypothesisResult('b','spearman',0,.2,.2,False,n),
        HypothesisResult('c','spearman',0,.3,.3,False,n),
    ]
    out=screen_interactions(x,pd.Series(future),base,alpha=.05,seed_features=3,max_interactions=2,min_observations=50)
    assert len(out)<=2
    assert all(0<=r.qvalue<=1 for r in out)
    assert any(r.feature=='interaction::a*b' and r.rejected_null for r in out)
