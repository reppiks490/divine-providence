from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
def test_manifest_declares_v150_subscription_resilience():
 m=yaml.safe_load((ROOT/'manifest.yaml').read_text()); assert tuple(map(int,m['version'].split('.'))) >= (1,5,0); d=set(m['core_domains']); assert {'plugins.subscription_restart_guard','evidence.subscription_restart_receipt'} <= d
