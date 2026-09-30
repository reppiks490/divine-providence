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
