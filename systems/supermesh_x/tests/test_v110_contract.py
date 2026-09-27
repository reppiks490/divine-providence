from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[1]

def test_manifest_declares_v110_mrtr_task_capabilities():
    manifest = yaml.safe_load((ROOT / 'manifest.yaml').read_text())
    assert tuple(map(int, manifest['version'].split('.'))) >= (1,1,0)
    domains = set(manifest['core_domains'])
    assert 'plugins.multi_round_trip_guard' in domains
    assert 'plugins.task_extension_guard' in domains
    assert 'evidence.resumable_tool_trace' in domains
