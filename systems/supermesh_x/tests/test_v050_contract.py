from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]


def _version_tuple(text):
    m=re.search(r'^version:\s*(\d+)\.(\d+)\.(\d+)\s*$', text, re.M)
    assert m
    return tuple(map(int,m.groups()))


def test_v050_artifacts_exist():
    required=[
      'scripts/event_dedup.py','scripts/event_ledger.py','scripts/shock_graph.py',
      'scripts/watchlist_priority.py','scripts/confidence_decay.py','scripts/replay_bundle.py',
      'scripts/event_fabric.py','references/event-fabric.md','workflows/replayable-market-event-analysis.md'
    ]
    missing=[p for p in required if not (ROOT/p).exists()]
    assert not missing, f'missing: {missing}'


def test_manifest_preserves_v050_contract_and_v040_baseline():
    text=(ROOT/'manifest.yaml').read_text()
    assert _version_tuple(text) >= (0,5,0)
    assert re.search(r'^compatibility_baseline:\s*0\.3\.0\s*$', text, re.M)
    for capability in [
        'market.event.dedup','market.event.ledger','market.event.replay',
        'market.impact.shock_graph','market.mover.priority','evidence.confidence_decay'
    ]:
        assert capability in text


def test_skill_exposes_event_fabric_and_replay_policy():
    text=(ROOT/'SKILL.md').read_text().lower()
    assert 'event fabric' in text
    assert 'replay' in text
    assert 'duplicate' in text or 'syndication' in text
    assert 'hash' in text
