from pathlib import Path
from nexus.catalog import CorpusCatalog
from nexus.representation import infer_representation_hypothesis

def test_duplicate_headers_and_bad_ohlc_are_explicit(tmp_path:Path):
    p=tmp_path/'X_Y, 1.csv';p.write_text('time,open,high,low,close,close\n100,1,2,0,1,9\n160,x,2,0,1,9\n220,2,1,3,2,9\n')
    m=CorpusCatalog(tmp_path).build()[0]
    assert 'duplicate_header' in m.quality_flags
    assert 'non_numeric' in m.quality_flags
    assert 'ohlc_inconsistent' in m.quality_flags
    assert m.metadata['usable_ohlc_rows']==1
    assert m.metadata['duplicate_header_positions']['close']==[4,5]

def test_representation_hypothesis_never_becomes_authority(tmp_path:Path):
    p=tmp_path/'X_Y, 1.csv';p.write_text('time,open,high,low,close\n100.001,1,2,0,1\n100.002,1,2,0,1\n100.003,1,2,0,1\n')
    m=CorpusCatalog(tmp_path).build()[0];h=infer_representation_hypothesis(m)
    assert h.kind=='event_or_transformed_candidate'
    assert h.authoritative is False
    assert m.metadata['representation_hypothesis']['authoritative'] is False
