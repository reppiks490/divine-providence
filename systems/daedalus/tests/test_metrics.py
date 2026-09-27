import numpy as np
from daedalus.metrics import evaluate_predictions


def test_metrics_finite_core_values():
    y=np.array([0,1,0,1,1,0,1,0])
    p=np.array([.2,.8,.3,.7,.65,.4,.75,.25])
    r=np.array([-.01,.02,-.01,.01,.02,-.005,.015,-.01])
    m=evaluate_predictions(y,p,r,.55,1.5)
    assert m.auc>0.5
    assert np.isfinite(m.sharpe)
    assert 0<=m.max_drawdown<=1
