from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
def test_manifest_declares_v160_provider_health_feedback():
 m=yaml.safe_load((ROOT/'manifest.yaml').read_text()); assert tuple(map(int,m['version'].split('.'))) >= (1,6,0); d=set(m['core_domains']); assert {'plugins.adaptive_provider_health','plugins.provider_circuit_breaker','evidence.provider_health_receipt'} <= d
