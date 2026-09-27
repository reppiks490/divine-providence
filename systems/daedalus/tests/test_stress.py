import numpy as np
from daedalus.stress import threshold_cost_surface


def test_robustness_surface_has_expected_grid():
    y=np.array([0,1,0,1,1,0,1,0]*20)
    p=np.array([.2,.8,.3,.7,.65,.4,.75,.25]*20)
    r=np.array([-.01,.02,-.01,.01,.02,-.005,.015,-.01]*20)
    s=threshold_cost_surface(y,p,r,.55,1.5,(1.0,2.0),(-.02,0,.02))
    assert len(s.cells)==6
    assert 0<=s.profitable_fraction<=1
