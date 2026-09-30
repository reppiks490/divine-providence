from pathlib import Path
import numpy as np
import pandas as pd
from nexus.contracts import BarEvent
from nexus.replay import ReplayBus
from nexus.ledger import MarketFabricLedger
from nexus.synthetic import SyntheticTickerDefinition, AdaptiveTickerEngine
from nexus.ablation import SensorAblationEngine
from nexus.registry import FactorRegistry, FactorSpec


def e(s,event,avail,q,c): return BarEvent(s,event,q,c,c,c,c,None,s,available_ns=avail)


def test_availability_not_event_time_controls_visibility():
    merged=list(ReplayBus().merge({'macro':[e('macro',10,100,0,5)], 'price':[e('price',20,20,0,2),e('price',90,90,1,3)]}))
    assert [x.stream_id for x in merged]==['price','price','macro']
    states=list(ReplayBus().states(merged))
    before=next(x for x in states if x.decision_ns==90)
    assert 'macro' not in before.values
    assert states[-1].decision_ns==100 and states[-1].values['macro']==5


def test_hash_chained_ledger(tmp_path:Path):
    l=MarketFabricLedger(tmp_path/'ledger.db')
    h1=l.append(1,'frame',{'x':1}); h2=l.append(2,'factor',{'y':2})
    assert h1!=h2 and l.verify()
    l.close()


def test_factor_registry_is_immutable_by_version():
    r=FactorRegistry(); s=FactorSpec('NEXUS:RISK','1',('A','B'),'equal')
    r.register(s); r.register(s)
    try:
        r.register(FactorSpec('NEXUS:RISK','1',('A','C'),'equal'))
        assert False
    except ValueError: pass


def test_ablation_scores_fragility():
    n=120; rng=np.random.default_rng(4)
    a=100*np.exp(np.cumsum(rng.normal(0,.01,n)))
    b=100*np.exp(np.cumsum(rng.normal(0,.01,n)))
    c=100*np.exp(np.cumsum(rng.normal(0,.01,n)))
    x=pd.DataFrame({'A':a,'B':b,'C':c})
    d=SyntheticTickerDefinition('NEXUS:X',('A','B','C'),method='equal',window=40,min_periods=20,rebalance_every=5)
    results=SensorAblationEngine().evaluate(x,d)
    assert {r.removed for r in results}=={'A','B','C'}
    assert all(r.overlap>0 for r in results)


def test_ablation_preserves_component_weight_cap():
    n=140; rng=np.random.default_rng(11)
    x=pd.DataFrame({
        'A':100*np.exp(np.cumsum(rng.normal(0,.01,n))),
        'B':100*np.exp(np.cumsum(rng.normal(0,.01,n))),
        'C':100*np.exp(np.cumsum(rng.normal(0,.01,n))),
        'D':100*np.exp(np.cumsum(rng.normal(0,.01,n))),
    })
    d=SyntheticTickerDefinition(
        'NEXUS:CAP',tuple(x.columns),method='equal',
        window=50,min_periods=25,rebalance_every=5,max_component_weight=.6,
    )
    # Removing one of four leaves three components, so the .6 cap remains feasible.
    results=SensorAblationEngine().evaluate(x,d)
    assert len(results)==4
    # Regression target: ablation definitions inherit the cap rather than defaulting to 1.0.
    for removed in d.components:
        keep=tuple(c for c in d.components if c!=removed)
        sub=SyntheticTickerDefinition(
            d.name+f':minus:{removed}',keep,d.method,d.window,d.min_periods,
            d.rebalance_every,d.clip_z,d.max_component_weight,
        )
        out=AdaptiveTickerEngine().build(x,sub)
        assert float(out.filter(like='w:').abs().max().max()) <= .6000001


def test_ledger_rejects_invalid_identity_and_nonfinite_payload(tmp_path:Path):
    import pytest
    l=MarketFabricLedger(tmp_path/'strict-ledger.db')
    with pytest.raises(ValueError,match='visible_ns'):
        l.append(-1,'frame',{'x':1})
    with pytest.raises(ValueError,match='kind'):
        l.append(1,'   ',{'x':1})
    with pytest.raises(ValueError):
        l.append(1,'frame',{'x':float('nan')})
    with pytest.raises(ValueError,match='non-negative'):
        l.tail(-1)
    assert l.count()==0
    l.close()


def test_factor_spec_rejects_malformed_identity():
    import pytest
    with pytest.raises(ValueError,match='required'):
        FactorSpec('','1',('A',),'equal')
    with pytest.raises(ValueError,match='unique'):
        FactorSpec('x','1',('A','A'),'equal')
    with pytest.raises(ValueError,match='parameter'):
        FactorSpec('x','1',('A',),'equal',parameters=(('p',1),('p',2)))
    with pytest.raises(ValueError,match='finite canonical'):
        FactorSpec('x','1',('A',),'equal',parameters=(('p',float('nan')),))
    with pytest.raises(ValueError,match='dependencies'):
        FactorSpec('x','1',('A',),'equal',dependencies=(('','1'),))
