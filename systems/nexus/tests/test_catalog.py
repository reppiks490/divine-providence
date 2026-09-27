from pathlib import Path
from nexus.catalog import CorpusCatalog, infer_cadence_ns
from nexus.quality import quality_score


def test_catalog_filters_appledouble(tmp_path: Path):
    good=tmp_path/'X_TEST, 1.csv'
    good.write_text('time,open,high,low,close\n100,1,2,0,1.5\n160,1.5,2,1,1.8\n220,1.8,2,1,1.9\n')
    bad=tmp_path/'._X_TEST, 1.csv'
    bad.write_bytes(b'not csv')
    m=CorpusCatalog(tmp_path).build()
    assert len(m)==2
    gm=next(x for x in m if x.identity.source_path==good.name)
    bm=next(x for x in m if x.identity.source_path==bad.name)
    assert gm.observed_cadence_ns==60_000_000_000
    assert 'appledouble' in bm.quality_flags
    assert quality_score(bm)==0


def test_infer_cadence_ignores_session_gap():
    times=[0,60,120,180,3600,3660,3720]
    cadence,confidence,repeats,backwards=infer_cadence_ns(times)
    assert cadence==60
    assert confidence > .7
    assert repeats==0 and backwards==0
