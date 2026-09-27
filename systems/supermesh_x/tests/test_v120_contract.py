from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
def test_manifest_declares_v120_task_lifecycle_capabilities():
    m=yaml.safe_load((ROOT/'manifest.yaml').read_text())
    assert tuple(map(int,m['version'].split('.'))) >= (1,2,0)
    d=set(m['core_domains'])
    assert {'evidence.task_lifecycle_receipt','plugins.task_ttl_guard','plugins.task_poll_normalizer'} <= d
