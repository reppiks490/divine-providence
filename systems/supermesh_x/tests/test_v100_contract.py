from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_declares_v100_protocol_era_capabilities():
    manifest = yaml.safe_load((ROOT / 'manifest.yaml').read_text())
    assert tuple(map(int, manifest['version'].split('.'))) >= (1,0,0)
    domains = set(manifest['core_domains'])
    assert 'plugins.mcp_era_negotiation' in domains
    assert 'plugins.tool_annotation_guard' in domains
    assert 'evidence.tool_trace' in domains


def test_v100_docs_exist():
    assert (ROOT / 'references' / 'mcp-era-safety.md').exists()
    assert (ROOT / 'workflows' / 'protocol-era-preflight.md').exists()
    assert (ROOT / 'CHANGELOG_V100.md').exists()
