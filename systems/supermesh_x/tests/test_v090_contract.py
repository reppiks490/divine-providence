from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_declares_v090_execution_plan_capabilities():
    manifest = yaml.safe_load((ROOT / 'manifest.yaml').read_text())
    assert tuple(map(int, manifest['version'].split('.'))) >= (0, 9, 0)
    domains = set(manifest['core_domains'])
    assert 'plugins.execution_plan' in domains
    assert 'plugins.authority_contract' in domains
    assert 'privacy.plan_firewall' in domains
    assert 'evidence.plan_digest' in domains


def test_v090_reference_and_workflow_exist():
    assert (ROOT / 'references' / 'adaptive-execution-planning.md').exists()
    assert (ROOT / 'workflows' / 'capability-plan-execution.md').exists()
