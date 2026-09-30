import numpy as np
import pandas as pd
from nexus.synthetic import AdaptiveTickerEngine, SyntheticTickerDefinition


def _frame(n=120):
    idx=pd.RangeIndex(n)
    a=100*np.exp(np.cumsum(np.linspace(-.001,.002,n)))
    b=80*np.exp(np.cumsum(np.linspace(.001,-.001,n)))
    return pd.DataFrame({'A':a,'B':b},index=idx)


def test_synthetic_does_not_refit_past_when_future_appended():
    x=_frame(140)
    d=SyntheticTickerDefinition('NEXUS:TEST',('A','B'),window=50,min_periods=20,rebalance_every=5)
    eng=AdaptiveTickerEngine()
    early=eng.build(x.iloc[:100],d)
    full=eng.build(x,d)
    common=early.index.intersection(full.index)
    pd.testing.assert_series_equal(early.loc[common,'value'],full.loc[common,'value'])
    for c in [k for k in early.columns if k.startswith('w:')]:
        pd.testing.assert_series_equal(early.loc[common,c],full.loc[common,c])


def test_inverse_vol_weights_are_normalized():
    x=_frame(80)
    d=SyntheticTickerDefinition('NEXUS:TEST',('A','B'),method='inverse_vol',window=40,min_periods=20,rebalance_every=1)
    out=AdaptiveTickerEngine().build(x,d)
    assert len(out)>0
    s=(out['w:A'].abs()+out['w:B'].abs()).round(10)
    assert (s==1.0).all()


def test_missing_component_is_excluded_not_zero_imputed():
    x=_frame(100)
    x.loc[60,'B']=np.nan
    d=SyntheticTickerDefinition(
        'NEXUS:MISSING',('A','B'),method='equal',
        window=40,min_periods=20,rebalance_every=1
    )
    out=AdaptiveTickerEngine().build(x,d)
    row=out.loc[60]
    assert np.isfinite(row['value'])
    assert row['w:B']==0.0
    assert abs(abs(row['w:A'])-1.0)<1e-12
    assert 0.0 < row['confidence'] < 1.0


def test_all_current_components_missing_stays_missing():
    x=_frame(100)
    x.loc[60,['A','B']]=np.nan
    d=SyntheticTickerDefinition(
        'NEXUS:MISSING',('A','B'),method='equal',
        window=40,min_periods=20,rebalance_every=1
    )
    out=AdaptiveTickerEngine().build(x,d)
    row=out.loc[60]
    assert np.isnan(row['value'])
    assert row['confidence']==0.0
    assert row['w:A']==0.0 and row['w:B']==0.0


def test_historical_missing_component_gets_no_fit_weight_until_evidenced():
    x=_frame(120)
    x.loc[:80,'B']=np.nan
    d=SyntheticTickerDefinition(
        'NEXUS:HIST-MISSING',('A','B'),method='inverse_vol',
        window=40,min_periods=20,rebalance_every=1
    )
    out=AdaptiveTickerEngine().build(x,d)
    # B has no usable trailing return history when it first reappears, so it
    # cannot receive estimator weight merely because NaNs were mean-imputed.
    row=out.loc[82]
    assert row['w:B']==0.0
    assert abs(row['w:A'])==1.0


def test_multivariate_fit_does_not_zero_impute_disjoint_history():
    x=_frame(120)
    x.loc[:69,'B']=np.nan
    x.loc[70:,'A']=np.nan
    d=SyntheticTickerDefinition(
        'NEXUS:DISJOINT',('A','B'),method='adaptive_pca',
        window=50,min_periods=20,rebalance_every=1
    )
    out=AdaptiveTickerEngine().build(x,d)
    # There is no joint A/B training history. The PCA fit must fail closed,
    # not manufacture covariance by replacing missing z-scores with zero.
    tail=out.loc[out.index>=90]
    assert tail['value'].isna().all()
    assert (tail[['w:A','w:B']]==0.0).all().all()


def test_current_missingness_cannot_bypass_component_cap():
    x=_frame(100)
    x.loc[60,'B']=np.nan
    d=SyntheticTickerDefinition(
        'NEXUS:CAP-MISSING',('A','B'),method='equal',
        window=40,min_periods=20,rebalance_every=1,max_component_weight=.6
    )
    out=AdaptiveTickerEngine().build(x,d)
    row=out.loc[60]
    assert np.isnan(row['value'])
    assert row['confidence']==0.0
    assert row['w:A']==0.0 and row['w:B']==0.0


def test_synthetic_definition_rejects_invalid_configuration():
    import pytest
    with pytest.raises(ValueError,match='components'):
        SyntheticTickerDefinition('X',())
    with pytest.raises(ValueError,match='unique'):
        SyntheticTickerDefinition('X',('A','A'))
    with pytest.raises(ValueError,match='unknown method'):
        SyntheticTickerDefinition('X',('A',),method='magic')
    with pytest.raises(ValueError,match='window'):
        SyntheticTickerDefinition('X',('A',),window=2,min_periods=3)
    with pytest.raises(ValueError,match='rebalance_every'):
        SyntheticTickerDefinition('X',('A',),rebalance_every=0)
    with pytest.raises(ValueError,match='clip_z'):
        SyntheticTickerDefinition('X',('A',),clip_z=float('nan'))
    with pytest.raises(ValueError,match='infeasible'):
        SyntheticTickerDefinition('X',('A','B'),max_component_weight=.4)


def test_synthetic_log_level_inputs_fail_closed_on_nonpositive_or_infinite_values():
    import pytest
    eng=AdaptiveTickerEngine()
    d=SyntheticTickerDefinition(
        'NEXUS:STRICT',('A','B'),method='equal',
        window=10,min_periods=3,rebalance_every=1,
    )
    x=_frame(20)
    x.loc[5,'A']=0.0
    with pytest.raises(ValueError,match='strictly positive'):
        eng.build(x,d)
    y=_frame(20)
    y.loc[5,'A']=float('inf')
    with pytest.raises(ValueError,match='infinite'):
        eng.build(y,d)


def test_synthetic_missing_component_column_is_rejected():
    import pytest
    d=SyntheticTickerDefinition('X',('A','B'),window=10,min_periods=3)
    with pytest.raises(ValueError,match='missing synthetic components'):
        AdaptiveTickerEngine().build(pd.DataFrame({'A':[1.,2.,3.]}),d)
