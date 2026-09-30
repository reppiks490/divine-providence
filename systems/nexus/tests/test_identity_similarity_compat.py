from pathlib import Path
import pandas as pd
import pytest
from nexus.identity_registry import IdentityRegistry, IdentityRecord
from nexus.identity import InstrumentRegistry, InstrumentSpec
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
    obs=aion_bar_observation(ev,available_ns=20,ingested_ns=21,availability_basis='observed_receipt')
    assert obs['available_ns']==20 and obs['evidence_tier']==1
    assert argus_candle_proxy_feature(name='x',value=1,event_ns=10,source_id='s',reason='csv')['evidence_tier']==1


def test_aion_source_is_candle_tier():
    ident=StreamIdentity('csv','CME','NQ','60','csv_export','x','a'*64)
    m=StreamManifest(ident,10,['time','open','high','low','close'],1,2,1,1.0,0,0,0)
    spec=aion_source_spec(m)
    assert spec['max_evidence_tier']==1 and spec['capabilities']==['bar']


def test_instrument_registry_alias_conflict_is_atomic():
    r=InstrumentRegistry()
    r.register(InstrumentSpec('nq','NQ','future',venue='CME',aliases=('NASDAQ FUT',)))
    with pytest.raises(ValueError,match='ambiguous alias'):
        r.register(InstrumentSpec('es','ES','future',venue='CME',aliases=('SP FUT','NASDAQ FUT')))
    with pytest.raises(KeyError):
        r.resolve('SP FUT')
    with pytest.raises(KeyError):
        r.get('es')


def test_compat_adapter_never_invents_receipt_basis_or_impossible_time():
    ev=BarEvent('s',10,0,1,2,0,1.5,None,'x')
    with pytest.raises(ValueError,match='attested availability basis'):
        aion_bar_observation(ev,available_ns=20)
    with pytest.raises(ValueError,match='before event'):
        aion_bar_observation(ev,available_ns=5,availability_basis='observed_receipt')


def test_execution_identity_requires_venue_representation_and_roll_policy():
    r=IdentityRegistry()
    with pytest.raises(ValueError,match='roll_policy'):
        IdentityRecord(
            's','NQ1!','future',venue='CME',representation_class='standard:20m',
            executable=True,continuous_contract=True,roll_policy=None,
            timestamp_semantics='bar_close',
        )
    good=IdentityRecord(
        'named','NQZ6','future',venue='CME',representation_class='standard:20m',
        executable=True,continuous_contract=False,timestamp_semantics='bar_close',
    )
    r.register(good)
    assert r.require_execution_safe('named')==good


def test_near_duplicate_repeated_times_require_sequence_identity():
    a=pd.DataFrame({
        'event_ns':[1,1,2],'open':[1.,2.,3.],'high':[2.,3.,4.],
        'low':[0.,1.,2.],'close':[1.5,2.5,3.5],
    })
    b=a.copy()
    with pytest.raises(ValueError,match='source_sequence'):
        NearDuplicateDetector(min_overlap=1).compare('a',a,'b',b)

    a['source_sequence']=[0,1,2]
    b['source_sequence']=[0,1,2]
    result=NearDuplicateDetector(min_overlap=3).compare('a',a,'b',b)
    assert result.overlap_rows==3
    assert result.identical_fraction==1.0
    assert result.likely_near_duplicate


def test_near_duplicate_configuration_is_validated():
    with pytest.raises(ValueError,match='min_overlap'):
        NearDuplicateDetector(min_overlap=0)
    with pytest.raises(ValueError,match='identical_threshold'):
        NearDuplicateDetector(identical_threshold=1.1)
    with pytest.raises(ValueError,match='corr_threshold'):
        NearDuplicateDetector(corr_threshold=float('nan'))


def test_instrument_alias_resolution_is_trimmed_and_case_normalized():
    r=InstrumentRegistry()
    spec=InstrumentSpec('nq','NQ','future',venue='CME',aliases=('NASDAQ FUT',))
    r.register(spec)
    assert r.resolve(' nq ') is spec
    assert r.resolve(' nasdaq fut ') is spec


def test_instrument_and_reviewed_identity_reject_malformed_contracts():
    with pytest.raises(ValueError,match='contract_kind'):
        InstrumentSpec('x','X','future',contract_kind='mystery')
    with pytest.raises(ValueError,match='execution_role'):
        InstrumentSpec('x','X','future',execution_role='live')
    with pytest.raises(ValueError,match='trimmed'):
        InstrumentSpec(' x ','X','future')
    with pytest.raises(ValueError,match='stream_id'):
        IdentityRecord('','NQ','future')
    with pytest.raises(ValueError,match='timestamp_semantics'):
        IdentityRecord('s','NQ','future',timestamp_semantics='tomorrow')


def test_stream_identity_requires_real_sha_and_canonicalizes_case():
    upper='A'*64
    ident=StreamIdentity('csv','CME','NQ','1','csv_export','x.csv',upper)
    assert ident.raw_sha256=='a'*64
    assert ident.stream_id.endswith('a'*12)
    with pytest.raises(ValueError,match='raw_sha256'):
        StreamIdentity('csv','CME','NQ','1','csv_export','x.csv','not-a-hash')
    with pytest.raises(ValueError,match='source_id'):
        StreamIdentity('','CME','NQ','1','csv_export','x.csv','a'*64)


def test_stream_manifest_rejects_invalid_structural_fields():
    ident=StreamIdentity('csv','CME','NQ','1','csv_export','x.csv','a'*64)
    with pytest.raises(ValueError,match='row_count'):
        StreamManifest(ident,-1,[],None,None,None,0.0,0,0,0)
    with pytest.raises(ValueError,match='cadence_confidence'):
        StreamManifest(ident,1,['time'],1,1,None,float('nan'),0,0,0)
    with pytest.raises(ValueError,match='observed_cadence_ns'):
        StreamManifest(ident,1,['time'],1,1,0,1.0,0,0,0)
    with pytest.raises(ValueError,match='cannot exceed row_count'):
        StreamManifest(ident,1,['time'],1,1,1,1.0,2,0,0)


def test_identity_record_rejects_invalid_reviewed_metadata():
    with pytest.raises(ValueError,match='invalid timezone'):
        IdentityRecord('s','NQ','future',timezone='Mars/Chicago')
    with pytest.raises(ValueError,match='venue'):
        IdentityRecord('s','NQ','future',venue=' CME ')
    with pytest.raises(ValueError,match='volume_semantics'):
        IdentityRecord('s','NQ','future',volume_semantics='')
    with pytest.raises(TypeError,match='record'):
        IdentityRegistry().register(object())
