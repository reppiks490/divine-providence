import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from smoke_check import run_checks


def test_smoke_exercises_v090_execution_planning_layer():
    r = run_checks()
    assert tuple(map(int, r['package_version'].split('.'))) >= (0, 9, 0)
    assert r['checks']['capability_execution_plan'] is True
    assert r['checks']['plan_authority_gate'] is True
    assert r['checks']['plan_privacy_firewall'] is True
    assert r['checks']['plan_schema_rediscovery'] is True
