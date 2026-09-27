import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from event_study import abnormal_return, cumulative_abnormal_return, placebo_check


def test_event_study_abnormal_and_cumulative_return():
    assert round(abnormal_return(0.012, 0.004), 6) == 0.008
    vals = [0.01, -0.002, 0.005]
    assert round(cumulative_abnormal_return(vals), 6) == 0.013


def test_placebo_flags_pretrend_when_pre_event_abnormal_moves_are_large():
    out = placebo_check([-0.001, 0.002, 0.001], threshold=0.01)
    assert out['pretrend_detected'] is False
    out2 = placebo_check([0.015, -0.002], threshold=0.01)
    assert out2['pretrend_detected'] is True
