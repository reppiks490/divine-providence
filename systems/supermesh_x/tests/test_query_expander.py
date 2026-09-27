import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('query_expander', ROOT/'scripts/query_expander.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_finance_expansion_includes_primary_and_temporal_queries():
    qs=mod.expand('AAPL revenue guidance', domain='finance')
    kinds={q['kind'] for q in qs}
    assert {'baseline','primary','temporal','contradiction'} <= kinds

def test_expansion_deduplicates_queries():
    qs=mod.expand('bitcoin etf flows', domain='research')
    texts=[q['query'] for q in qs]
    assert len(texts)==len(set(texts))
