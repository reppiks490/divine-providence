import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    'deep-research','exa','tavily','firecrawl','parallel-search','consensus','scite',
    'datablue','twelve-data','tickerlayer','factorweave','zacks','coingecko','blockscout',
    'exoscope','economist-graphs','omgskills','nvidia-skills','codex-coordinator',
    'youtube-conversation','baton-pass','founder-pulse','superpowers','astral-orchestrator',
    'akinator','hey-traders','study','finances','interactive-brokers','forex-factory','substack'
}

def test_registry_contains_all_required_integrations():
    data = json.loads((ROOT/'config/integration-registry.json').read_text())
    assert tuple(map(int,data['version'].split('.'))) >= (0,6,0)
    ids = {x['id'] for x in data['integrations']}
    assert REQUIRED <= ids


def test_every_integration_declares_access_and_permissions():
    data = json.loads((ROOT/'config/integration-registry.json').read_text())
    for item in data['integrations']:
        assert item['capabilities']
        assert item['access_mode']
        assert item['permission_class'] in {'read_only','read_write_gated','private_read_write_gated','orchestration','local_runtime'}
