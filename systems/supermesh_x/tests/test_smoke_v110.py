import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from smoke_check import run_checks

def test_smoke_exercises_v110_resumable_layer():
    r = run_checks()
    assert tuple(map(int, r['package_version'].split('.'))) >= (1,1,0)
    assert r['checks']['mcp_multi_round_trip_guard'] is True
    assert r['checks']['mcp_task_extension_guard'] is True
