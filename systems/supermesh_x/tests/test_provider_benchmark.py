import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('provider_benchmark', ROOT/'scripts/provider_benchmark.py')
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def test_benchmark_rewards_reliability_and_low_latency():
    samples=[
      {'ok':True,'latency_ms':100,'quality':0.9},
      {'ok':True,'latency_ms':120,'quality':0.8},
      {'ok':False,'latency_ms':500,'quality':0.0},
    ]
    out=mod.summarize(samples)
    assert round(out['success_rate'],3)==0.667
    assert out['latency_p95_ms'] >= 120
    assert 0 <= out['health'] <= 1

def test_empty_samples_are_unverified():
    out=mod.summarize([])
    assert out['state']=='unverified'
    assert out['health']==0.0
