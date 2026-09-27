import numpy as np
from daedalus.adversarial import moving_block_bootstrap_evidence, prediction_permutation_test


def test_bootstrap_uses_trade_pnl_not_trade_indices():
    p=np.array([.9,.1,.9,.1,.9,.1,.9,.1])
    r=np.array([.02,-.02,.02,-.02,.02,-.02,.02,-.02])
    b=moving_block_bootstrap_evidence(p,r,.55,0.0,1,100,.90,7)
    assert b.trade_count==8
    assert b.median_cumulative_return>0
    assert b.positive_fraction>0.9


def test_circular_shift_permutation_is_reproducible():
    y=np.array([0,0,1,1,0,1,0,1]*20)
    p=np.where(y==1,.8,.2)
    a=prediction_permutation_test(y,p,iterations=99,random_state=11,method='circular_shift')
    b=prediction_permutation_test(y,p,iterations=99,random_state=11,method='circular_shift')
    assert a==b
    assert a.observed_auc>0.9
