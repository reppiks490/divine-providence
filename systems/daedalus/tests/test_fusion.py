import numpy as np
import pandas as pd
import pytest

from daedalus.config import FeatureConfig
from daedalus.fusion import build_execution_target, build_fused_dataset


def _bars(times, start=100.0):
    n=len(times)
    close=start+np.arange(n,dtype=float)*0.2
    open_=close-0.05
    return pd.DataFrame({
        'time':np.asarray(times,dtype=float),
        'open':open_,
        'high':close+0.1,
        'low':open_-0.1,
        'close':close,
        'volume':np.arange(n,dtype=float)+100,
    })


def _cfg():
    return FeatureConfig(
        return_windows=(1,2),vol_windows=(2,),range_windows=(2,),volume_windows=(2,),
        target_horizon=2,feature_lag_bars=1,include_utc_calendar=False,
    )


def test_execution_target_enters_at_open_not_same_bar_close():
    df=_bars([0,60,120,180,240])
    y,r=build_execution_target(df,_cfg())
    expected=np.log(df.loc[1,'close']/df.loc[0,'open'])
    assert np.isclose(r.iloc[0],expected)
    assert y.iloc[-1] != y.iloc[-1]  # NaN: final 2-bar target cannot mature


def test_fusion_is_strictly_backward_only_and_future_mutation_safe():
    execution=_bars(np.arange(0,1200,60))
    rep=_bars(np.arange(30,1230,60),start=50)
    x1,y1,r1,d1=build_fused_dataset(execution,{'alt':rep},_cfg())
    assert len(x1)>0
    assert all(s.max_source_time_minus_execution_time < 0 for s in d1.sources)

    cutoff=int(x1.index[len(x1)//2])
    mutated=rep.copy()
    mutated.loc[mutated['time']>execution.loc[cutoff,'time'],'close'] *= 5
    x2,_,_,_=build_fused_dataset(execution,{'alt':mutated},_cfg())
    common=x1.index.intersection(x2.index)
    prior=common[common<=cutoff]
    pd.testing.assert_frame_equal(x1.loc[prior],x2.loc[prior])


def test_fusion_rejects_ambiguous_repeated_timestamp_source():
    execution=_bars(np.arange(0,1200,60))
    rep=_bars(np.arange(30,1230,60),start=50)
    rep.loc[5,'time']=rep.loc[4,'time']
    with pytest.raises(ValueError,match='repeated timestamps'):
        build_fused_dataset(execution,{'alt':rep},_cfg())
