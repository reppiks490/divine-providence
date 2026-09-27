from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_v080_manifest_and_docs_contract():
    manifest = (ROOT/'manifest.yaml').read_text(encoding='utf-8')
    skill = (ROOT/'SKILL.md').read_text(encoding='utf-8')
    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    version_line = next(line for line in manifest.splitlines() if line.startswith('version:'))
    version = tuple(map(int, version_line.split(':',1)[1].strip().split('.')))
    assert version >= (0, 8, 0)
    for capability in [
        'plugins.surface_diff',
        'plugins.discovery_receipt',
        'plugins.adaptive_routing',
        'plugins.schema_drift',
        'plugins.replacement_plan',
        'evidence.discovery_audit',
    ]:
        assert f'  - {capability}' in manifest
    assert 'Adaptive Capability Director' in skill
    assert 'schema drift' in skill.lower()
    assert 'discovery receipt' in readme.lower()
