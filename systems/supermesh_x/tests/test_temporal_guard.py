import importlib.util
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('temporal_guard', ROOT/'scripts/temporal_guard.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_rejects_evidence_unavailable_at_decision_time():
    evidence={'event_time':'2024-01-01T00:00:00Z','available_time':'2024-01-03T00:00:00Z'}
    assert mod.point_in_time_usable(evidence,'2024-01-02T00:00:00Z') is False

def test_accepts_evidence_available_before_decision_time():
    evidence={'event_time':'2024-01-01T00:00:00Z','available_time':'2024-01-01T18:00:00Z'}
    assert mod.point_in_time_usable(evidence,'2024-01-02T00:00:00Z') is True
