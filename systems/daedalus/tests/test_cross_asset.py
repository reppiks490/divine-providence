import numpy as np
import pandas as pd
from daedalus.cross_asset import lead_lag_screen


def test_lead_lag_never_requires_future_right_values():
    n=500
    rng=np.random.default_rng(1)
    r=rng.normal(0,0.01,n)
    # left at t is driven by right at t-2
    l=np.roll(r,2); l[:2]=0
    rc=100*np.exp(np.cumsum(r)); lc=100*np.exp(np.cumsum(l))
    right=pd.DataFrame({"time":np.arange(n),"close":rc})
    left=pd.DataFrame({"time":np.arange(n),"close":lc})
    hits=lead_lag_screen(left,right,max_lag=4,alpha=0.05)
    assert any(h.lag in (1,2,3) for h in hits)
