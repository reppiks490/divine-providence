from pathlib import Path
from nexus.timeutil import timestamp_to_ns
from nexus.ingest import iter_bars, BarClockPolicy


def test_fractional_epoch_preserved():
    ns,frac=timestamp_to_ns('1700000000.125')
    assert frac
    assert ns==1_700_000_000_125_000_000


def test_repeated_timestamps_preserve_sequence(tmp_path: Path):
    p=tmp_path/'x.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n100,1,3,0,2\n')
    rows=list(iter_bars(p,'s',emit_unsealed_terminal=True))
    assert [r.event_ns for r in rows]==[100_000_000_000,100_000_000_000]
    assert [r.source_sequence for r in rows]==[0,1]


def test_nonfinite_epoch_is_rejected():
    import pytest
    for value in ('NaN','Infinity','-Infinity'):
        with pytest.raises(ValueError):
            timestamp_to_ns(value)
