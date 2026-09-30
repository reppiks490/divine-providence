import numpy as np
import pandas as pd
from nexus.topology import RollingTopology
from nexus.change import ChangePointEngine


def test_topology_detects_strong_pair():
    rng=np.random.default_rng(7)
    a=rng.normal(size=200); b=a*.9+rng.normal(scale=.1,size=200); c=rng.normal(size=200)
    r=pd.DataFrame({'A':a,'B':b,'C':c})
    snap=RollingTopology(window=150,min_periods=50,edge_floor=.5).snapshot(r)
    assert snap.strongest_edges[0][:2]==('A','B')
    assert abs(snap.strongest_edges[0][2])>.9


def test_change_detector_flags_large_shift():
    cp=ChangePointEngine(alpha=.05,drift=.2,threshold=3)
    for _ in range(100): cp.update(0.0)
    seen=False
    for _ in range(10): seen = cp.update(10.0).change or seen
    assert seen


def test_topology_missing_pairs_remain_unknown_not_zero():
    rng=np.random.default_rng(17)
    a=rng.normal(size=120)
    b=a+rng.normal(scale=.02,size=120)
    c=np.full(120,np.nan)
    r=pd.DataFrame({'A':a,'B':b,'C':c})
    snap=RollingTopology(window=120,min_periods=40,edge_floor=.5).snapshot(r)
    assert np.isnan(snap.correlation.loc['A','C'])
    assert np.isnan(snap.partial_correlation.loc['A','C'])
    # Missing C does not dilute A/B centrality as if A-C were a true zero edge.
    assert snap.centrality['A']>.9
    assert snap.centrality['B']>.9
    assert snap.centrality['C']==0.0


def test_change_engine_rejects_invalid_configuration_and_nonfinite_input():
    import pytest
    for kwargs in ({'alpha':0},{'alpha':1.1},{'drift':-1},{'threshold':0}):
        with pytest.raises(ValueError):
            ChangePointEngine(**kwargs)
    cp=ChangePointEngine()
    with pytest.raises(ValueError,match='finite'):
        cp.update(float('nan'))
    with pytest.raises(ValueError,match='finite'):
        cp.update(float('inf'))


def test_change_engine_rejects_nonfinite_configuration():
    import pytest
    with pytest.raises(ValueError,match='alpha'):
        ChangePointEngine(alpha=float('nan'))
    with pytest.raises(ValueError,match='drift'):
        ChangePointEngine(drift=float('nan'))
    with pytest.raises(ValueError,match='threshold'):
        ChangePointEngine(threshold=float('inf'))
