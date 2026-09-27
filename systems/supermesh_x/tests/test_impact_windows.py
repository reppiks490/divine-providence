import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from impact_windows import event_windows


def test_intraday_windows_include_pre_event_and_multiple_post_horizons():
    w=event_windows('intraday')
    assert (-10,0) in w['pre_minutes']
    assert (0,1) in w['post_minutes']
    assert (0,60) in w['post_minutes']


def test_swing_windows_extend_beyond_intraday():
    w=event_windows('swing')
    assert 1 in w['post_days'] and 5 in w['post_days']
