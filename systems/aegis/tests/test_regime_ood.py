
import unittest, math
from challenger_forge.core import ComponentContext
from challenger_forge.regime import VolatilityRegimeAdapter
from challenger_forge.ood import KNNDistanceOODAdapter
from challenger_forge.causality import audit_prefix_invariance
from challenger_forge.event_time import validate_event_time

class RegimeOODTests(unittest.TestCase):
    def test_vol_regime_is_causal(self):
        n=180
        close=[100.0]
        for i in range(1,n):
            step=(0.05 if i<90 else (1.2 if i%2==0 else -1.0))
            close.append(max(1.0,close[-1]+step))
        ctx=ComponentContext(["SYNTH-REGIME"],list(range(n)),{"close":close})
        a=VolatilityRegimeAdapter(short_window=12,long_window=48)
        audit=audit_prefix_invariance(a,ctx,warmup=48)
        self.assertTrue(audit.passed,audit.violations)
        self.assertTrue(validate_event_time(a.run(ctx))["passed"])
        regimes=[x["regime"] for x in a.run(ctx).values if x]
        self.assertIn("HIGH",regimes)

    def test_knn_ood_is_causal_and_detects_spike(self):
        n=170
        f1=[math.sin(i/10)*0.2 for i in range(n)]
        f2=[math.cos(i/10)*0.2 for i in range(n)]
        f1[150]=12.0; f2[150]=-12.0
        ctx=ComponentContext(["SYNTH-OOD"],list(range(n)),{"f1":f1,"f2":f2})
        a=KNNDistanceOODAdapter(["f1","f2"],lookback=60,k=5,threshold=3.0)
        audit=audit_prefix_invariance(a,ctx,warmup=60)
        self.assertTrue(audit.passed,audit.violations)
        result=a.run(ctx)
        self.assertTrue(result.values[150]["ood"])
        self.assertTrue(result.values[150]["abstain"])
