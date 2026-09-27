import numpy as np
import pandas as pd
from daedalus.config import FeatureConfig
from daedalus.features import build_causal_features


def make_df(n=300):
    c=np.linspace(100,130,n)+np.sin(np.arange(n)/5)
    return pd.DataFrame({"time":np.arange(n),"open":c-0.1,"high":c+0.5,"low":c-0.5,"close":c,"volume":100+np.arange(n)})


def test_future_change_does_not_change_prior_feature_row():
    cfg=FeatureConfig(target_horizon=5)
    a=make_df()
    x1,_,_=build_causal_features(a,cfg)
    b=a.copy()
    b.loc[250:,"close"]*=10
    b.loc[250:,"high"]=np.maximum(b.loc[250:,"high"],b.loc[250:,"close"]+0.5)
    b.loc[250:,"low"]=np.minimum(b.loc[250:,"low"],b.loc[250:,"close"]-0.5)
    x2,_,_=build_causal_features(b,cfg)
    common=[i for i in x1.index.intersection(x2.index) if i < 250]
    pd.testing.assert_frame_equal(x1.loc[common],x2.loc[common])


def test_features_are_shifted_one_bar():
    df=make_df()
    x,_,_=build_causal_features(df,FeatureConfig())
    idx=int(x.index[0])
    expected=np.log(df.loc[idx-1,"close"]/df.loc[idx-2,"close"])
    assert abs(x.loc[idx,"ret_1"]-expected)<1e-12


def test_positive_target_threshold_creates_neutral_deadband_not_false_short():
    df=make_df(350)
    cfg=FeatureConfig(target_horizon=1,target_threshold_bps=50)
    x,y,r=build_causal_features(df,cfg)
    assert not ((r.abs() <= 0.005 + 1e-15)).any()


def test_row_counter_timestamps_do_not_create_fake_utc_calendar_features():
    df=make_df(350)
    x,_,_=build_causal_features(df,FeatureConfig(include_utc_calendar=True))
    assert not any(c.startswith('utc_') for c in x.columns)


def test_empty_optional_volume_does_not_erase_price_features():
    df=make_df(350)
    df['volume']=np.nan
    x,y,r=build_causal_features(df,FeatureConfig(target_horizon=3))
    assert len(x)>200
    assert not any(c.startswith('volume_') for c in x.columns)


def test_partial_bar_mechanics_missingness_does_not_discard_valid_price_rows():
    df=make_df(400)
    # Simulate an event/alternate chart representation with repeated timestamps
    # and intermittent backward timestamp corrections. These mechanics may make
    # cadence-derived predictors undefined while the OHLC state remains valid.
    t=np.arange(400,dtype=float)
    t[80:120]=t[79]
    t[220:230]=t[219]-1
    df['time']=1_700_000_000+t
    cfg=FeatureConfig(target_horizon=3,min_row_feature_coverage=0.70)
    x,y,r=build_causal_features(df,cfg)
    assert len(x)>300
    assert x['repeat_timestamp'].max()==1.0
    assert x['backward_timestamp'].max()==1.0
    assert len(x)==len(y)==len(r)


def test_feature_coverage_threshold_preserves_partial_rows_for_train_fitted_imputation():
    df=make_df(220)
    cfg=FeatureConfig(
        return_windows=(1,2,5,100),vol_windows=(5,100),range_windows=(5,100),volume_windows=(5,100),
        target_horizon=3,min_row_feature_coverage=0.60,include_utc_calendar=False,
    )
    x,y,r=build_causal_features(df,cfg)
    assert len(x)>100
    assert x.isna().any(axis=None)  # missingness is explicit, not silently row-dropped
    assert len(x)==len(y)==len(r)
