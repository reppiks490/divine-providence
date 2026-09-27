import unittest, math
from challenger_forge.core import ComponentContext
from challenger_forge.factor import PITFactorCorrelationAdapter
from challenger_forge.causality import audit_prefix_invariance
from challenger_forge.event_time import validate_event_time

class FactorTests(unittest.TestCase):
    def test_factor_adapter_causal(self):
        n=120; ts=list(range(n))
        a=[math.sin(i/8)*.01 for i in range(n)]; b=[math.cos(i/9)*.01 for i in range(n)]
        target=[0.6*a[i]-0.3*b[i] for i in range(n)]
        ctx=ComponentContext(['SYNTH-F'],ts,{'target_return':target,'a':a,'b':b},{'factor_available_at':{'a':ts[:],'b':ts[:]}})
        ad=PITFactorCorrelationAdapter(['a','b'],{'a':.6,'b':.4},window=30)
        self.assertTrue(audit_prefix_invariance(ad,ctx,warmup=29).passed)
        self.assertTrue(validate_event_time(ad.run(ctx))['passed'])
    def test_future_factor_availability_is_rejected(self):
        n=40; ts=list(range(n)); x=[0.01*i for i in range(n)]; avail=ts[:]; avail[20]=21
        ctx=ComponentContext(['S'],ts,{'target_return':x,'a':x},{'factor_available_at':{'a':avail}})
        with self.assertRaises(ValueError): PITFactorCorrelationAdapter(['a'],window=10).run(ctx)
