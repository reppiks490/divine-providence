from pathlib import Path
import pytest
from nexus.columns import AmbiguousColumnError, profile_header, resolve_columns
from nexus.catalog import CorpusCatalog
from nexus.ingest import iter_bars, BarClockPolicy
from nexus.contracts import QualityFlag


def test_header_profile_preserves_duplicate_positions():
    h=profile_header(['time','open','high','low','close','close','volume'])
    assert h.duplicates['close']==(4,5)
    with pytest.raises(AmbiguousColumnError):
        resolve_columns(h)
    m=resolve_columns(h,explicit_positions={'close':5})
    assert m['close']==5


def test_ingest_requires_explicit_duplicate_core_choice(tmp_path:Path):
    p=tmp_path/'X, 1.csv'
    p.write_text('time,open,high,low,close,close\n100,1,3,0,1,2\n')
    with pytest.raises(AmbiguousColumnError):
        list(iter_bars(p,'s',clock_policy=BarClockPolicy(source_stamp='close')))
    rows=list(iter_bars(p,'s',clock_policy=BarClockPolicy(source_stamp='close'),column_positions={'close':5}))
    assert rows[0].close==2.0


def test_catalog_flags_duplicate_header_and_keeps_positions(tmp_path:Path):
    p=tmp_path/'X, 1.csv'
    p.write_text('time,open,high,low,close,close\n100,1,3,0,1,2\n110,2,4,1,2,3\n')
    m=CorpusCatalog(tmp_path).build()[0]
    assert QualityFlag.DUPLICATE_HEADER.value in m.quality_flags
    assert m.metadata['duplicate_header_positions']['close']==[4,5]


def test_catalog_tracks_bad_numeric_and_inconsistent_ohlc(tmp_path:Path):
    p=tmp_path/'BAD, 1.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n110,x,3,0,2\n120,2,1,3,2\n')
    m=CorpusCatalog(tmp_path).build()[0]
    assert m.metadata['nonnumeric_ohlc_rows']==1
    assert m.metadata['inconsistent_ohlc_rows']==1
    assert 'non_numeric' in m.quality_flags and 'ohlc_inconsistent' in m.quality_flags


def test_explicit_duplicate_position_must_be_exact_integer():
    h=profile_header(['time','open','high','low','close','close'])
    with pytest.raises(TypeError,match='integer'):
        resolve_columns(h,explicit_positions={'close':4.9})
    with pytest.raises(TypeError,match='explicit_positions'):
        resolve_columns(h,explicit_positions=[('close',4)])


def test_resolve_columns_rejects_normalized_semantic_key_collisions():
    h=profile_header(['time','open','high','low','close'])
    with pytest.raises(ValueError,match='duplicate explicit semantic'):
        resolve_columns(h,explicit_positions={'Close':4,' close ':4})
    with pytest.raises(ValueError,match='must be unique'):
        resolve_columns(h,required=('time','open'),optional=(' Open ',))
    resolved=resolve_columns(
        h,required=(' Time ',' OPEN ','HIGH','LOW','CLOSE'),optional=()
    )
    assert resolved=={'time':0,'open':1,'high':2,'low':3,'close':4}
