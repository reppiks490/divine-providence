import numpy as np
import pandas as pd
import pytest

from nexus.ablation import SensorAblationEngine
from nexus.promotion import CausalTransformRegistry, TransformSpec
from nexus.synthetic import SyntheticTickerDefinition


def test_transform_registry_requires_prefix_invariance_before_promotable():
    x=pd.DataFrame({'x':np.arange(1,41,dtype=float)})
    reg=CausalTransformRegistry();spec=TransformSpec('rolling-mean','1','feature','a'*64)
    reg.register(spec)
    assert not reg.promotable('rolling-mean','1')
    cert,audit=reg.certify('rolling-mean','1',lambda d: pd.DataFrame({'m':d['x'].rolling(4,min_periods=1).mean()}),x)
    assert audit.passed and cert.verify() and reg.promotable('rolling-mean','1')
    assert reg.manifest()['production_authorized'] is False


def test_transform_registry_rejects_centered_future_leakage():
    x=pd.DataFrame({'x':np.arange(1,41,dtype=float)})
    reg=CausalTransformRegistry();reg.register(TransformSpec('centered','1','feature','b'*64))
    with pytest.raises(ValueError,match='causality certification failed'):
        reg.certify('centered','1',lambda d: pd.DataFrame({'m':d['x'].rolling(5,center=True,min_periods=1).mean()}),x)


def test_cluster_sector_or_representation_family_ablation_uses_same_generic_engine():
    idx=pd.RangeIndex(180)
    rng=np.random.default_rng(4)
    values=pd.DataFrame({
        'A':100*np.exp(np.cumsum(rng.normal(0,.002,len(idx)))),
        'B':80*np.exp(np.cumsum(rng.normal(0,.002,len(idx)))),
        'C':60*np.exp(np.cumsum(rng.normal(0,.002,len(idx)))),
        'D':50*np.exp(np.cumsum(rng.normal(0,.002,len(idx)))),
    },index=idx)
    d=SyntheticTickerDefinition('X',('A','B','C','D'),'equal',30,10,5,4.0)
    out=SensorAblationEngine().evaluate_clusters(values,d,{'tech':('A','B'),'macro':('C','D')})
    assert {x.removed for x in out}=={'cluster:tech','cluster:macro'}
    assert all(x.overlap>0 for x in out)


def test_transform_promotion_rejects_vacuous_causality_evidence():
    reg=CausalTransformRegistry()
    reg.register(TransformSpec('labels','1','feature','c'*64))
    x=pd.DataFrame({'x':np.arange(8,dtype=float)})
    with pytest.raises(ValueError,match='insufficient comparable evidence'):
        reg.certify(
            'labels','1',
            lambda d: pd.DataFrame({'label':['x']*len(d)},index=d.index),
            x,
        )
    assert not reg.promotable('labels','1')


def test_transform_spec_rejects_malformed_identity():
    with pytest.raises(ValueError,match='name'):
        TransformSpec('','1','feature','a'*64)
    with pytest.raises(ValueError,match='code_hash'):
        TransformSpec('x','1','feature','not-a-hash')
    with pytest.raises(ValueError,match='trimmed'):
        TransformSpec(' x ','1','feature','a'*64)
