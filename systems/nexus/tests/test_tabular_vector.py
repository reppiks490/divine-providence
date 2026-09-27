from pathlib import Path
import pytest
from nexus.tabular import iter_numeric_events
from nexus.vector_replay import VectorReplayBus
from nexus.ingest import BarClockPolicy
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
