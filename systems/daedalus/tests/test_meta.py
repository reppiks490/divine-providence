from pathlib import Path
from daedalus.registry import ExperimentRegistry
from daedalus.meta import summarize_model_memory


def test_meta_memory_reads_registry(tmp_path: Path):
    p=tmp_path/'x.sqlite3'; r=ExperimentRegistry(p)
    result={"validation":{"aggregate":{"auc":0.6}}}
    r.record('a','s','p','m',{},result,True)
    rows=summarize_model_memory(p)
    assert rows and rows[0].model_name=='m' and rows[0].experiments==1
