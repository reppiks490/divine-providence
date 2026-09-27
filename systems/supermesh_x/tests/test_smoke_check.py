import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_smoke_check_reports_all_green():
    p = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'smoke_check.py')],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr or p.stdout
    data = json.loads(p.stdout)
    assert tuple(map(int,data['package_version'].split('.'))) >= (0,4,0)
    assert data['status'] == 'pass'
    assert data['checks']['mesh_planner'] is True
    assert data['checks']['public_event_impact'] is True
    assert data['checks']['geopolitical_transmission'] is True
    assert data['checks']['recency_guard'] is True
