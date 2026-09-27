from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
def test_manifest_declares_v140_subscription_integrity():
 m=yaml.safe_load((ROOT/'manifest.yaml').read_text()); assert tuple(map(int,m['version'].split('.'))) >= (1,4,0); d=set(m['core_domains']); assert {'plugins.subscription_event_dedupe','evidence.cache_invalidation_receipt'} <= d
