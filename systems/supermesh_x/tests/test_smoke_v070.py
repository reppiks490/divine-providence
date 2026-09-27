import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_smoke_reports_private_intelligence_bus():
    p=subprocess.run([sys.executable, str(ROOT/'scripts/smoke_check.py')], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    data=json.loads(p.stdout)
    major, minor, patch = (int(x) for x in data['package_version'].split('.'))
    assert (major, minor, patch) >= (0, 7, 0)
    for key in ['email_intelligence_bus','private_source_firewall','portfolio_shock_overlay','private_context_fusion']:
        assert data['checks'][key] is True
