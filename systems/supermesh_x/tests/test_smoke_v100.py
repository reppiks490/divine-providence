import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from smoke_check import run_checks


def test_smoke_exercises_v100_protocol_era_layer():
    r = run_checks()
    assert tuple(map(int, r['package_version'].split('.'))) >= (1,0,0)
    assert r['checks']['mcp_protocol_era_guard'] is True
    assert r['checks']['mcp_tool_annotation_guard'] is True
    assert r['checks']['tool_trace_redaction'] is True
