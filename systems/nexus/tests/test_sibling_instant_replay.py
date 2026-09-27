from nexus.contracts import BarEvent, StreamIdentity, StreamManifest
from nexus.replay import ReplayBus
from nexus.lineage import DerivationRecord
from nexus.sibling_replay import SiblingInstantRouter
from nexus.lineage import DerivationRecord


def _manifest(symbol:str,sha:str):
    ident=StreamIdentity('csv','X',symbol,'1','clock:1m',f'{symbol}.csv',sha*64)
    return StreamManifest(ident,1,['time','open','high','low','close'],100,100,60,1.0,0,0,0)


def test_same_instant_bundle_is_atomic_and_never_authorizes_production():
    ma=_manifest('A','a'); mb=_manifest('B','b')
    ea=BarEvent(ma.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    eb=BarEvent(mb.identity.stream_id,100,0,2,3,1.5,2.5,None,'B.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({ea.stream_id:[ea],eb.stream_id:[eb]},require_available=True))
    state=next(bus.states_batches([batch],required_streams={ea.stream_id,eb.stream_id}))
    bundle=SiblingInstantRouter().package(
        batch=batch,state=state,manifests={ea.stream_id:ma,eb.stream_id:mb},
        factors={'risk':.2},topology={'entropy':.7},quality={'coverage':1.0},ood={'novelty':.1},ingested_ns=170,
    )
    assert bundle.decision_ns==160==batch.visible_ns==state.decision_ns
    assert bundle.production_authorized is False
    assert bundle.aion['production_authorized'] is False
    assert len(bundle.aion['observations'])==2
    assert bundle.argus['evidence_tier']=='CANDLE_PROXY' and bundle.argus['microstructure_truth'] is False
    assert bundle.argus['same_instant_batch_size']==2
    assert bundle.athena['same_instant_batch_size']==2 and bundle.athena['advisory_only'] is True
    assert bundle.daedalus['production_authorized'] is False and bundle.daedalus['status']=='RESEARCH_CANDIDATE_ONLY'
    assert len(bundle.bundle_hash)==64


def test_bundle_rejects_non_atomic_state_batch_mismatch():
    m=_manifest('A','a'); e=BarEvent(m.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({e.stream_id:[e]},require_available=True)); state=next(bus.states_batches([batch]))
    from dataclasses import replace
    bad=replace(state,batch_size=2)
    try:
        SiblingInstantRouter().package(batch=batch,state=bad,manifests={e.stream_id:m},factors={},topology={},quality={})
    except ValueError as ex:
        assert 'batch_size' in str(ex)
    else:
        raise AssertionError('expected mismatch rejection')


def test_same_instant_bundle_can_persist_exact_derivation_genealogy_to_aion():
    from nexus.lineage import DerivationRecord
    ma=_manifest('A','a')
    ea=BarEvent(ma.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({ea.stream_id:[ea]},require_available=True))
    state=next(bus.states_batches([batch],required_streams={ea.stream_id}))
    d=DerivationRecord.create(product_id='NEXUS:RISK',product_version='3',decision_ns=160,spec_hash='c'*64,input_hashes={'A':ma.identity.raw_sha256},code_version='test')
    bundle=SiblingInstantRouter().package(
        batch=batch,state=state,manifests={ea.stream_id:ma},factors={'risk':.2},topology={},quality={'coverage':1.0},derivation=d,
    )
    assert bundle.aion['derivation_hash']==d.derivation_hash
    assert len(bundle.aion['source_specs'])==2
    deriv_obs=[o for o in bundle.aion['observations'] if o['kind']=='context']
    assert len(deriv_obs)==1
    assert deriv_obs[0]['payload']['derivation_hash']==d.derivation_hash
    assert bundle.daedalus['candidate']['derivation_hash']==d.derivation_hash


def test_same_instant_bundle_rejects_derivation_from_another_decision_time():
    from nexus.lineage import DerivationRecord
    ma=_manifest('A','a')
    ea=BarEvent(ma.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({ea.stream_id:[ea]},require_available=True)); state=next(bus.states_batches([batch]))
    d=DerivationRecord.create(product_id='NEXUS:RISK',product_version='3',decision_ns=159,spec_hash='d'*64,input_hashes={'A':ma.identity.raw_sha256},code_version='test')
    import pytest
    with pytest.raises(ValueError,match='decision_ns'):
        SiblingInstantRouter().package(batch=batch,state=state,manifests={ea.stream_id:ma},factors={},topology={},quality={},derivation=d)


def test_same_instant_bundle_carries_aion_derivation_genealogy():
    m=_manifest('A','a'); e=BarEvent(m.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({e.stream_id:[e]},require_available=True)); state=next(bus.states_batches([batch]))
    d=DerivationRecord.create(product_id='NEXUS:RISK',product_version='2',decision_ns=160,spec_hash='b'*64,input_hashes={'A':m.identity.raw_sha256},code_version='test')
    bundle=SiblingInstantRouter().package(batch=batch,state=state,manifests={e.stream_id:m},factors={'risk':.2},topology={},quality={},factor_derivations=[d])
    assert bundle.aion['derivation_observations'][0]['payload']['derivation_hash']==d.derivation_hash
    assert bundle.aion['derivation_source_specs'][0]['sequence_policy']=='none'
    assert any(x.get('derivation_hash')==d.derivation_hash for x in bundle.argus['lineage'])


def test_same_instant_bundle_rejects_derivation_from_different_instant():
    m=_manifest('A','a'); e=BarEvent(m.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({e.stream_id:[e]},require_available=True)); state=next(bus.states_batches([batch]))
    d=DerivationRecord.create(product_id='NEXUS:RISK',product_version='2',decision_ns=159,spec_hash='b'*64,input_hashes={'A':m.identity.raw_sha256},code_version='test')
    import pytest
    with pytest.raises(ValueError,match='atomic replay instant'):
        SiblingInstantRouter().package(batch=batch,state=state,manifests={e.stream_id:m},factors={},topology={},quality={},factor_derivations=[d])


def test_same_instant_bundle_carries_exact_source_health_plane():
    from nexus.source_health import SourceHealthRegistry, SourceSLOPolicy
    m=_manifest('A','a')
    e=BarEvent(m.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({e.stream_id:[e]},require_available=True)); state=next(bus.states_batches([batch]))
    health=SourceHealthRegistry(); health.set_policy(e.stream_id,SourceSLOPolicy(max_receive_lag_ns_p95=20,max_gap_size=0))
    health.observe(e,received_ns=170)
    plane=health.snapshot(160)
    bundle=SiblingInstantRouter().package(batch=batch,state=state,manifests={e.stream_id:m},factors={},topology={},quality={},source_health=plane)
    assert bundle.aion['source_health']['plane_hash']==plane.plane_hash
    assert bundle.argus['source_health']['decision_ns']==160
    assert bundle.athena['source_health']['healthy_streams']==[e.stream_id]
    assert bundle.daedalus['candidate']['source_health']['healthy_fraction']==1.0


def test_same_instant_bundle_rejects_health_from_different_instant():
    from nexus.source_health import SourceHealthRegistry
    m=_manifest('A','a')
    e=BarEvent(m.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({e.stream_id:[e]},require_available=True)); state=next(bus.states_batches([batch]))
    health=SourceHealthRegistry(); health.observe(e,received_ns=170)
    import pytest
    with pytest.raises(ValueError,match='source_health decision_ns'):
        SiblingInstantRouter().package(batch=batch,state=state,manifests={e.stream_id:m},factors={},topology={},quality={},source_health=health.snapshot(159))


def test_same_instant_bundle_persists_source_health_without_execution_authority():
    from nexus.source_health import SourceHealthRegistry, SourceSLOPolicy
    ma=_manifest('A','a')
    ea=BarEvent(ma.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({ea.stream_id:[ea]},require_available=True)); state=next(bus.states_batches([batch]))
    health=SourceHealthRegistry(); health.set_policy(ea.stream_id,SourceSLOPolicy(max_receive_lag_ns_p95=20,max_gap_size=0))
    health.observe(ea,received_ns=170)
    plane=health.snapshot(state.decision_ns)
    bundle=SiblingInstantRouter().package(batch=batch,state=state,manifests={ea.stream_id:ma},factors={},topology={},quality={},source_health=plane,ingested_ns=170)
    assert bundle.aion['source_health_plane_hash']==plane.plane_hash
    hobs=[o for o in bundle.aion['observations'] if o['payload'].get('plane_hash')==plane.plane_hash]
    assert len(hobs)==1 and hobs[0]['kind']=='context'
    assert bundle.athena['source_health']['plane_hash']==plane.plane_hash
    assert bundle.daedalus['candidate']['source_health']['plane_hash']==plane.plane_hash
    assert bundle.production_authorized is False


def test_same_instant_bundle_rejects_health_plane_from_other_instant():
    from nexus.source_health import SourceHealthRegistry
    import pytest
    ma=_manifest('A','a')
    ea=BarEvent(ma.identity.stream_id,100,0,1,2,.5,1.5,None,'A.csv',available_ns=160,availability_basis='verified_bar_close')
    bus=ReplayBus(); batch=next(bus.merge_batches({ea.stream_id:[ea]},require_available=True)); state=next(bus.states_batches([batch]))
    plane=SourceHealthRegistry().snapshot(159)
    with pytest.raises(ValueError,match='source_health decision_ns'):
        SiblingInstantRouter().package(batch=batch,state=state,manifests={ea.stream_id:ma},factors={},topology={},quality={},source_health=plane)
