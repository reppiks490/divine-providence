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
    events=[
        BarEvent('s',10,0,1,2,0.5,1.5,None,'p','research',(),10,0,9,'verified_bar_close'),
        BarEvent('s',20,1,1.5,2.5,1,2,100,'p','research',('x',),20,0,19,'verified_bar_close'),
    ]
    src=IterableMarketSource(_m(),events)
    store=NpyColumnarBarStore(tmp_path/'store')
    m=store.write(src.events())
    assert m.rows==2 and store.verify()
    out=list(store.iter_stream('s'))
    assert out==events
    # modify one numeric cell on disk; content verification must fail
    import numpy as np
    part=m.partitions[0].partition
    p=tmp_path/'store'/part/'close.npy'
    a=np.load(p,allow_pickle=False); a[0]=999; np.save(p,a,allow_pickle=False)
    assert not store.verify()


def test_parquet_frontier_reports_runtime_capability():
    assert isinstance(ParquetBarStore.available(),bool)
