from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]


def test_v030_artifacts_exist():
    required=[
      'scripts/capability_catalog.py','scripts/circuit_breaker.py','scripts/provenance_graph.py',
      'scripts/frontier_planner.py','scripts/adapter_negotiation.py',
      'schemas/provider-descriptor.schema.json','config/discovery-registry.example.json',
      'references/dynamic-discovery.md','references/provenance-graph.md',
      'workflows/autonomous-source-expansion.md'
    ]
    missing=[p for p in required if not (ROOT/p).exists()]
    assert not missing, f'missing: {missing}'


def test_v030_artifacts_remain_available_in_newer_package():
    text=(ROOT/'manifest.yaml').read_text()
    assert 'compatibility_baseline: 0.3.0' in text
    assert 'market.mover.public_signal' in text
    assert 'market.impact.attribution' in text
