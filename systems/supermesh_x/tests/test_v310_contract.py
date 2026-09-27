from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def test_v310_manifest_and_artifacts():
    text=(ROOT/'manifest.yaml').read_text()
    v=tuple(map(int,re.search(r'version: (\d+)\.(\d+)\.(\d+)',text).groups()))
    assert v >= (3,1,0)
    for cap in ('trust.durable_root','trust.threshold_rotation','evidence.transparency_log','evidence.merkle_inclusion','evidence.signed_checkpoint'):
        assert cap in text
    assert (ROOT/'scripts/trust_transparency.py').exists()
    assert (ROOT/'references/trust-transparency.md').exists()
