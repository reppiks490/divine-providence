from pathlib import Path
import pandas as pd
from daedalus.catalog import build_catalog


def test_exact_duplicates_are_marked_but_distinct_mechanics_preserved(tmp_path: Path):
    a = pd.DataFrame({"time":[1,2,3],"open":[1,1,1],"high":[2,2,2],"low":[0,0,0],"close":[1,1,1]})
    b = pd.DataFrame({"time":[1,1.001,2],"open":[1,1,1],"high":[2,2,2],"low":[0,0,0],"close":[1,1,1]})
    a.to_csv(tmp_path/"X, 1.csv",index=False)
    a.to_csv(tmp_path/"X, 1 2.csv",index=False)
    b.to_csv(tmp_path/"X, 1 3.csv",index=False)
    cat = build_catalog(tmp_path)
    assert len(cat)==3
    assert cat.sha256.nunique()==2
    assert cat.mechanics_signature.nunique()==2
