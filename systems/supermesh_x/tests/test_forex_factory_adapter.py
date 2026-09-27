import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from forex_factory_adapter import normalize_event, surprise_score


def test_normalize_event_preserves_revision_and_timezone():
    e = normalize_event({'title':'Core PCE Price Index m/m','country':'USD','date':'2026-09-25','time':'12:30pm','impact':'High','actual':'0.3%','forecast':'0.2%','previous':'0.2%','revised_previous':'0.1%'}, timezone='Europe/London')
    assert e['currency'] == 'USD'
    assert e['impact'] == 'high'
    assert e['timezone'] == 'Europe/London'
    assert e['revised_previous'] == '0.1%'


def test_surprise_score_numeric_percent():
    s = surprise_score('0.3%','0.2%')
    assert s['direction'] == 'above_forecast'
    assert abs(s['difference'] - 0.1) < 1e-9
