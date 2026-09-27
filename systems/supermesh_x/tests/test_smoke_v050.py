from scripts.smoke_check import run_checks


def _vtuple(v):
    return tuple(map(int,v.split('.')))


def test_smoke_exercises_event_fabric_v050_or_later():
    result=run_checks()
    assert _vtuple(result['package_version']) >= (0,5,0)
    assert result['checks']['event_fabric'] is True
    assert result['status'] == 'pass'
