from pathlib import Path
import zipfile
from nexus.archive import ZipCorpusCatalog
from nexus.catalog import CorpusCatalog
from nexus.reconcile import reconcile


def test_zip_catalog_profiles_without_extraction_and_skips_sidecar(tmp_path:Path):
    z=tmp_path/'batch.zip'
    with zipfile.ZipFile(z,'w') as f:
        f.writestr('AAPL, 1.csv','time,open,high,low,close\n100,1,2,0,1\n110,2,3,1,2\n')
        f.writestr('__MACOSX/._AAPL, 1.csv','junk')
    ms=ZipCorpusCatalog(tmp_path).build()
    assert len(ms)==2
    good=next(m for m in ms if 'appledouble' not in m.quality_flags)
    assert good.row_count==2 and good.metadata['archive_member']=='AAPL, 1.csv'
    assert good.identity.source_path.startswith('batch.zip!')


def test_reconcile_compares_content_not_filenames(tmp_path:Path):
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    text='time,open,high,low,close\n100,1,2,0,1\n110,2,3,1,2\n'
    (a/'X, 1.csv').write_text(text);(b/'RENAMED, 1.csv').write_text(text)
    r=reconcile('a',CorpusCatalog(a).build(),'b',CorpusCatalog(b).build())
    assert r.common_byte_hashes==1 and r.left_only_byte_hashes==0 and r.right_only_byte_hashes==0


def test_zip_catalog_preserves_representation_and_sampling_claims(tmp_path:Path):
    z=tmp_path/'multi-chart.zip'
    text='time,open,high,low,close\n100,1,2,0,1\n110,2,3,1,2\n'
    with zipfile.ZipFile(z,'w') as f:
        f.writestr('Renko/CME_MINI_DL_NQ1!, 10R.csv',text)
        f.writestr('Tick/CME_MINI_DL_NQ1!, 1000T.csv',text.replace('110','111'))
    ms=[m for m in ZipCorpusCatalog(tmp_path).build() if 'appledouble' not in m.quality_flags]
    by_claim={m.identity.filename_claim:m for m in ms}
    renko=by_claim['10R']
    tick=by_claim['1000T']
    assert renko.metadata['representation_claim']['family']=='renko'
    assert renko.metadata['representation_claim']['price_geometry']=='renko'
    assert renko.metadata['representation_claim']['sampling_domain']=='event'
    assert renko.metadata['representation_claim']['construction']=='range'
    assert renko.metadata['representation_hypothesis']['kind']=='event_representation_candidate'
    assert tick.metadata['representation_claim']['family']=='unknown'
    assert tick.metadata['representation_claim']['price_geometry']=='unknown'
    assert tick.metadata['representation_claim']['sampling_domain']=='event'
    assert tick.metadata['representation_claim']['construction']=='tick'
    assert tick.metadata['representation_hypothesis']['kind']=='event_bar_claim_candidate'
    assert renko.metadata['representation_claim']['authoritative'] is False


def test_documented_candidate_archive_is_regular_candles_not_profile_family(tmp_path:Path):
    z=tmp_path/'Csv first 60.zip'
    text='time,open,high,low,close,MP POC,MP VAH,MP VAL\n100,1,2,0,1,1,2,0\n110,2,3,1,2,2,3,1\n'
    with zipfile.ZipFile(z,'w') as f:
        f.writestr('Csv first 60/BATS_AAPL, 1.csv',text)
    m=next(m for m in ZipCorpusCatalog(tmp_path).build() if m.row_count)
    claim=m.metadata['representation_claim']
    assert claim['family']=='regular_candles'
    assert claim['price_geometry']=='standard_ohlc'
    assert claim['construction']=='time_bar'
    assert 'market_profile_fields' in claim['schema_tags']
    assert claim['authoritative'] is False


def test_zip_and_plain_catalog_agree_on_invalid_geometry_usability(tmp_path:Path):
    text='time,open,high,low,close\n100,1,2,0,1\n110,2,1,3,2\n'
    plain=tmp_path/'plain'; plain.mkdir()
    (plain/'CME_NQ1!, 1.csv').write_text(text)
    z=tmp_path/'batch.zip'
    with zipfile.ZipFile(z,'w') as f:
        f.writestr('CME_NQ1!, 1.csv',text)
    pm=CorpusCatalog(plain).build()[0]
    zm=next(m for m in ZipCorpusCatalog(tmp_path).build() if m.identity.source_path.startswith('batch.zip!'))
    assert pm.metadata['usable_ohlc_rows']==1
    assert zm.metadata['usable_ohlc_rows']==1
    assert pm.metadata['inconsistent_ohlc_rows']==1
    assert zm.metadata['inconsistent_ohlc_rows']==1
