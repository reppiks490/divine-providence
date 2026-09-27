from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def test_manifest_and_docs_declare_v060_unified_fabric():
    manifest=(ROOT/'manifest.yaml').read_text()
    version_line=next(line for line in manifest.splitlines() if line.startswith('version:'))
    assert tuple(map(int,version_line.split(':',1)[1].strip().split('.'))) >= (0,6,0)
    for cap in ['broker.portfolio','broker.orders','market.calendar.macro','research.newsletters','integrations.resolve']:
        assert cap in manifest
    for p in [
        'references/unified-integration-fabric.md',
        'references/ibkr-brokerage.md',
        'references/forex-factory-calendar.md',
        'references/substack-intelligence.md',
    ]:
        assert (ROOT/p).exists()
    skill=(ROOT/'SKILL.md').read_text()
    assert 'Unified Provider & Broker Fabric' in skill
    assert 'Interactive Brokers' in skill
    assert 'Forex Factory' in skill
    assert 'Substack' in skill


def test_plugin_aliases_cover_user_named_surfaces():
    data=json.loads((ROOT/'config/plugin-aliases.json').read_text())
    keys=set(data['aliases'])
    for k in ['Deep research','Search','Study','Codex Coordinator','YouTube Conversation','Baton Pass','Founder Pulse','Superpowers','Astral Orchestrator','Akinator','Hey-Traders! Quant Trading','FactorWeave','TickerLayer','NVIDIA Skills','omgskills','The Economist - Graphs','Exum: ExoScope Crypto','CoinGecko','Blockscout Blockchain Data','Zacks Financial Data','DataBlue','Twelve Data','Interactive Brokers','Forex Factory','Substack']:
        assert k in keys
