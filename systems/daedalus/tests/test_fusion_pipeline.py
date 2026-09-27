from dataclasses import replace

import numpy as np
import pandas as pd

from daedalus.config import DaedalusConfig
from daedalus.fusion_pipeline import research_fused_sources


def _frame(n, step, offset=0, seed=1):
    rng=np.random.default_rng(seed)
    ret=rng.normal(0,0.0015,n)
    close=100*np.exp(np.cumsum(ret))
    open_=np.r_[close[0],close[:-1]]
    spread=np.maximum(.01,close*.0005)
    return pd.DataFrame({
        'time':1_700_000_000+offset+np.arange(n)*step,
        'open':open_, 'high':np.maximum(open_,close)+spread,
        'low':np.minimum(open_,close)-spread, 'close':close,
        'volume':rng.integers(100,1000,n),
    })


def test_fused_research_uses_same_protected_protocol(tmp_path):
    execution=_frame(620,60,0,4)
    alt=_frame(900,37,11,5)
    ep=tmp_path/'EXEC, 1.csv'; ap=tmp_path/'ALT, event.csv'
    execution.to_csv(ep,index=False); alt.to_csv(ap,index=False)
    base=DaedalusConfig()
    cfg=replace(
        base,
        data=replace(base.data,min_rows=300,max_rows_per_file=None),
        features=replace(base.features,return_windows=(1,2,5),vol_windows=(5,10),range_windows=(5,10),volume_windows=(5,10),target_horizon=3,include_utc_calendar=False),
        validation=replace(base.validation,n_splits=2,min_train_size=180,test_size=70,purge_bars=3,embargo_bars=3,protected_holdout_size=100,protected_holdout_min=80,protected_holdout_max=120,min_holdout_rows=70,min_development_folds=1),
        development_gate=replace(base.development_gate,enabled=False),
        adversarial=replace(base.adversarial,permutation_iterations=9,bootstrap_iterations=10,max_feature_ablation_groups=1,cost_multipliers=(0.,1.),threshold_offsets=(0.,),temporal_segments=2),
        promotion=replace(base.promotion,require_execution_safe_identity=False,min_trade_count=1,min_trade_sharpe_like=-999,min_profit_factor=0,max_permutation_pvalue=1,max_drift_score=1,min_fold_pass_rate=0,min_robustness_score=0,min_threshold_survival_rate=0,min_cost_survival_rate=0,require_positive_bootstrap_median=False,min_bootstrap_positive_fraction=0),
        runtime=replace(base.runtime,registry_path='artifacts/test.sqlite3',output_dir='artifacts/runs',candidate_dir='artifacts/candidates',shadow_path='artifacts/shadow.sqlite3',holdout_ledger_path='artifacts/holdout.sqlite3',strict_holdout_ledger=True),
    )
    report=research_fused_sources(ep,{'alt':ap},tmp_path,cfg,data_root=tmp_path)
    assert report['status']=='ok'
    assert report['research_mode']=='cross_representation_fusion'
    assert report['fusion']['diagnostics']['target_entry']=='execution_open'
    assert report['protocol_context']['mode']=='cross_representation_fusion_v1'
    assert report['final_candidate']['holdout_protocol_clean'] is True
