import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_smoke_reports_unified_fabric():
    p=subprocess.run([sys.executable, str(ROOT/'scripts/smoke_check.py')], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    data=json.loads(p.stdout)
    assert tuple(map(int,data['package_version'].split('.'))) >= (0,6,0)
    assert data['checks']['unified_integration_fabric'] is True
