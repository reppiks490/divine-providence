import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_market_mover_artifacts_exist():
    required=[
      'schemas/public-market-signal.schema.json',
      'config/market-movers.example.json',
      'references/market-mover-intelligence.md',
      'workflows/public-figure-market-impact.md'
    ]
    missing=[p for p in required if not (ROOT/p).exists()]
    assert not missing, f'missing: {missing}'


def test_skill_and_manifest_advertise_market_mover_capabilities():
    skill=(ROOT/'SKILL.md').read_text()
    manifest=(ROOT/'manifest.yaml').read_text()
    assert 'market.mover.public_signal' in manifest
    assert 'market.impact.attribution' in manifest
    assert re.search(r'Market[- ]Mover', skill, re.I)
    assert 'public-only' in skill.lower() or 'public only' in skill.lower()
