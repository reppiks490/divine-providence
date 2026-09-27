from pathlib import Path
from nexus.ingest import iter_bars, BarClockPolicy
from nexus.csvio import load_ohlcv
from nexus.align import CausalAligner


def test_conservative_next_seals_repeated_group_together_and_withholds_terminal(tmp_path: Path):
    p=tmp_path/'x.csv'
    p.write_text(
        'time,open,high,low,close\n'
        '100,1,2,0,1\n'
        '100,1,3,0,2\n'
        '110,2,4,1,3\n'
        '120,3,5,2,4\n'
    )
    rows=list(iter_bars(p,'s'))
    assert len(rows)==3  # final 120 row is unsealed and withheld
    assert [r.source_sequence for r in rows]==[0,1,2]
    assert [r.available_ns for r in rows]==[110_000_000_000,110_000_000_000,120_000_000_000]
    assert all('stamp_semantics_unknown' in r.quality_flags for r in rows)
    assert all('availability_unknown' not in r.quality_flags for r in rows)


def test_terminal_can_be_emitted_for_forensics_but_remains_unavailable(tmp_path: Path):
    p=tmp_path/'x.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n110,1,3,0,2\n')
    rows=list(iter_bars(p,'s',emit_unsealed_terminal=True))
    assert len(rows)==2
    assert rows[-1].available_ns is None
    assert 'availability_unknown' in rows[-1].quality_flags


def test_verified_close_policy_does_not_delay(tmp_path: Path):
    p=tmp_path/'x.csv'
    p.write_text('time,open,high,low,close\n100,1,2,0,1\n')
    rows=list(iter_bars(p,'s',clock_policy=BarClockPolicy(source_stamp='close')))
    assert rows[0].event_ns==100_000_000_000
    assert rows[0].available_ns==100_000_000_000


def test_load_and_align_can_use_conservative_availability(tmp_path: Path):
    a=tmp_path/'a.csv'; b=tmp_path/'b.csv'
    a.write_text('time,open,high,low,close\n100,1,1,1,1\n110,2,2,2,2\n120,3,3,3,3\n')
    b.write_text('time,open,high,low,close\n105,10,10,10,10\n115,20,20,20,20\n125,30,30,30,30\n')
    da=load_ohlcv(a); db=load_ohlcv(b)
    out=CausalAligner().align(da,{'b':db},time_col='available_ns')
    # A's first row becomes usable at 110; B's first becomes usable at 115, so it is not visible at 110.
    assert out.iloc[0]['available_ns']==110_000_000_000
    assert out.iloc[0]['b']!=out.iloc[0]['b']
