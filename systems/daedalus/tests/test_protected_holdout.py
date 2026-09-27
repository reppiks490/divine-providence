from daedalus.config import ValidationConfig
from daedalus.validation import split_development_holdout


def test_protected_holdout_is_separated_by_purge():
    cfg=ValidationConfig(protected_holdout_size=100,purge_bars=7)
    dev_end,holdout_start=split_development_holdout(1000,cfg,target_horizon=5)
    assert holdout_start == 900
    assert holdout_start-dev_end == 7


def test_target_horizon_can_widen_purge_gap():
    cfg=ValidationConfig(protected_holdout_size=100,purge_bars=3)
    dev_end,holdout_start=split_development_holdout(1000,cfg,target_horizon=10)
    assert holdout_start-dev_end == 10
