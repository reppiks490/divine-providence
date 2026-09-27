import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('evidence_fusion', ROOT/'scripts/evidence_fusion.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_duplicate_source_family_does_not_double_count_support():
    records=[
      {'claim':'x','stance':'support','source_family':'wire-a','authority':0.9,'freshness':1.0},
      {'claim':'x','stance':'support','source_family':'wire-a','authority':0.8,'freshness':1.0},
      {'claim':'x','stance':'contrast','source_family':'primary-b','authority':0.9,'freshness':1.0},
    ]
    out=mod.fuse_claim(records)
    assert out['independent_families']==2
    assert out['support_weight'] < 1.8
    assert out['has_conflict'] is True

def test_primary_source_gets_more_weight_than_low_authority_echo():
    records=[
      {'claim':'x','stance':'support','source_family':'primary','authority':1.0,'freshness':1.0},
      {'claim':'x','stance':'contrast','source_family':'echo','authority':0.2,'freshness':1.0},
    ]
    out=mod.fuse_claim(records)
    assert out['support_weight'] > out['contrast_weight']
