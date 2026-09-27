
import unittest
from challenger_forge.core import ComponentContext
from challenger_forge.liquidity import LiquiditySweepAdapter, SessionVWAPVolumeSweepAdapter
from challenger_forge.causality import audit_prefix_invariance
from challenger_forge.event_time import validate_event_time
from challenger_forge.execution import CostScenario, next_bar_shadow_pnl

class LiquidityTests(unittest.TestCase):
    def make_ctx(self):
        n=80
        ts=list(range(n))
        o=[100.0+i*0.1 for i in range(n)]
        c=[x+0.2 for x in o]
        h=[max(a,b)+0.5 for a,b in zip(o,c)]
        l=[min(a,b)-0.5 for a,b in zip(o,c)]
        v=[100+i for i in range(n)]
        sessions=[i//20 for i in range(n)]
        # deterministic sweep-like bars
        l[30]=min(l[10:30])-2.0; c[30]=min(l[10:30])+0.2; o[30]=c[30]-1.0; h[30]=c[30]+0.5; v[30]=300
        h[50]=max(h[30:50])+2.0; c[50]=max(h[30:50])-0.2; o[50]=c[50]+1.0; l[50]=c[50]-0.5; v[50]=350
        return ComponentContext(["SYNTH-LIQ-001"],ts,
            {"open":o,"high":h,"low":l,"close":c,"volume":v},
            {"session_id":sessions})

    def test_incumbent_causal_and_event_time(self):
        ctx=self.make_ctx()
        a=LiquiditySweepAdapter(lookback=20)
        audit=audit_prefix_invariance(a,ctx,warmup=20)
        self.assertTrue(audit.passed,audit.violations)
        self.assertTrue(validate_event_time(a.run(ctx))["passed"])

    def test_challenger_causal_and_event_time(self):
        ctx=self.make_ctx()
        a=SessionVWAPVolumeSweepAdapter(lookback=20,min_volume_ratio=0.75)
        audit=audit_prefix_invariance(a,ctx,warmup=20)
        self.assertTrue(audit.passed,audit.violations)
        self.assertTrue(validate_event_time(a.run(ctx))["passed"])

    def test_cost_harness_penalizes(self):
        ctx=self.make_ctx()
        result=LiquiditySweepAdapter(lookback=20).run(ctx)
        pnl0=next_bar_shadow_pnl(ctx.series["close"],result.values,cost=CostScenario(0,0,0,1))
        pnl1=next_bar_shadow_pnl(ctx.series["close"],result.values,cost=CostScenario(1,1,1,1))
        self.assertEqual(len(pnl0),len(pnl1))
        if pnl0:
            self.assertTrue(all(b["net_points"] < a["net_points"] for a,b in zip(pnl0,pnl1)))
