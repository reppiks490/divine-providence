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
