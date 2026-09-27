from pathlib import Path
import numpy as np
import pandas as pd

from daedalus.config import (
    AdversarialConfig, DaedalusConfig, DataConfig, DevelopmentGateConfig, FeatureConfig,
    PromotionConfig, RuntimeConfig, ValidationConfig,
)
from daedalus.pipeline import research_file


def test_end_to_end_pipeline_respects_frozen_protected_ensemble(tmp_path: Path):
    rng=np.random.default_rng(5)
    n=760
    ret=rng.normal(0,0.002,n)
    close=100*np.exp(np.cumsum(ret))
    open_=np.r_[close[0],close[:-1]]
    spread=np.maximum(.05,close*0.001)
    df=pd.DataFrame({
        'time':1_700_000_000+np.arange(n)*60,
        'open':open_, 'high':np.maximum(open_,close)+spread,
        'low':np.minimum(open_,close)-spread, 'close':close,
        'volume':rng.integers(100,1000,n),
    })
    src=tmp_path/'NQ_ALT, 1.csv'; df.to_csv(src,index=False)
    cfg=DaedalusConfig(
        data=DataConfig(min_rows=300),
        features=FeatureConfig(return_windows=(1,2,5),vol_windows=(5,10),range_windows=(5,10),volume_windows=(5,10),target_horizon=3),
        validation=ValidationConfig(n_splits=2,min_train_size=220,test_size=90,purge_bars=3,embargo_bars=3,protected_holdout_size=120,protected_holdout_min=100,protected_holdout_max=200,min_holdout_rows=80,min_development_folds=2),
        development_gate=DevelopmentGateConfig(enabled=False),
        adversarial=AdversarialConfig(permutation_iterations=31,bootstrap_iterations=40,max_feature_ablation_groups=3),
        promotion=PromotionConfig(require_execution_safe_identity=False,min_trade_count=1,min_trade_sharpe_like=-999,min_profit_factor=0,max_permutation_pvalue=1,max_drift_score=1,min_fold_pass_rate=0,min_robustness_score=0,min_threshold_survival_rate=0,min_cost_survival_rate=0,require_positive_bootstrap_median=False,min_bootstrap_positive_fraction=0),
        runtime=RuntimeConfig(registry_path='artifacts/test.sqlite3',output_dir='artifacts/runs',candidate_dir='artifacts/candidates',shadow_path='artifacts/shadow.sqlite3',identity_manifest='config/source_identity.csv'),
    )
    report=research_file(src,tmp_path,cfg,data_root=tmp_path)
    assert report['status']=='ok'
    assert 1 <= report['final_candidate']['protected_holdout_model_count'] <= cfg.ensemble.max_models
    assert report['final_candidate']['model']=='development_weighted_ensemble'
    assert report['selected_champion']==report['selected_development_champion']
    assert set(report['final_candidate']['selected_development_components']) == set(report['development_ensemble_weights'])
    assert report['final_candidate']['holdout_protocol_clean'] is True
    assert report['purge_gap_rows']>=cfg.features.target_horizon
    assert len(report['development_models'])==4
    assert all(not m['protected_holdout_touched'] for m in report['development_models'])


def test_development_only_mode_never_creates_holdout_ledger(tmp_path: Path):
    rng=np.random.default_rng(15)
    n=760
    ret=rng.normal(0,0.002,n)
    close=100*np.exp(np.cumsum(ret))
    open_=np.r_[close[0],close[:-1]]
    spread=np.maximum(.05,close*0.001)
    df=pd.DataFrame({
        'time':1_700_000_000+np.arange(n)*60,
        'open':open_, 'high':np.maximum(open_,close)+spread,
        'low':np.minimum(open_,close)-spread, 'close':close,
        'volume':rng.integers(100,1000,n),
    })
    src=tmp_path/'NQ_DEV_ONLY, 1.csv'; df.to_csv(src,index=False)
    cfg=DaedalusConfig(
        data=DataConfig(min_rows=300),
        features=FeatureConfig(return_windows=(1,2,5),vol_windows=(5,10),range_windows=(5,10),volume_windows=(5,10),target_horizon=3),
        validation=ValidationConfig(n_splits=2,min_train_size=220,test_size=90,purge_bars=3,embargo_bars=3,protected_holdout_size=120,protected_holdout_min=100,protected_holdout_max=200,min_holdout_rows=80,min_development_folds=2),
        development_gate=DevelopmentGateConfig(enabled=False),
        adversarial=AdversarialConfig(permutation_iterations=31,bootstrap_iterations=40,max_feature_ablation_groups=3),
        promotion=PromotionConfig(require_execution_safe_identity=False,min_trade_count=1,min_trade_sharpe_like=-999,min_profit_factor=0,max_permutation_pvalue=1,max_drift_score=1,min_fold_pass_rate=0,min_robustness_score=0,min_threshold_survival_rate=0,min_cost_survival_rate=0,require_positive_bootstrap_median=False,min_bootstrap_positive_fraction=0),
        runtime=RuntimeConfig(registry_path='artifacts/test.sqlite3',output_dir='artifacts/runs',candidate_dir='artifacts/candidates',shadow_path='artifacts/shadow.sqlite3',identity_manifest='config/source_identity.csv'),
    )
    report=research_file(src,tmp_path,cfg,data_root=tmp_path,allow_holdout=False)
    assert report['status']=='development_qualified'
    assert report['protected_holdout_touched'] is False
    assert not (tmp_path/'artifacts/holdout_ledger.sqlite3').exists()
