from pathlib import Path
import pandas as pd
import pytest
from nexus.identity_registry import IdentityRegistry, IdentityRecord
from nexus.similarity import NearDuplicateDetector
from nexus.contracts import BarEvent, StreamIdentity, StreamManifest
from nexus.compat import aion_bar_observation, aion_source_spec, argus_candle_proxy_feature


def test_identity_registry_requires_review_for_execution():
    r=IdentityRegistry(); rec=IdentityRecord('s','NQ','future',executable=False)
    r.register(rec)
    with pytest.raises(ValueError): r.require_execution_safe('s')


def test_near_duplicate_preserves_detection_not_deletion():
    a=pd.DataFrame({'event_ns':range(200),'open':1.,'high':2.,'low':0.,'close':1.})
    b=a.copy(); b.loc[0,'close']=1.1
    x=NearDuplicateDetector(min_overlap=100,identical_threshold=.99).compare('a',a,'b',b)
    assert x.likely_near_duplicate and x.overlap_rows==200


def test_aion_compat_refuses_unproved_availability():
    ev=BarEvent('s',10,0,1,2,0,1.5,None,'x')
    with pytest.raises(ValueError): aion_bar_observation(ev)
    obs=aion_bar_observation(ev,available_ns=20,ingested_ns=21)
    assert obs['available_ns']==20 and obs['evidence_tier']==1
    assert argus_candle_proxy_feature(name='x',value=1,event_ns=10,source_id='s',reason='csv')['evidence_tier']==1


def test_aion_source_is_candle_tier():
    ident=StreamIdentity('csv','CME','NQ','60','csv_export','x','a'*64)
    m=StreamManifest(ident,10,['time','open','high','low','close'],1,2,1,1.0,0,0,0)
    spec=aion_source_spec(m)
    assert spec['max_evidence_tier']==1 and spec['capabilities']==['bar']
