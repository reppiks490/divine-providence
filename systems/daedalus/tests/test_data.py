from pathlib import Path
import pandas as pd
from daedalus.data import load_bars_with_quality


def test_repeated_timestamps_are_preserved(tmp_path: Path):
    p=tmp_path/'event.csv'
    pd.DataFrame({
        'time':[1.0,1.0,1.25,2.0],
        'open':[1,1,1,1], 'high':[2,2,2,2], 'low':[0,0,0,0], 'close':[1,1,1,1]
    }).to_csv(p,index=False)
    df,q=load_bars_with_quality(p,require_nondecreasing_time=True)
    assert len(df)==4
    assert q.duplicate_timestamp_ratio>0
    assert q.fractional_timestamp_ratio>0
