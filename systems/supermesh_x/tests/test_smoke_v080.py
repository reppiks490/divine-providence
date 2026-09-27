import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from smoke_check import run_checks


def test_smoke_exercises_v080_adaptive_layer():
    r = run_checks()
    assert tuple(map(int, r['package_version'].split('.'))) >= (0, 8, 0)
    assert r['checks']['tool_surface_diff'] is True
    assert r['checks']['discovery_receipt'] is True
    assert r['checks']['adaptive_capability_director'] is True
