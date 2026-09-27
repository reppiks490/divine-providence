import numpy as np
import pandas as pd
from nexus.causality import audit_prefix_invariance,audit_event_availability
from nexus.synthetic import AdaptiveTickerEngine,SyntheticTickerDefinition
from nexus.contracts import BarEvent


def test_prefix_audit_accepts_adaptive_ticker():
    n=100;idx=pd.RangeIndex(n)
    levels=pd.DataFrame({"A":100*np.exp(np.linspace(0,.1,n)+.01*np.sin(np.arange(n))),"B":80*np.exp(np.linspace(0,.05,n)+.01*np.cos(np.arange(n)))},index=idx)
    d=SyntheticTickerDefinition("X",("A","B"),"inverse_vol",window=30,min_periods=10,rebalance_every=5)
    audit=audit_prefix_invariance(lambda x:AdaptiveTickerEngine().build(x,d),levels,cutpoints=(30,55,80,100))
    assert audit.passed, audit.violations[:3]
    assert audit.comparisons>0


def test_prefix_audit_catches_centered_future_leakage():
    x=pd.DataFrame({"x":np.arange(20,dtype=float)})
    audit=audit_prefix_invariance(lambda d:d.rolling(3,center=True,min_periods=1).mean(),x,cutpoints=(8,12,20))
    assert not audit.passed
    assert audit.violations


def test_availability_audit_rejects_future_visibility_inversion():
    e=BarEvent("s",100,0,1,2,0,1,None,"x",available_ns=90)
    assert audit_event_availability([e])
