from daedalus.config import PromotionConfig
from daedalus.promotion import decide


def test_promotion_requires_every_gate():
    m={"auc":0.60,"brier_improvement":0.01,"sharpe":1.0,"max_drawdown":0.10,"profit_factor":1.4,"trade_count":100}
    d=decide(m,0.05,0.10,0.8,PromotionConfig(),bootstrap_median_return=0.01,bootstrap_positive_fraction=0.8,execution_safe_identity=True)
    assert d.promoted
    m["trade_count"]=1
    d=decide(m,0.05,0.10,0.8,PromotionConfig(),bootstrap_median_return=0.01,bootstrap_positive_fraction=0.8,execution_safe_identity=True)
    assert not d.promoted and "trade_count" in d.failed
