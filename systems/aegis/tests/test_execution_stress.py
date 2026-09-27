import unittest
from challenger_forge.execution import stressed_partial_fill_pnl
class ExecutionStressTests(unittest.TestCase):
    def test_partial_fill_and_cost_reduce_total(self):
        close=[100,102,104,106,108]; sig=[{'direction':1},None,None,None,None]
        s=stressed_partial_fill_pnl(close,sig,latency_bars=(1,),fill_fractions=(1.0,.5),cost_points=(1.0,))
        full=[x for x in s if x['fill_fraction']==1.0][0]; half=[x for x in s if x['fill_fraction']==.5][0]
        self.assertGreater(full['total_net'],half['total_net'])
