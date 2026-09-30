from pathlib import Path
import pytest
from nexus.ingest import iter_bars,iter_bars_streaming,BarClockPolicy,BackwardSourceTimeError
from nexus.storage import NpyColumnarBarStore
from nexus.ledger import MarketFabricLedger
from nexus.checkpoint import ReplayCheckpoint
from nexus.fabric import FabricCheckpointManifest
from nexus.contracts import StatePacket

def test_streaming_matches_buffered_on_monotone_repeated_times(tmp_path:Path):
    p=tmp_path/'x.csv';p.write_text('time,open,high,low,close\n100,1,2,0,1\n100,1,3,0,2\n110,2,4,1,3\n120,3,5,2,4\n')
    a=list(iter_bars(p,'s'));b=list(iter_bars_streaming(p,'s'))
    assert a==b and [x.source_sequence for x in b]==[0,1,2]

def test_streaming_rejects_backward_time_instead_of_sorting(tmp_path:Path):
    p=tmp_path/'x.csv';p.write_text('time,open,high,low,close\n100,1,2,0,1\n90,1,2,0,1\n110,1,2,0,1\n')
    with pytest.raises(BackwardSourceTimeError):list(iter_bars_streaming(p,'s'))

def test_streamwise_columnar_and_fabric_checkpoint(tmp_path:Path):
    p=tmp_path/'x.csv';p.write_text('time,open,high,low,close\n100,1,2,0,1\n110,2,3,1,2\n120,3,4,2,3\n')
    events=list(iter_bars_streaming(p,'s',clock_policy=BarClockPolicy(source_stamp='close')))
    store=NpyColumnarBarStore(tmp_path/'store');sm=store.write_streams({'s':events});assert store.verify() and sm.rows==3
    led=MarketFabricLedger(tmp_path/'ledger.sqlite');led.append(100,'bar',{'s':1});head=led.head_hash();assert led.verify() and led.count()==1
    state=StatePacket(100,{'s':1.0},{'s':0},(),{'s':0},{'s':str(p)},frame_hash='f');cp=ReplayCheckpoint.from_state(state)
    f=FabricCheckpointManifest.create(decision_ns=100,catalog_sha256='a'*64,event_store_sha256=sm.content_sha256,ledger_head_sha256=head,replay_checkpoint_sha256=cp.checkpoint_hash,code_version='0.2.0')
    q=tmp_path/'fabric.json';f.save(q);assert FabricCheckpointManifest.load(q).verify();led.close()


def test_buffered_rejects_backward_time_too(tmp_path:Path):
    p=tmp_path/'backward.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n90,1,2,0,1\n110,1,2,0,1\n')
    with pytest.raises(BackwardSourceTimeError):
        list(iter_bars(p,'s'))


def test_streaming_verified_close_does_not_bypass_backward_time_guard(tmp_path:Path):
    p=tmp_path/'backward-close.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n90,1,2,0,1\n')
    with pytest.raises(BackwardSourceTimeError):
        list(iter_bars_streaming(p,'s',clock_policy=BarClockPolicy(source_stamp='close')))


def test_fabric_checkpoint_rejects_invalid_identity_fields(tmp_path:Path):
    import dataclasses
    with pytest.raises(ValueError,match='identity fields'):
        FabricCheckpointManifest.create(
            decision_ns=-1,catalog_sha256='a'*64,event_store_sha256='b'*64,
            ledger_head_sha256='c'*64,replay_checkpoint_sha256='d'*64,code_version='1',
        )
    with pytest.raises(ValueError,match='identity fields'):
        FabricCheckpointManifest.create(
            decision_ns=1,catalog_sha256='bad',event_store_sha256='b'*64,
            ledger_head_sha256='c'*64,replay_checkpoint_sha256='d'*64,code_version='1',
        )
    good=FabricCheckpointManifest.create(
        decision_ns=1,catalog_sha256='a'*64,event_store_sha256='b'*64,
        ledger_head_sha256='c'*64,replay_checkpoint_sha256='d'*64,code_version='1',
    )
    assert good.verify()
    bad=dataclasses.replace(good,schema='wrong')
    assert not bad.verify()
    with pytest.raises(ValueError,match='refusing'):
        bad.save(tmp_path/'bad.json')


def test_fabric_load_rejects_tampered_checkpoint_by_default(tmp_path:Path):
    import json
    good=FabricCheckpointManifest.create(
        decision_ns=1,catalog_sha256='a'*64,event_store_sha256='b'*64,
        ledger_head_sha256='c'*64,replay_checkpoint_sha256='d'*64,code_version='1',
    )
    p=tmp_path/'fabric-tamper.json';good.save(p)
    body=json.loads(p.read_text());body['decision_ns']=2;p.write_text(json.dumps(body))
    with pytest.raises(ValueError,match='verification'):
        FabricCheckpointManifest.load(p)
    assert not FabricCheckpointManifest.load(p,verify=False).verify()
    with pytest.raises(TypeError,match='verify'):
        FabricCheckpointManifest.load(p,verify=1)
