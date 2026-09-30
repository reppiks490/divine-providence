from pathlib import Path
import numpy as np
import pandas as pd
from nexus.ood import RollingMahalanobisOOD, KernelShiftSensor
from nexus.contracts import StatePacket, StreamIdentity, StreamManifest, BarEvent
from nexus.checkpoint import ReplayCheckpoint
from nexus.adapters import market_state_packet, aion_source_spec, aion_bar_observation


def test_ood_is_trailing_only_and_flags_large_shift():
    rng=np.random.default_rng(3)
    base=rng.normal(0,1,(140,3)); shock=np.array([[12.0,12.0,12.0]])
    x=pd.DataFrame(np.vstack([base,shock]),columns=list('abc'))
    out=RollingMahalanobisOOD(window=100,min_periods=60,threshold=4.0).score(x)
    assert bool(out.iloc[-1]['ood'])
    assert out.iloc[-1]['ood_score']>=4.0


def test_kernel_shift_increases_for_distribution_change():
    rng=np.random.default_rng(8)
    stable=pd.DataFrame(rng.normal(0,1,(160,2)))
    shifted=pd.DataFrame(np.vstack([rng.normal(0,1,(80,2)),rng.normal(4,1,(80,2))]))
    k=KernelShiftSensor(window=80,min_periods=40)
    assert k.score_at_end(shifted)>k.score_at_end(stable)


def test_checkpoint_roundtrip(tmp_path:Path):
    s=StatePacket(10,{'a':1.0},{'a':0},(),{'a':1},{'a':'x'},frame_hash='abc')
    cp=ReplayCheckpoint.from_state(s); p=tmp_path/'cp.json'; cp.save(p)
    loaded=ReplayCheckpoint.load(p)
    assert loaded.verify() and loaded.checkpoint_hash==cp.checkpoint_hash


def test_strict_aion_adapter_requires_availability():
    ident=StreamIdentity('csv','CME','NQ','60','time','x.csv','a'*64)
    m=StreamManifest(ident,1,['time','open','high','low','close'],1,1,60,1.0,0,0,0)
    spec=aion_source_spec(m)
    assert spec['max_evidence_tier']==1 and spec['origin']=='historical_csv'
    unknown=BarEvent(ident.stream_id,1,0,1,1,1,1,None,'x.csv')
    try:
        aion_bar_observation(unknown)
        assert False
    except ValueError:
        pass
    known=BarEvent(ident.stream_id,1,0,1,1,1,1,None,'x.csv',available_ns=2)
    obs=aion_bar_observation(known,availability_basis='observed_receipt')
    assert obs['available_ns']==2 and obs['evidence_tier']==1
    p=market_state_packet(decision_ns=2,factors={},topology={},quality={},lineage=[])
    assert p['contract']=='nexus.market-state.v2' and p['production_authorized'] is False


def test_checkpoint_top_level_metadata_is_bound_to_state(tmp_path:Path):
    import json
    s=StatePacket(10,{'a':1.0},{'a':0},(),{'a':1},{'a':'x'},frame_hash='abc')
    cp=ReplayCheckpoint.from_state(s); p=tmp_path/'cp-bind.json'; cp.save(p)
    raw=json.loads(p.read_text())
    raw['decision_ns']=11
    p.write_text(json.dumps(raw))
    assert not ReplayCheckpoint.load(p).verify()
    raw=json.loads(cp_path.read_text()) if False else None


def test_checkpoint_top_level_frame_hash_tamper_fails(tmp_path:Path):
    import json
    s=StatePacket(10,{'a':1.0},{'a':0},(),{'a':1},{'a':'x'},frame_hash='abc')
    cp=ReplayCheckpoint.from_state(s); p=tmp_path/'cp-frame.json'; cp.save(p)
    raw=json.loads(p.read_text());raw['frame_hash']='tampered';p.write_text(json.dumps(raw))
    assert not ReplayCheckpoint.load(p).verify()
