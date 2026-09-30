from pathlib import Path
from nexus.contracts import BarEvent,StreamIdentity,StreamManifest
from nexus.sources import SQLiteMarketSource
from nexus.storage import SQLiteBarStore


def _manifest():
    i=StreamIdentity('sqlite','X','Y','1','clock:1m','db','a'*64)
    return StreamManifest(i,2,['time','open','high','low','close'],10,20,10,1.0,0,0,0)


def test_sqlite_append_roundtrip_and_content_hash(tmp_path:Path):
    m=_manifest();ev=[
        BarEvent(m.identity.stream_id,10,0,1,2,.5,1.5,None,'x',available_ns=11,availability_basis='observed_receipt'),
        BarEvent(m.identity.stream_id,20,1,2,3,1.5,2.5,5,'x',quality_flags=('q',),available_ns=21,revision=1,source_timestamp_ns=19,availability_basis='observed_receipt'),
    ]
    store=SQLiteBarStore(tmp_path/'events.db');assert store.append(ev)==2
    assert store.stream_ids()==(m.identity.stream_id,)
    out=list(store.iter_stream(m.identity.stream_id));assert out==ev
    h1=store.content_sha256();h2=store.content_sha256();assert h1==h2 and len(h1)==64
    src=SQLiteMarketSource(m,tmp_path/'events.db');assert list(src.events())==ev


def test_sqlite_same_revision_duplicate_is_rejected(tmp_path:Path):
    m=_manifest();e=BarEvent(m.identity.stream_id,10,0,1,2,.5,1.5,None,'x',available_ns=11,availability_basis='observed_receipt')
    s=SQLiteBarStore(tmp_path/'e.db');s.append([e])
    try:s.append([e])
    except Exception:pass
    else:raise AssertionError('expected primary-key rejection')


def test_sqlite_replace_mode_is_idempotent_not_mutating(tmp_path:Path):
    import pytest
    m=_manifest()
    original=BarEvent(
        m.identity.stream_id,10,0,1,2,.5,1.5,None,'x',
        available_ns=11,availability_basis='observed_receipt'
    )
    s=SQLiteBarStore(tmp_path/'idempotent.db')
    assert s.append([original])==1
    assert s.append([original],replace_same_revision=True)==1
    changed=BarEvent(
        m.identity.stream_id,10,0,1,2,.5,9.5,None,'x',
        available_ns=11,availability_basis='observed_receipt'
    )
    with pytest.raises(ValueError,match='conflicting payload'):
        s.append([changed],replace_same_revision=True)
    assert list(s.iter_stream(m.identity.stream_id))==[original]
