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
