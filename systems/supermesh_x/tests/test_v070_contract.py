from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]


def test_manifest_and_docs_declare_v070_private_intelligence_bus():
    manifest=(ROOT/'manifest.yaml').read_text()
    assert 'version:' in manifest
    for cap in ['communications.email.search','research.newsletter.private','portfolio.holdings','portfolio.event_impact','privacy.private_source_guard']:
        assert cap in manifest
    for p in [
        'references/email-intelligence-bus.md',
        'references/private-source-boundary.md',
        'references/portfolio-shock-overlay.md',
    ]:
        assert (ROOT/p).exists()
    skill=(ROOT/'SKILL.md').read_text()
    assert 'Private Intelligence Bus & Portfolio Shock Overlay' in skill
    assert 'Gmail' in skill
    assert 'Finances' in skill


def test_plugin_universe_and_aliases_include_gmail_and_finances():
    uni=json.loads((ROOT/'config/plugin-universe.json').read_text())
    ids={p['id'] for p in uni['providers']}
    assert {'gmail','finances'} <= ids
    aliases=json.loads((ROOT/'config/plugin-aliases.json').read_text())['aliases']
    assert aliases['Gmail']=='gmail'
    assert aliases['Finances']=='finances'
