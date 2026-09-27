import unittest
from challenger_forge.negative_controls import deterministic_random_direction, randomized_signal_control
class NegativeControlTests(unittest.TestCase):
    def test_deterministic(self): self.assertEqual(deterministic_random_direction(7),deterministic_random_direction(7))
    def test_only_rewrites_active_signals(self):
        x=[None,{'direction':1},None,{'direction':-1}]; y=randomized_signal_control(x)
        self.assertIsNone(y[0]); self.assertIsNone(y[2]); self.assertIn(y[1]['direction'],(-1,1)); self.assertTrue(y[1]['negative_control'])
