import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from circuit_breaker import evaluate_breaker, request_allowed


def test_breaker_opens_after_failure_threshold():
    state=evaluate_breaker({'consecutive_failures':3,'last_failure_ts':100}, now=110, failure_threshold=3, reset_after=60)
    assert state['state']=='open'
    assert state['retry_after']==160
    assert request_allowed(state, now=120) is False


def test_breaker_half_opens_after_reset_window():
    state=evaluate_breaker({'consecutive_failures':3,'last_failure_ts':100}, now=161, failure_threshold=3, reset_after=60)
    assert state['state']=='half_open'
    assert request_allowed(state, now=161, probe=True) is True
    assert request_allowed(state, now=161, probe=False) is False
