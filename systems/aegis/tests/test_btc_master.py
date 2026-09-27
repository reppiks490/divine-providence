import unittest, math
from challenger_forge.core import ComponentContext
from challenger_forge.btc_master import ADXTrendStrengthAdapter, IchimokuRegimeAdapter, TrendPullbackAdapter, CompositeExitAdapter
from challenger_forge.causality import audit_prefix_invariance
from challenger_forge.event_time import validate_event_time

class BTCMasterTests(unittest.TestCase):
    def market(self,n=180):
        c=[100+i*.2+math.sin(i/5) for i in range(n)]; h=[x+1 for x in c]; l=[x-1 for x in c]; o=[x-.1 for x in c]
        return ComponentContext(['BTC-SYNTH'],list(range(n)),{'open':o,'high':h,'low':l,'close':c})
    def test_adx_causal(self):
        ctx=self.market(); a=ADXTrendStrengthAdapter(); self.assertTrue(audit_prefix_invariance(a,ctx,warmup=30).passed); self.assertTrue(validate_event_time(a.run(ctx))['passed'])
    def test_ichimoku_causal(self):
        ctx=self.market(); a=IchimokuRegimeAdapter(); self.assertTrue(audit_prefix_invariance(a,ctx,warmup=52).passed)
    def test_pullback_causal(self):
        ctx=self.market(); a=TrendPullbackAdapter(); self.assertTrue(audit_prefix_invariance(a,ctx,warmup=22).passed)
    def test_exit_composite(self):
        n=20; ts=list(range(n)); z=[False]*n; one=z[:]; one[10]=True
        ctx=ComponentContext(['X'],ts,{'tk_cross':one,'cloud_breach':one,'rsi_deceleration':z,'ema_cross':z,'kijun_break':z})
        self.assertTrue(CompositeExitAdapter(2).run(ctx).values[10]['exit_now'])
