from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_v020_artifacts_remain_present():
    required=[
      'scripts/provider_state.py','scripts/temporal_guard.py','scripts/evidence_fusion.py',
      'scripts/query_expander.py','scripts/mesh_planner.py','scripts/provider_benchmark.py',
      'schemas/provider-state.schema.json','config/runtime-state.example.json',
      'references/runtime-provider-state.md','workflows/adaptive-federated-research.md',
      'CHANGELOG.md'
    ]
    missing=[p for p in required if not (ROOT/p).exists()]
    assert not missing, f'missing: {missing}'
