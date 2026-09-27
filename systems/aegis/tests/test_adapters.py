
import unittest
from challenger_forge.core import ComponentContext
from challenger_forge.risk import ATRRiskAdapter
from challenger_forge.macro import DXYMacroPressureAdapter
from challenger_forge.causality import audit_prefix_invariance
from challenger_forge.partitions import chronological_purged_partitions

class AdapterTests(unittest.TestCase):
    def make_ctx(self, n=80):
        ts=list(range(n))
        close=[100 + i*0.2 + (i%5)*0.1 for i in range(n)]
        high=[x+1 for x in close]
        low=[x-1 for x in close]
        return ComponentContext(["SYNTH-ADAPTER-001"],ts,{"high":high,"low":low,"close":close})

    def test_atr_adapter_causal(self):
        ctx=self.make_ctx()
        audit=audit_prefix_invariance(ATRRiskAdapter(length=14),ctx,warmup=13)
        self.assertTrue(audit.passed, audit.violations)

    def test_macro_adapter_causal(self):
        n=80
        ts=list(range(n))
        dxy_level=[100+i*0.1 for i in range(n)]
        dxy_return=[0.001 for _ in range(n)]
        asset_return=[-0.001 + ((i%3)-1)*0.0001 for i in range(n)]
        ctx=ComponentContext(["SYNTH-MACRO-001"],ts,{
            "asset_return":asset_return,
            "dxy_return":dxy_return,
            "dxy_level":dxy_level
        })
        audit=audit_prefix_invariance(DXYMacroPressureAdapter(corr_window=20,slope_window=5),ctx,warmup=19)
        self.assertTrue(audit.passed, audit.violations)

    def test_partitions_keep_final_holdout(self):
        p=chronological_purged_partitions(600,purge_bars=24,embargo_bars=24)
        self.assertEqual(p["train"], (0,336))
        self.assertEqual(p["validation"], (384,456))
        self.assertEqual(p["final_holdout_untouched"], (504,600))
