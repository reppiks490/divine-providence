from pathlib import Path
import pytest
from nexus.tabular import iter_numeric_events
from nexus.vector_replay import VectorReplayBus
from nexus.ingest import BarClockPolicy, BackwardSourceTimeError
from nexus.adapters import aion_context_observation,aion_context_source_spec
from nexus.columns import AmbiguousColumnError


def test_generic_numeric_csv_preserves_duplicate_field_positions(tmp_path:Path):
    p=tmp_path/'sensor.csv'
    p.write_text('time,score,score,label\n100,1,2,x\n110,3,4,y\n120,5,6,z\n')
    ev=list(iter_numeric_events(p,'sensor'))
    assert len(ev)==2  # terminal unsealed under conservative policy
    assert ev[0].values()=={'score#1':1.0,'score#2':2.0}
    assert 'duplicate_header' in ev[0].quality_flags


def test_generic_time_duplicate_requires_explicit_choice(tmp_path:Path):
    p=tmp_path/'sensor.csv';p.write_text('time,time,x\n100,101,1\n')
    with pytest.raises(AmbiguousColumnError):list(iter_numeric_events(p,'s'))
    out=list(iter_numeric_events(p,'s',time_position=0,clock_policy=BarClockPolicy(source_stamp='close')))
    assert out[0].source_timestamp_ns==100_000_000_000


def test_vector_replay_is_batch_atomic_and_strict(tmp_path:Path):
    a=tmp_path/'a.csv';b=tmp_path/'b.csv'
    a.write_text('time,x\n100,1\n110,2\n')
    b.write_text('time,y\n100,3\n110,4\n')
    policy=BarClockPolicy(source_stamp='close')
    bus=VectorReplayBus(); states=list(bus.states({'a':iter_numeric_events(a,'a',clock_policy=policy),'b':iter_numeric_events(b,'b',clock_policy=policy)},required_streams={'a','b'}))
    assert states[0].batch_size==2 and states[0].values['a']['x#1']==1.0 and states[0].values['b']['y#1']==3.0


def test_vector_aion_context_requires_attested_basis(tmp_path:Path):
    p=tmp_path/'a.csv';p.write_text('time,x\n100,1\n')
    e=list(iter_numeric_events(p,'ctx',clock_policy=BarClockPolicy(source_stamp='close',basis='verified_bar_close')))[0]
    spec=aion_context_source_spec(source_id='ctx',representation_id='context:v1',symbol='CTX',source_sha256='a'*64,evidence_reference='a.csv')
    obs=aion_context_observation(e)
    assert spec['capabilities']==['context'] and obs['kind']=='context' and obs['payload']=={'x#1':1.0}


def test_generic_numeric_rejects_backward_source_time(tmp_path:Path):
    p=tmp_path/'backward-sensor.csv'
    p.write_text('time,x\n100,1\n90,2\n110,3\n')
    with pytest.raises(BackwardSourceTimeError):
        list(iter_numeric_events(p,'sensor'))


def test_vector_replay_expires_stale_context(tmp_path:Path):
    from nexus.contracts import VectorEvent
    old=VectorEvent('old',100,0,(('x#1',1.0),),'old',available_ns=100)
    trigger=VectorEvent('new',200,0,(('y#1',2.0),),'new',available_ns=200)
    states=list(VectorReplayBus().states(
        {'old':[old],'new':[trigger]},
        required_streams={'old','new'},
        max_age_ns=50,
    ))
    assert states[-1].decision_ns==200
    assert 'old' not in states[-1].values
    assert 'old' in states[-1].missing
    assert states[-1].values['new']['y#1']==2.0


def test_vector_replay_rejects_negative_max_age():
    with pytest.raises(ValueError,match='max_age_ns'):
        list(VectorReplayBus().states({},max_age_ns=-1))


def test_vector_event_rejects_invalid_numeric_structure():
    from nexus.contracts import VectorEvent
    with pytest.raises(ValueError,match='event_ns'):
        VectorEvent('s',-1,0,(('x',1.0),),'p')
    with pytest.raises(ValueError,match='unique'):
        VectorEvent('s',1,0,(('x',1.0),('x',2.0)),'p')
    with pytest.raises(ValueError,match='finite'):
        VectorEvent('s',1,0,(('x',float('nan')),),'p')


def test_vector_state_and_event_reject_empty_or_inconsistent_structure():
    from nexus.contracts import VectorEvent, VectorStatePacket
    with pytest.raises(ValueError,match='at least one'):
        VectorEvent('s',1,0,(),'p')
    with pytest.raises(ValueError,match='keys must match'):
        VectorStatePacket(
            10,{'s':{'x':1.0}},{},(),{'s':0},{'s':'p'}
        )
    with pytest.raises(ValueError,match='finite'):
        VectorStatePacket(
            10,{'s':{'x':float('inf')}},{'s':0},(),{'s':0},{'s':'p'}
        )


def test_vector_replay_rejects_coerced_option_types():
    from nexus.contracts import VectorEvent
    e=VectorEvent("a",10,0,(("x",1.0),),"a",available_ns=10)
    with pytest.raises(TypeError,match="require_available"):
        list(VectorReplayBus().merge({"a":[e]},require_available=1))
    with pytest.raises(ValueError,match="max_age_ns"):
        list(VectorReplayBus().states({"a":[e]},max_age_ns=1.5))
