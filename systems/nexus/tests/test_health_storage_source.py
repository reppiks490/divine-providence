from pathlib import Path

from nexus.contracts import BarEvent, StatePacket, StreamIdentity, StreamManifest
from nexus.quality_state import QualityStateEngine
from nexus.sources import IterableMarketSource
from nexus.storage import NpyColumnarBarStore, ParquetBarStore


def _m(sid='csv:X:a'):
    return StreamManifest(StreamIdentity('csv','X','Y','1','csv_export','x.csv','a'*64),10,['time','open','high','low','close'],0,9,10,1.0,0,0,0,quality_flags=[])


def test_dynamic_health_tracks_missing_and_stale_without_imputation():
    m1=_m('a'); m2=_m('b')
    # stream ids in mapping are the canonical ids that the state uses
    state=StatePacket(100,{'a':1.0},{'a':35},('b',),{'a':1},{'a':'x'},frame_hash='f')
    h=QualityStateEngine().build(state,{'a':m1,'b':m2},stale_after_multiples=2.0)
    assert h.missing_count==1
    assert h.stale_fraction==0.5
    assert h.streams['b'].dynamic_quality==0.0
    assert 'b' not in state.values  # health never fills a market value


def test_npy_columnar_roundtrip_and_tamper_detection(tmp_path:Path):
    manifest=_m()
    sid=manifest.identity.stream_id
    events=[
        BarEvent(sid,10,0,1,2,0.5,1.5,None,'p','research',(),10,0,9,'verified_bar_close'),
        BarEvent(sid,20,1,1.5,2.5,1,2,100,'p','research',('x',),20,0,19,'verified_bar_close'),
    ]
    src=IterableMarketSource(manifest,events)
    store=NpyColumnarBarStore(tmp_path/'store')
    m=store.write(src.events())
    assert m.rows==2 and store.verify()
    out=list(store.iter_stream(sid))
    assert out==events
    # modify one numeric cell on disk; content verification must fail
    import numpy as np
    part=m.partitions[0].partition
    p=tmp_path/'store'/part/'close.npy'
    a=np.load(p,allow_pickle=False); a[0]=999; np.save(p,a,allow_pickle=False)
    assert not store.verify()


def test_parquet_frontier_reports_runtime_capability():
    assert isinstance(ParquetBarStore.available(),bool)


def test_empty_quality_plane_is_not_perfect_health():
    state=StatePacket(100,{}, {}, (), {}, {}, frame_hash='empty')
    h=QualityStateEngine().build(state,{})
    assert h.coverage==0.0
    assert h.mean_quality==0.0
    assert h.min_quality==0.0
    assert h.missing_count==0


def test_npy_manifest_version_and_backend_are_verified(tmp_path:Path):
    import json
    events=[BarEvent('s',10,0,1,2,.5,1.5,None,'p',available_ns=10)]
    store=NpyColumnarBarStore(tmp_path/'store-meta')
    store.write(events)
    path=tmp_path/'store-meta'/'manifest.json'
    raw=json.loads(path.read_text())
    raw['version']='forged'
    path.write_text(json.dumps(raw))
    assert not store.verify()


def test_dynamic_quality_rejects_negative_timing_inputs():
    from nexus.quality import dynamic_state_quality
    import pytest
    with pytest.raises(ValueError,match='age_ns'):
        dynamic_state_quality(base_score=1.0,age_ns=-1,cadence_ns=10)
    with pytest.raises(ValueError,match='clock_uncertainty_ns'):
        dynamic_state_quality(base_score=1.0,age_ns=0,cadence_ns=10,clock_uncertainty_ns=-1)
    with pytest.raises(ValueError,match='cadence_ns'):
        dynamic_state_quality(base_score=1.0,age_ns=0,cadence_ns=0)


def test_npy_store_rejects_duplicate_ordering_keys(tmp_path:Path):
    import pytest
    a=BarEvent('s',10,0,1,2,.5,1.5,None,'p',available_ns=10)
    b=BarEvent('s',10,0,1,2,.5,1.5,None,'p2',available_ns=10)
    with pytest.raises(ValueError,match='ordering keys'):
        NpyColumnarBarStore(tmp_path/'dups').write([a,b])


def test_npy_store_rejects_out_of_order_input_instead_of_sorting(tmp_path:Path):
    import pytest
    late=BarEvent('s',20,1,1,2,.5,1.5,None,'p',available_ns=20)
    early=BarEvent('s',10,0,1,2,.5,1.5,None,'p',available_ns=10)
    with pytest.raises(ValueError,match='ordering keys'):
        NpyColumnarBarStore(tmp_path/'out-of-order').write([late,early])


def test_quality_plane_rejects_negative_clock_uncertainty():
    import pytest
    state=StatePacket(100,{'a':1.0},{'a':0},(),{'a':1},{'a':'x'},frame_hash='f')
    with pytest.raises(ValueError,match='clock_uncertainty_ns'):
        QualityStateEngine().build(state,{'a':_m()},clock_uncertainty_ns={'a':-1})


def test_iterable_source_rejects_manifest_stream_mismatch_and_merges_quality():
    import pytest
    manifest=_m()
    manifest.quality_flags=['claim_mismatch']
    sid=manifest.identity.stream_id
    good=BarEvent(sid,10,0,1,2,.5,1.5,None,'p',quality_flags=('local',),available_ns=10)
    out=list(IterableMarketSource(manifest,[good]).events())
    assert out[0].quality_flags==('local','claim_mismatch')

    bad=BarEvent('wrong',10,0,1,2,.5,1.5,None,'p',available_ns=10)
    with pytest.raises(ValueError,match='manifest stream_id'):
        list(IterableMarketSource(manifest,[bad]).events())


def test_csv_source_propagates_manifest_quality_flags(tmp_path:Path):
    from nexus.sources import CSVMarketSource
    from nexus.ingest import BarClockPolicy
    p=tmp_path/'x.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n')
    manifest=_m()
    manifest.identity = StreamIdentity(
        manifest.identity.source_id,manifest.identity.venue,manifest.identity.symbol,
        manifest.identity.filename_claim,manifest.identity.representation,
        str(p),manifest.identity.raw_sha256,
    )
    manifest.quality_flags=['claim_mismatch']
    events=list(CSVMarketSource(
        manifest,BarClockPolicy(source_stamp='close')
    ).events())
    assert len(events)==1
    assert 'claim_mismatch' in events[0].quality_flags


def test_quality_scoring_fails_closed_on_corrupt_telemetry():
    import pytest
    from nexus.quality import quality_score,dynamic_state_quality
    m=_m()
    m.metadata['nonnumeric_ohlc_rows']=-1
    assert quality_score(m)==0.0

    m=_m();m.metadata['inconsistent_ohlc_rows']=m.row_count+1
    assert quality_score(m)==0.0

    for value in (float('nan'),float('inf'),-0.1,1.1):
        with pytest.raises(ValueError,match='base_score'):
            dynamic_state_quality(
                base_score=value,age_ns=0,cadence_ns=10
            )
    with pytest.raises(ValueError,match='age_ns'):
        dynamic_state_quality(base_score=1.0,age_ns=1.5,cadence_ns=10)
    with pytest.raises(ValueError,match='cadence_ns'):
        dynamic_state_quality(base_score=1.0,age_ns=0,cadence_ns=10.0)
    with pytest.raises(TypeError,match='missing'):
        dynamic_state_quality(base_score=1.0,age_ns=0,cadence_ns=10,missing=1)
